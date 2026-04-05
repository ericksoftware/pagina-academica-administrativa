from functools import wraps
from django.shortcuts import render


def roles_required(*allowed_roles):
    """
    Decorador genérico para permitir acceso solo a ciertos roles.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return render(request, 'core/403.html', {
                    'exception': 'Debes iniciar sesión para acceder a esta página'
                }, status=403)

            tipo_usuario = getattr(user, 'tipo_usuario', None)

            if tipo_usuario not in allowed_roles:
                return render(request, 'core/403.html', {
                    'exception': 'No tienes permisos para acceder a esta página'
                }, status=403)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Decoradores simples
control_escolar_required = roles_required('control_escolar')
docente_required = roles_required('docente')
directivo_required = roles_required('directivo')
alumno_required = roles_required('alumno')

# Decoradores compuestos
control_escolar_or_directivo_required = roles_required('control_escolar', 'directivo')
constancias_required = roles_required('alumno', 'control_escolar', 'directivo')
actas_required = roles_required('docente', 'control_escolar', 'directivo')