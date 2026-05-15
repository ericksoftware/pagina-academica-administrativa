from django.contrib import admin

from .models import ConfiguracionSistema


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = [
        'lema_anio',
        'firma_izquierda_constancia',
        'firma_derecha_constancia',
        'actualizado_por',
        'actualizado_en'
    ]

    readonly_fields = ['actualizado_en']

    def has_add_permission(self, request):
        return not ConfiguracionSistema.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False