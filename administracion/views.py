from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import ConfiguracionSistema


def puede_acceder_administracion(user):
    if not user.is_authenticated:
        return False

    tipo_usuario = getattr(user, 'tipo_usuario', None)

    return (
        user.is_superuser
        or user.is_staff
        or tipo_usuario == 'administrador'
        or tipo_usuario == 'control_escolar'
    )


@login_required
def administration_home(request):
    if not puede_acceder_administracion(request.user):
        messages.error(request, 'No tienes permisos para acceder al módulo de Administración.')
        return redirect('dashboard')

    configuracion = ConfiguracionSistema.obtener()

    if request.method == 'POST':
        lema_anio = request.POST.get('lema_anio', '').strip()
        firma_izquierda_constancia = request.POST.get('firma_izquierda_constancia', '').strip()
        firma_derecha_constancia = request.POST.get('firma_derecha_constancia', '').strip()

        if not lema_anio:
            messages.error(request, 'El lema del año no puede estar vacío.')
            return redirect('administration_home')

        if not firma_izquierda_constancia:
            messages.error(request, 'La firma izquierda no puede estar vacía.')
            return redirect('administration_home')

        if not firma_derecha_constancia:
            messages.error(request, 'La firma derecha no puede estar vacía.')
            return redirect('administration_home')

        configuracion.lema_anio = lema_anio
        configuracion.firma_izquierda_constancia = firma_izquierda_constancia
        configuracion.firma_derecha_constancia = firma_derecha_constancia
        configuracion.actualizado_por = request.user
        configuracion.save()

        messages.success(request, 'Configuración actualizada correctamente.')
        return redirect('administration_home')

    context = {
        'configuracion': configuracion,
        'page_title': 'Administración'
    }

    return render(request, 'administracion/administration_home.html', context)