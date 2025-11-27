from django.db import models
from alumnos.models import Alumno

class Constancia(models.Model):
    TIPO_CONSTANCIA_CHOICES = [
        ('estudios', 'Constancia de Estudios'),
        ('calificaciones', 'Constancia de Calificaciones'),
        ('regular', 'Constancia de Alumno Regular'),
    ]
    
    ESTADO_CHOICES = [
        ('generada', 'Generada'),
        ('revisada', 'Revisada'),
        ('entregada', 'Entregada'),
    ]
    
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    tipo_constancia = models.CharField(max_length=20, choices=TIPO_CONSTANCIA_CHOICES)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_emision = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='generada')
    observaciones = models.TextField(blank=True)
    archivo_pdf = models.FileField(upload_to='constancias/%Y/%m/%d/', blank=True, null=True)
    
    # Nuevos campos para las firmas
    firma_izquierda = models.CharField(max_length=100, default='Vo.Bo. Subdirección Académica')
    firma_derecha = models.CharField(max_length=100, default='DRA. LIUBA ABIYOVA TÉLLEZ OSUNA')
    
    # Nuevo campo para el costo
    costo = models.FloatField(default=0.0, verbose_name='Costo de la constancia')
    
    # NUEVO CAMPO: Lema del año
    lema_anio = models.CharField(
        max_length=200, 
        default='2025, Año del Turismo Sostenible como Impulsor del Bienestar Social y Progreso',
        verbose_name='Lema del año'
    )
    
    class Meta:
        verbose_name = 'Constancia'
        verbose_name_plural = 'Constancias'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"{self.get_tipo_constancia_display()} - {self.alumno.nombre_completo}"