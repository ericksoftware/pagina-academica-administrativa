from django.contrib import admin
from .models import Constancia


@admin.register(Constancia)
class ConstanciaAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'get_tipo_constancia_display', 'fecha_emision', 'estado', 'costo']
    list_filter = ['tipo_constancia', 'estado', 'fecha_emision']
    search_fields = ['alumno__nombre', 'alumno__apellido_paterno', 'alumno__apellido_materno']
    ordering = ['-fecha_generacion']
    readonly_fields = ['lema_anio']

    def get_tipo_constancia_display(self, obj):
        return obj.get_tipo_constancia_display()

    get_tipo_constancia_display.short_description = 'Tipo de Constancia'