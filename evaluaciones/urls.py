from django.urls import path
from . import views

urlpatterns = [
    path('', views.grade_list, name='grade_list'),

    # Actas
    path('actas/', views.acta_list, name='acta_list'),
    path('actas/generar/', views.generate_acta, name='generate_acta'),
    path('actas/ver/<int:acta_id>/', views.view_acta, name='view_acta'),
    path('actas/descargar/<int:acta_id>/', views.download_acta, name='download_acta'),
    path('actas/preview/', views.acta_preview_data, name='acta_preview_data'),

    # Carreras
    path('carreras/', views.lista_carreras, name='lista_carreras'),
    path('carreras/agregar/', views.agregar_carrera, name='agregar_carrera'),
    path('carreras/editar/<int:carrera_id>/', views.editar_carrera, name='editar_carrera'),
    path('carreras/eliminar/<int:carrera_id>/', views.eliminar_carrera, name='eliminar_carrera'),
    path('carreras/detalle/<int:carrera_id>/', views.detalle_carrera, name='detalle_carrera'),
    path('carreras/<int:carrera_id>/materias/', views.obtener_materias_por_carrera, name='obtener_materias_por_carrera'),

    # Otras URLs
    path('importar/', views.import_grades, name='import_grades'),
    path('carreras/agregar-materia/<int:carrera_id>/', views.agregar_materia, name='agregar_materia'),
    path('carreras/eliminar-materia/<int:materia_id>/', views.eliminar_materia, name='eliminar_materia'),
    path('materia/<int:materia_id>/editar/', views.editar_materia, name='editar_materia'),
    path('materia/<int:materia_id>/cambiar-estado/', views.cambiar_estado_materia, name='cambiar_estado_materia'),
    path('materia/<int:materia_id>/datos/', views.obtener_datos_materia, name='obtener_datos_materia'),
]