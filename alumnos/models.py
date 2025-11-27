from django.db import models
from django.core.exceptions import ValidationError
from core.fields import EncryptedCharField, EncryptedEmailField
import re

def validate_email_domain(value):
    """Validar que el email institucional termine con @edubc.mx"""
    if value != 'N/A' and value != 'Pendiente':
        if not value.endswith('@edubc.mx'):
            raise ValidationError('El correo institucional debe terminar con @edubc.mx')

def validate_email_format(value):
    """Validar formato básico de email"""
    if value != 'N/A' and value != 'Pendiente':
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise ValidationError('Formato de correo electrónico inválido')

class Alumno(models.Model):
    SEXO_CHOICES = [
        ('hombre', 'Hombre'),
        ('mujer', 'Mujer'),
        ('otro', 'Otro'),
    ]
    
    TURNO_CHOICES = [
        ('matutino', 'Matutino'),
        ('vespertino', 'Vespertino'),
    ]
    
    SI_NO_CHOICES = [
        ('si', 'Sí'),
        ('no', 'No'),
    ]
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('graduado', 'Graduado'),
    ]
    
    # Información básica - SIN unique=True y SIN constraints
    matricula = models.CharField(max_length=20, default='PENDIENTE')
    curp = EncryptedCharField(max_length=500, default='N/A')
    rfc = EncryptedCharField(max_length=500, default='N/A')
    nombre = models.CharField(max_length=200, default='N/A')
    apellido_paterno = models.CharField(max_length=200, default='N/A')
    apellido_materno = models.CharField(max_length=200, default='N/A')
    
    # Información personal
    municipio_nacimiento = models.CharField(max_length=100, default='N/A')
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, default='N/A')
    
    # Información académica previa
    institucion_procedencia = models.CharField(max_length=200, default='N/A')
    municipio_institucion = models.CharField(max_length=100, default='N/A')
    clave_escuela = models.CharField(max_length=50, default='N/A')
    fecha_terminacion_prepa = models.DateField(null=True, blank=True)
    promedio_prepa = models.FloatField(null=True, blank=True)
    constancia_terminacion = models.CharField(max_length=2, choices=SI_NO_CHOICES, default='no')
    
    # Información académica actual
    carrera = models.ForeignKey('evaluaciones.Carrera', on_delete=models.SET_NULL, null=True, blank=True)
    promedio_semestre_anterior = models.FloatField(null=True, blank=True)
    semestre_actual = models.PositiveIntegerField(default=1)
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, default='matutino')
    plan = models.PositiveIntegerField(default=2023)
    grupo = models.CharField(
        max_length=10,
        default='101',
        help_text='Ejemplo: 101, 102, 201, etc.'
    )
    
    # Información de contacto con validaciones
    email_institucional = EncryptedCharField(
        max_length=500, 
        default='Pendiente',
        validators=[validate_email_domain, validate_email_format],
        help_text="Debe terminar con @edubc.mx. Use 'Pendiente' si no tiene correo asignado."
    )
    password_email_institucional = EncryptedCharField(max_length=500, default='N/A')
    email_personal = EncryptedCharField(
        max_length=500, 
        default='N/A',
        validators=[validate_email_format],
        help_text="Use 'N/A' si no tiene correo personal."
    )
    telefono = EncryptedCharField(max_length=500, default='N/A')
    
    # Estado del alumno
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    
    # Metadata
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        ordering = ['matricula', 'apellido_paterno', 'apellido_materno', 'nombre']
    
    def __str__(self):
        return f"{self.matricula} - {self.nombre_completo()}"
    
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}"
    
    def clean(self):
        """Validación CORREGIDA - buscando en todos los alumnos"""
        from django.core.exceptions import ValidationError
        
        print(f"🔍 EJECUTANDO CLEAN() - Matrícula: {self.matricula}")
        
        # Validar que matrículas diferentes de "PENDIENTE" sean únicas
        if self.matricula != 'PENDIENTE':
            alumnos_con_misma_matricula = Alumno.objects.filter(
                matricula=self.matricula
            ).exclude(pk=self.pk)
            
            if alumnos_con_misma_matricula.exists():
                alumno_existente = alumnos_con_misma_matricula.first()
                raise ValidationError({
                    'matricula': f'La matrícula "{self.matricula}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}'
                })
        
        # Para campos cifrados, necesitamos verificar TODOS los registros
        if self.curp and self.curp != 'N/A':
            # Buscar en TODOS los alumnos para comparar CURPs descifradas
            for alumno_existente in Alumno.objects.exclude(pk=self.pk):
                if alumno_existente.curp == self.curp:  # Esto compara los valores DESCIFRADOS
                    raise ValidationError({
                        'curp': f'La CURP "{self.curp}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}'
                    })
        
        if self.rfc and self.rfc != 'N/A':
            # Buscar en TODOS los alumnos para comparar RFCs descifrados
            for alumno_existente in Alumno.objects.exclude(pk=self.pk):
                if alumno_existente.rfc == self.rfc:  # Esto compara los valores DESCIFRADOS
                    raise ValidationError({
                        'rfc': f'El RFC "{self.rfc}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}'
                    })
        
        if self.email_institucional and self.email_institucional not in ['N/A', 'Pendiente']:
            if not self.email_institucional.endswith('@edubc.mx'):
                raise ValidationError({
                    'email_institucional': 'El correo institucional debe terminar con @edubc.mx'
                })
            
            # Buscar en TODOS los alumnos para comparar emails descifrados
            for alumno_existente in Alumno.objects.exclude(pk=self.pk):
                if alumno_existente.email_institucional == self.email_institucional:
                    raise ValidationError({
                        'email_institucional': f'El correo institucional "{self.email_institucional}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}'
                    })
    
    def save(self, *args, **kwargs):
        """Método save CORREGIDO para forzar validaciones"""
        print("💾 INICIANDO SAVE() DEL ALUMNO")
        
        # FORZAR la ejecución de validaciones
        try:
            self.full_clean()
            print("✅ VALIDACIONES PASADAS")
        except ValidationError as e:
            print(f"❌ ERROR DE VALIDACIÓN: {e}")
            raise e
        
        # ¿Es un nuevo alumno?
        es_nuevo = self.pk is None
        
        # Guardar el alumno
        super().save(*args, **kwargs)
        print("✅ ALUMNO GUARDADO EN BASE DE DATOS")
        
        # Si es nuevo alumno, crear usuario Django automáticamente
        if es_nuevo:
            self.crear_usuario_django()

    def crear_usuario_django(self):
        """Crear usuario Django automáticamente para el alumno"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Generar username único para el alumno
        username = f"alumno_{self.matricula if self.matricula != 'PENDIENTE' else self.id}"
        
        # Verificar si el usuario ya existe
        if not User.objects.filter(username=username).exists():
            try:
                # Crear usuario con email y password
                user = User.objects.create_user(
                    username=username,
                    email=self.email_institucional if self.email_institucional not in ['N/A', 'Pendiente'] else f"{username}@edubc.mx",
                    password=self.password_email_institucional,
                    tipo_usuario='alumno',
                    first_name=self.nombre,
                    last_name=f"{self.apellido_paterno} {self.apellido_materno}"
                )
                print(f"✅ Usuario Django creado automáticamente: {username}")
                return user
            except Exception as e:
                print(f"❌ Error creando usuario Django: {e}")
        return None
    
    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        
        # ¿Es un nuevo alumno?
        es_nuevo = self.pk is None
        
        # Guardar primero el alumno
        super().save(*args, **kwargs)
        
        # Si es nuevo alumno, crear usuario Django automáticamente
        if es_nuevo:
            self.crear_usuario_django()

    def crear_usuario_django(self):
        """Crear usuario Django automáticamente para el alumno"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Generar username único para el alumno
        username = f"alumno_{self.matricula if self.matricula != 'PENDIENTE' else self.id}"
        
        # Verificar si el usuario ya existe
        if not User.objects.filter(username=username).exists():
            try:
                # Crear usuario con email y password
                user = User.objects.create_user(
                    username=username,
                    email=self.email_institucional if self.email_institucional not in ['N/A', 'Pendiente'] else f"{username}@edubc.mx",
                    password=self.password_email_institucional,
                    tipo_usuario='alumno',  # Agregar este campo al modelo Usuario si no existe
                    first_name=self.nombre,
                    last_name=f"{self.apellido_paterno} {self.apellido_materno}"
                )
                print(f"✅ Usuario Django creado automáticamente: {username}")
                return user
            except Exception as e:
                print(f"❌ Error creando usuario Django: {e}")
        return None