from django.conf import settings
from django.db import models


class ConfiguracionSistema(models.Model):
    lema_anio = models.CharField(
        max_length=255,
        default='2025, Año del Turismo Sostenible como Impulsor del Bienestar Social y Progreso',
        verbose_name='Lema del año'
    )

    firma_izquierda_constancia = models.CharField(
        max_length=255,
        default='Vo.Bo. Subdirección Académica',
        verbose_name='Firma izquierda para constancias'
    )

    firma_derecha_constancia = models.CharField(
        max_length=255,
        default='DRA. LIUBA ABIYOVA TÉLLEZ OSUNA',
        verbose_name='Firma derecha para constancias'
    )

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configuraciones_actualizadas'
    )

    costo_constancia = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name='Costo de constancia'
    )

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración del sistema'
        verbose_name_plural = 'Configuración del sistema'

    def __str__(self):
        return 'Configuración general del sistema'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion