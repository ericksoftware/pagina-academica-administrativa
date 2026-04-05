from django.contrib import admin
from .models import Carrera, Unidad, Materia, Calificacion, PromedioPeriodo, ActaEvaluacion


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'tipo_carrera', 'codigo', 'numero_semestres', 'plan', 'activa']
    list_filter = ['tipo_carrera', 'activa', 'plan']
    search_fields = ['nombre', 'codigo']
    list_editable = ['activa']
    ordering = ['id']


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'carrera', 'numero', 'nombre', 'materia_asignada_admin', 'estado']
    list_filter = ['carrera']
    search_fields = ['codigo', 'nombre', 'carrera__nombre']
    ordering = ['carrera', 'numero']

    def materia_asignada_admin(self, obj):
        materia = getattr(obj, 'materia', None)
        return materia.nombre if materia else 'Sin asignar'
    materia_asignada_admin.short_description = 'Materia Asignada'

    def estado(self, obj):
        return 'Ocupada' if getattr(obj, 'materia', None) else 'Disponible'
    estado.short_description = 'Estado'


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'carrera', 'semestre', 'unidad', 'parciales', 'creditos', 'horas', 'activa']
    list_filter = ['carrera', 'semestre', 'activa', 'parciales']
    search_fields = ['nombre', 'carrera__nombre', 'unidad__codigo']
    list_editable = ['activa']
    ordering = ['carrera', 'semestre', 'nombre']


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'unidad', 'tipo_calificacion', 'calificacion', 'periodo', 'fecha_registro']
    list_filter = ['periodo', 'tipo_calificacion', 'unidad__carrera']
    search_fields = ['alumno__matricula', 'alumno__nombre', 'unidad__codigo']
    readonly_fields = ['fecha_registro', 'fecha_actualizacion']
    ordering = ['-fecha_registro']


@admin.register(PromedioPeriodo)
class PromedioPeriodoAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'periodo', 'promedio_general', 'total_materias', 'materias_aprobadas']
    list_filter = ['periodo']
    search_fields = ['alumno__matricula', 'alumno__nombre']
    readonly_fields = ['fecha_calculo']
    ordering = ['alumno', 'periodo']


@admin.register(ActaEvaluacion)
class ActaEvaluacionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'materia',
        'carrera',
        'semestre',
        'grupo',
        'turno',
        'docente_identificador',
        'docente_nombre',
        'periodo',
        'estado',
        'fecha_generacion',
    ]
    list_filter = ['carrera', 'semestre', 'estado', 'periodo', 'turno']
    search_fields = [
        'materia__nombre',
        'carrera__nombre',
        'grupo',
        'periodo',
        'docente_identificador',
        'docente_nombre',
    ]
    readonly_fields = ['fecha_generacion']
    ordering = ['-fecha_generacion']