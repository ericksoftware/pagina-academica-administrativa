# evaluaciones/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
# Elimina la importación de Alumno, usaremos cadenas para las referencias

class Carrera(models.Model):
    TIPO_CARRERA_CHOICES = [
        ('licenciatura', 'Licenciatura'),
        ('ingenieria', 'Ingeniería'),
        ('maestria', 'Maestría'),
        ('doctorado', 'Doctorado'),
        ('tecnico', 'Técnico Superior Universitario'),
        ('especialidad', 'Especialidad'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=10, unique=True)
    tipo_carrera = models.CharField(max_length=20, choices=TIPO_CARRERA_CHOICES, default='licenciatura')
    numero_semestres = models.PositiveIntegerField(default=8)
    plan = models.PositiveIntegerField(
        default=2023,
        validators=[
            MinValueValidator(2000),
            MaxValueValidator(2030)
        ]
    )
    activa = models.BooleanField(default=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Carrera'
        verbose_name_plural = 'Carreras'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.tipo_carrera.upper()}: {self.nombre} - Plan {self.plan}"
    
    def get_semestres_range(self):
        """Retorna un rango de semestres para esta carrera"""
        return range(1, self.numero_semestres + 1)
    
    def get_tipo_display_short(self):
        """Retorna la abreviatura del tipo de carrera"""
        abreviatura = {
            'licenciatura': 'LIC.',
            'ingenieria': 'ING.',
            'maestria': 'MTRO.',
            'doctorado': 'DR.',
            'tecnico': 'TSU',
            'especialidad': 'ESP.',
        }
        return abreviatura.get(self.tipo_carrera, self.tipo_carrera.upper()[:4])
    
    def save(self, *args, **kwargs):
        if not self.codigo and self.nombre:
            # Generar código basado en el tipo y nombre
            tipo_abrev = self.get_tipo_display_short().replace('.', '')
            palabras = self.nombre.split()
            siglas = ''.join([palabra[0].upper() for palabra in palabras if palabra[0].isalpha()])
            self.codigo = f"{tipo_abrev}{siglas[:6]}"
        
        if self.codigo:
            counter = 1
            original_codigo = self.codigo
            while Carrera.objects.filter(codigo=self.codigo).exclude(pk=self.pk).exists():
                self.codigo = f"{original_codigo}{counter}"
                counter += 1
        
        super().save(*args, **kwargs)

# evaluaciones/models.py - OPCIÓN RECOMENDADA
class Unidad(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='unidades')
    codigo = models.CharField(max_length=10)
    nombre = models.CharField(max_length=100, default='')
    numero = models.PositiveIntegerField(default=1)
    # QUITAR el campo materia - ya no es necesario
    
    class Meta:
        verbose_name = 'Unidad'
        verbose_name_plural = 'Unidades'
        unique_together = ['carrera', 'codigo']
        ordering = ['carrera', 'numero']
    
    def __str__(self):
        return self.codigo
    
    def save(self, *args, **kwargs):
        if not self.codigo and self.carrera:
            año_plan = str(self.carrera.plan)[-2:]
            numero_str = str(self.numero).zfill(2)
            self.codigo = f"{self.carrera.codigo}{año_plan}{numero_str}"
        
        if not self.nombre:
            self.nombre = f"Unidad {self.numero}"
        
        super().save(*args, **kwargs)
    
    @property
    def materia_asignada(self):
        """Obtener la materia asignada a esta unidad"""
        return self.materias.first() if self.materias.exists() else None

class Materia(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    unidades = models.ManyToManyField(Unidad, related_name='materias')
    nombre = models.CharField(max_length=100)
    semestre = models.PositiveIntegerField()
    creditos = models.FloatField(
        default=8.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(20.0)
        ]
    )
    horas = models.PositiveIntegerField(default=64)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        ordering = ['carrera', 'semestre', 'nombre']
        unique_together = ['carrera', 'nombre', 'semestre']
    
    def __str__(self):
        unidades_str = ", ".join([unidad.codigo for unidad in self.unidades.all()])
        return f"{self.nombre} - Unidades: {unidades_str}"
    
    def clean(self):
        """Validación para asegurar que las unidades no estén ya asignadas"""
        from django.core.exceptions import ValidationError
        
        if self.pk:  # Si la materia ya existe (está siendo editada)
            for unidad in self.unidades.all():
                # Verificar si la unidad ya está asignada a otra materia
                materias_existentes = Materia.objects.filter(unidades=unidad).exclude(pk=self.pk)
                if materias_existentes.exists():
                    materia_existente = materias_existentes.first()
                    raise ValidationError(
                        f'La unidad {unidad.codigo} ya está asignada a la materia: {materia_existente.nombre}'
                    )
    
    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

class Calificacion(models.Model):
    TIPO_CALIFICACION_CHOICES = [
        ('unidad', 'Unidad'),
        ('evidencia_final', 'Evidencia Final'),
        ('evaluacion_global', 'Evaluación Global'),
    ]
    
    alumno = models.ForeignKey('alumnos.Alumno', on_delete=models.CASCADE)
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, null=True, blank=True)
    tipo_calificacion = models.CharField(max_length=20, choices=TIPO_CALIFICACION_CHOICES, default='unidad')
    calificacion = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    periodo = models.CharField(max_length=20)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        unique_together = ['alumno', 'unidad', 'periodo', 'tipo_calificacion']
        ordering = ['alumno', 'unidad__numero']
    
    def __str__(self):
        calif = self.calificacion if self.calificacion else "N/A"
        return f"{self.alumno.matricula} - {self.unidad.codigo}: {calif}"

class PromedioPeriodo(models.Model):
    alumno = models.ForeignKey('alumnos.Alumno', on_delete=models.CASCADE)  # Usar cadena para referencia
    periodo = models.CharField(max_length=20)
    promedio_general = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    total_materias = models.IntegerField(default=0)
    materias_cursadas = models.IntegerField(default=0)
    materias_aprobadas = models.IntegerField(default=0)
    
    fecha_calculo = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Promedio de Periodo'
        verbose_name_plural = 'Promedios de Periodo'
        unique_together = ['alumno', 'periodo']
        ordering = ['alumno', 'periodo']
    
    def __str__(self):
        return f"{self.alumno.matricula} - {self.periodo} - {self.promedio_general}"
    
    def calcular_promedio(self):
        calificaciones = Calificacion.objects.filter(
            alumno=self.alumno,
            periodo=self.periodo
        ).exclude(calificacion__isnull=True)
        
        if calificaciones.exists():
            total_calificaciones = sum(calif.calificacion for calif in calificaciones)
            self.promedio_general = total_calificaciones / calificaciones.count()
            self.total_materias = calificaciones.count()
            self.materias_cursadas = calificaciones.count()
            self.materias_aprobadas = calificaciones.filter(calificacion__gte=6).count()
            self.save()

class ActaEvaluacion(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('generada', 'Generada'),
        ('aprobada', 'Aprobada'),
        ('cerrada', 'Cerrada'),
    ]
    
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    semestre = models.PositiveIntegerField()
    grupo = models.CharField(max_length=10)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=20)
    
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_emision = models.DateField()
    generada_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True)  # Usar cadena si es necesario
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    archivo_pdf = models.FileField(upload_to='actas/%Y/%m/%d/', blank=True, null=True)
    
    total_alumnos = models.IntegerField(default=0)
    alumnos_evaluados = models.IntegerField(default=0)
    promedio_grupo = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    
    class Meta:
        verbose_name = 'Acta de Evaluación'
        verbose_name_plural = 'Actas de Evaluación'
        ordering = ['-fecha_generacion']
        unique_together = ['materia', 'grupo', 'periodo']
    
    def __str__(self):
        return f"Acta {self.materia.nombre} - {self.grupo} - {self.periodo}"
    
    def calcular_estadisticas(self):
        calificaciones = Calificacion.objects.filter(
            materia=self.materia,
            periodo=self.periodo
        ).exclude(calificacion__isnull=True)
        
        self.total_alumnos = calificaciones.count()
        self.alumnos_evaluados = calificaciones.exclude(calificacion__isnull=True).count()
        
        if calificaciones.exists():
            total_calificaciones = sum(calif.calificacion for calif in calificaciones)
            self.promedio_grupo = total_calificaciones / calificaciones.count()
        
        self.save()