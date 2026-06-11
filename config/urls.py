# config/urls.py - ACTUALIZADO
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    # Administración de Django
    path('admin/', admin.site.urls),
    
    # Página principal
    path('', core_views.home_redirect, name='home'),
    
    # Autenticación simple
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    # Usar vista personalizada para logout que acepta GET
    path('logout/', core_views.custom_logout, name='logout'),
    
    # Incluir URLs de las apps
    path('', include('core.urls')),           # Dashboard
    path('usuarios/', include('usuarios.urls')), # NUEVO: Gestión de usuarios
    path('alumnos/', include('alumnos.urls')),    # Alumnos (solo control escolar)
    path('constancias/', include('constancias.urls')), # Constancias (solo control escolar)
    path('evaluaciones/', include('evaluaciones.urls')), # Evaluaciones (solo control escolar)
    path('administracion/', include('administracion.urls')),
]

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Personalizar títulos del admin
admin.site.site_header = f"{getattr(settings, 'SITE_SHORT_NAME', 'WASISV')} - Administración"
admin.site.site_title = f"Sistema de Gestión {getattr(settings, 'SITE_SHORT_NAME', 'WASISV')}"
admin.site.index_title = "Panel de Administración"