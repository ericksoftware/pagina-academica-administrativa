# constancias/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.certificate_list, name='certificate_list'),
    path('generar/', views.generate_certificate, name='generate_certificate'),
    path('ver/<int:certificate_id>/', views.view_certificate, name='view_certificate'),
    path('descargar/<int:certificate_id>/', views.download_certificate, name='download_certificate'),
    path('ver-pdf/<int:certificate_id>/', views.view_pdf, name='view_pdf'),
] 