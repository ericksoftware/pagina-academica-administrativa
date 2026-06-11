from django.db import models
from django.core.exceptions import ValidationError
from core.fields import EncryptedCharField
import re
from django.conf import settings

def get_institutional_email_domain():
    return getattr(settings, "SITE_EMAIL_DOMAIN", "wasisv.com").strip().lower().lstrip("@")

def normalizar_email_institucional(value):
    """
    Normaliza el correo institucional.

    Reglas:
    - vacío -> PENDIENTE
    - pendiente / Pendiente / PENDIENTE -> PENDIENTE
    - n/a / N/A -> N/A
    - correo real -> minúsculas
    """
    value = (value or '').strip()

    if not value:
        return 'PENDIENTE'

    value_upper = value.upper()

    if value_upper == 'PENDIENTE':
        return 'PENDIENTE'

    if value_upper in ['N/A', 'NA']:
        return 'N/A'

    return value.lower()


def normalizar_email_opcional(value):
    """
    Normaliza correos opcionales como email_personal.
    """
    value = (value or '').strip()

    if not value:
        return 'N/A'

    value_upper = value.upper()

    if value_upper in ['N/A', 'NA']:
        return 'N/A'

    return value.lower()


def es_email_pendiente_o_na(value):
    value = normalizar_email_institucional(value)
    return value in ['PENDIENTE', 'N/A']


def validate_email_domain(value):
    """Validar que el email institucional termine con el dominio configurado."""
    value = normalizar_email_institucional(value)

    if value in ['PENDIENTE', 'N/A']:
        return

    domain = get_institutional_email_domain()

    if not value.endswith(f'@{domain}'):
        raise ValidationError(f'El correo institucional debe terminar con @{domain}')


def validate_email_format(value):
    """Validar formato básico de email"""
    value = (value or '').strip()

    if not value:
        return

    value_upper = value.upper()

    if value_upper in ['PENDIENTE', 'N/A', 'NA']:
        return

    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_regex, value):
        raise ValidationError('Formato de correo electrónico inválido')


class Alumno(models.Model):
    SEXO_CHOICES = [
        ('hombre', 'Hombre'),
        ('mujer', 'Mujer'),
        ('otro', 'Otro'),
        ('N/A', 'No especificado'),
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

    # Información básica
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
    carrera = models.ForeignKey(
        'evaluaciones.Carrera',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    promedio_semestre_anterior = models.FloatField(null=True, blank=True)
    semestre_actual = models.PositiveIntegerField(default=1)
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, default='matutino')
    plan = models.PositiveIntegerField(default=2023)
    grupo = models.CharField(
        max_length=10,
        default='101',
        help_text='Ejemplo: 101, 102, 201, etc.'
    )

    # Información de contacto
    email_institucional = EncryptedCharField(
        max_length=500,
        default='PENDIENTE',
        validators=[validate_email_domain, validate_email_format],
        help_text="Debe terminar con @wasisv.com , Use 'PENDIENTE' si no tiene correo asignado."
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
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}".strip()

    def normalizar_campos(self):
        """Normaliza campos antes de validar y guardar."""

        self.matricula = (self.matricula or 'PENDIENTE').strip().upper() or 'PENDIENTE'
        self.curp = (self.curp or 'N/A').strip().upper() or 'N/A'
        self.rfc = (self.rfc or 'N/A').strip().upper() or 'N/A'

        self.nombre = (self.nombre or 'N/A').strip() or 'N/A'
        self.apellido_paterno = (self.apellido_paterno or 'N/A').strip() or 'N/A'
        self.apellido_materno = (self.apellido_materno or 'N/A').strip() or 'N/A'

        self.email_institucional = normalizar_email_institucional(self.email_institucional)
        self.email_personal = normalizar_email_opcional(self.email_personal)

        self.password_email_institucional = (
            self.password_email_institucional or 'N/A'
        ).strip() or 'N/A'

        self.telefono = (self.telefono or 'N/A').strip() or 'N/A'
        self.grupo = (self.grupo or '101').strip() or '101'

    def clean(self):
        """Validaciones personalizadas para Alumno."""

        self.normalizar_campos()

        # Validar matrícula única, excepto PENDIENTE
        if self.matricula != 'PENDIENTE':
            alumno_existente = Alumno.objects.filter(
                matricula=self.matricula
            ).exclude(pk=self.pk).first()

            if alumno_existente:
                raise ValidationError({
                    'matricula': (
                        f'La matrícula "{self.matricula}" ya le pertenece al alumno: '
                        f'{alumno_existente.nombre_completo()}'
                    )
                })

        # Validar CURP única, excepto N/A
        if self.curp and self.curp != 'N/A':
            for alumno_existente in Alumno.objects.exclude(pk=self.pk):
                if alumno_existente.curp == self.curp:
                    raise ValidationError({
                        'curp': (
                            f'La CURP "{self.curp}" ya le pertenece al alumno: '
                            f'{alumno_existente.nombre_completo()}'
                        )
                    })

        # Validar RFC único, excepto N/A
        if self.rfc and self.rfc != 'N/A':
            for alumno_existente in Alumno.objects.exclude(pk=self.pk):
                if alumno_existente.rfc == self.rfc:
                    raise ValidationError({
                        'rfc': (
                            f'El RFC "{self.rfc}" ya le pertenece al alumno: '
                            f'{alumno_existente.nombre_completo()}'
                        )
                    })

        # Validar correo institucional único, excepto PENDIENTE / N/A
        if self.email_institucional not in ['PENDIENTE', 'N/A']:
            domain = get_institutional_email_domain()

            if not self.email_institucional.endswith(f'@{domain}'):
                raise ValidationError({
                    'email_institucional': f'El correo institucional debe terminar con @{domain}'
                })

            for alumno_existente in Alumno.objects.exclude(pk=self.pk):
                email_existente = normalizar_email_institucional(
                    alumno_existente.email_institucional
                )

                if email_existente == self.email_institucional:
                    raise ValidationError({
                        'email_institucional': (
                            f'El correo institucional "{self.email_institucional}" ya le pertenece '
                            f'al alumno: {alumno_existente.nombre_completo()}'
                        )
                    })

    def save(self, *args, **kwargs):
        """
        Guarda el alumno y sincroniza su usuario Django.

        Esto corrige el problema donde un alumno creado con correo PENDIENTE
        no podía iniciar sesión después de asignarle un correo real.
        """

        self.normalizar_campos()
        self.full_clean()

        super().save(*args, **kwargs)

        self.sincronizar_usuario_django()

    def obtener_usernames_posibles(self):
        """
        Devuelve usernames posibles para encontrar usuarios de alumnos ya existentes.

        Antes se podía crear como:
        - alumno_<id>, si la matrícula era PENDIENTE
        - alumno_<matricula>, si ya tenía matrícula
        """

        usernames = [f"alumno_{self.id}"]

        if self.matricula and self.matricula != 'PENDIENTE':
            usernames.append(f"alumno_{self.matricula}")
            usernames.append(f"alumno_{self.matricula.lower()}")

        return list(dict.fromkeys(usernames))

    def obtener_email_para_usuario(self):
        """
        Devuelve el email que debe tener el Usuario Django asociado.
        Si el alumno aún no tiene correo institucional, se usa un correo técnico único.
        """

        if self.email_institucional not in ['PENDIENTE', 'N/A']:
            return self.email_institucional.lower().strip()

        domain = get_institutional_email_domain()
        return f"alumno_{self.id}@{domain}"

    def sincronizar_usuario_django(self):
        """
        Crear o actualizar el Usuario Django asociado al alumno.

        Importante:
        - Si el alumno ya existe y se le agrega correo después, actualiza Usuario.email.
        - Si cambia la contraseña institucional, actualiza la contraseña del Usuario.
        - Si no existía usuario, lo crea.
        """

        from django.contrib.auth import get_user_model

        if not self.id:
            return None

        User = get_user_model()

        usernames_posibles = self.obtener_usernames_posibles()
        email_usuario = self.obtener_email_para_usuario()

        usuario = User.objects.filter(
            username__in=usernames_posibles,
            tipo_usuario='alumno'
        ).first()

        # Fallback: buscar por email real si ya existe con ese correo
        if not usuario and self.email_institucional not in ['PENDIENTE', 'N/A']:
            try:
                usuario = User.objects.get(
                    email=self.email_institucional,
                    tipo_usuario='alumno'
                )
            except User.DoesNotExist:
                usuario = None
            except User.MultipleObjectsReturned:
                usuario = User.objects.filter(
                    email=self.email_institucional,
                    tipo_usuario='alumno'
                ).first()

        password_valida = (
            self.password_email_institucional
            and self.password_email_institucional not in ['N/A', 'PENDIENTE', '']
        )

        if usuario:
            usuario.email = email_usuario
            usuario.first_name = self.nombre
            usuario.last_name = f"{self.apellido_paterno} {self.apellido_materno}".strip()
            usuario.tipo_usuario = 'alumno'
            usuario.is_active = self.estado == 'activo'

            if password_valida:
                usuario.set_password(self.password_email_institucional)

            usuario.save()
            return usuario

        username = f"alumno_{self.id}"

        usuario = User(
            username=username,
            email=email_usuario,
            tipo_usuario='alumno',
            first_name=self.nombre,
            last_name=f"{self.apellido_paterno} {self.apellido_materno}".strip(),
            is_active=self.estado == 'activo',
        )

        if password_valida:
            usuario.set_password(self.password_email_institucional)
        else:
            usuario.set_password('N/A')

        usuario.save()
        return usuario