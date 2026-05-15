from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from django.db.models import Q
from core.decorators import control_escolar_required, directivo_required
from .models import Usuario
from django.core.exceptions import ValidationError
import os
import secrets

def validar_clave_eliminacion(request, variable_env):
    clave_configurada = os.getenv(variable_env, '').strip()
    clave_ingresada = request.POST.get('delete_password', '').strip()

    if not clave_configurada:
        messages.error(request, f'No está configurada la variable {variable_env} en el archivo .env.')
        return False

    if not clave_ingresada:
        messages.error(request, 'Debes ingresar la clave de eliminación.')
        return False

    if not secrets.compare_digest(clave_ingresada, clave_configurada):
        messages.error(request, 'Clave de eliminación incorrecta.')
        return False

    return True

@login_required
def user_list(request):
    """Lista de todos los usuarios - Solo control escolar y directivos"""
    # Verificar permisos
    if request.user.tipo_usuario not in ['control_escolar', 'directivo']:
        return render(request, 'core/403.html', status=403)
    
    # EXCLUIR usuarios de tipo 'alumno'
    usuarios = Usuario.objects.exclude(tipo_usuario='alumno').order_by('first_name', 'last_name')
    
    # Búsqueda por nombre o email
    search_query = request.GET.get('search', '')
    if search_query:
        usuarios = usuarios.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filtros
    tipo_filter = request.GET.get('tipo', '')
    estado_filter = request.GET.get('estado', '')
    
    if tipo_filter:
        usuarios = usuarios.filter(tipo_usuario=tipo_filter)
    if estado_filter:
        if estado_filter == 'activo':
            usuarios = usuarios.filter(is_active=True)
        elif estado_filter == 'inactivo':
            usuarios = usuarios.filter(is_active=False)
    
    # Paginación - 20 elementos por página
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'usuarios': page_obj,
        'tipo_filter': tipo_filter,
        'estado_filter': estado_filter,
        'search_query': search_query,
        'page_title': 'Lista de Usuarios'
    }
    return render(request, 'usuarios/user_list.html', context)

@login_required
def user_detail(request, user_id):
    """Detalle de un usuario específico - Solo control escolar y directivos"""
    # Verificar permisos
    if request.user.tipo_usuario not in ['control_escolar', 'directivo']:
        return render(request, 'core/403.html', status=403)
    
    usuario = get_object_or_404(Usuario, id=user_id)
    
    # PREVENIR acceso a usuarios tipo alumno
    if usuario.tipo_usuario == 'alumno':
        messages.error(request, 'Los usuarios tipo "Alumno" se gestionan desde el módulo de Alumnos')
        return redirect('user_list')
    
    context = {
        'usuario': usuario,
        'page_title': f'Detalle de {usuario.get_full_name()}'
    }
    return render(request, 'usuarios/user_detail.html', context)

@login_required
def user_create(request):
    """Crear nuevo usuario - Solo control escolar y directivos"""
    # Verificar permisos
    if request.user.tipo_usuario not in ['control_escolar', 'directivo']:
        return render(request, 'core/403.html', status=403)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            email_institucional = request.POST.get('email_institucional', 'Pendiente').strip()
            curp = request.POST.get('curp', 'N/A').strip().upper()
            rfc = request.POST.get('rfc', 'N/A').strip().upper()
            
            print(f"📝 CREANDO USUARIO - Email: {email_institucional}, CURP: {curp}, RFC: {rfc}")
            
            # Validaciones de duplicados ANTES de crear el objeto
            errores = []
            
            # Validar que email institucional sea único (excepto cuando es 'Pendiente' o 'N/A')
            if email_institucional not in ['Pendiente', 'N/A']:
                for usuario_existente in Usuario.objects.all():
                    if usuario_existente.email == email_institucional:
                        errores.append(f'El correo institucional "{email_institucional}" ya le pertenece al usuario: {usuario_existente.get_full_name()}')
                        break
            
            # Validar que CURP sea único (excepto cuando es 'N/A')
            if curp != 'N/A':
                for usuario_existente in Usuario.objects.all():
                    if usuario_existente.curp == curp:
                        errores.append(f'La CURP "{curp}" ya le pertenece al usuario: {usuario_existente.get_full_name()}')
                        break
            
            # Validar que RFC sea único (excepto cuando es 'N/A')
            if rfc != 'N/A':
                for usuario_existente in Usuario.objects.all():
                    if usuario_existente.rfc == rfc:
                        errores.append(f'El RFC "{rfc}" ya le pertenece al usuario: {usuario_existente.get_full_name()}')
                        break
            
            # Si hay errores, mostrar todos
            if errores:
                for error in errores:
                    messages.error(request, error)
                context = {
                    'page_title': 'Registrar Nuevo Usuario',
                    'modo': 'crear'
                }
                return render(request, 'usuarios/user_form.html', context)
            
            # Crear nuevo usuario si no hay errores
            usuario = Usuario()
            
            # Información básica
            usuario.first_name = request.POST.get('nombre', 'N/A').strip()
            apellido_paterno = request.POST.get('apellido_paterno', 'N/A').strip()
            apellido_materno = request.POST.get('apellido_materno', 'N/A').strip()
            usuario.last_name = f"{apellido_paterno} {apellido_materno}"
            
            # Información personal
            usuario.curp = curp
            usuario.rfc = rfc
            usuario.municipio_nacimiento = request.POST.get('municipio_nacimiento', 'N/A')
            
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            if fecha_nacimiento:
                usuario.fecha_nacimiento = fecha_nacimiento
            
            usuario.sexo = request.POST.get('sexo', 'N/A')
            
            # Información de usuario
            usuario.tipo_usuario = request.POST.get('tipo_usuario', 'docente')
            usuario.turno = request.POST.get('turno', 'matutino')
            
            # Información de contacto
            usuario.email = email_institucional
            usuario.username = email_institucional.split('@')[0] if email_institucional != 'Pendiente' else f"user_{Usuario.objects.count() + 1}"
            
            password = request.POST.get('password_email_institucional', '')
            if password:
                usuario.set_password(password)
            else:
                # Contraseña por defecto si no se proporciona
                usuario.set_password('N/A')
            
            usuario.email_personal = request.POST.get('email_personal', 'N/A').strip()
            usuario.telefono = request.POST.get('telefono', 'N/A')
            
            # Estado
            is_active = request.POST.get('estado', 'activo') == 'activo'
            usuario.is_active = is_active
            
            usuario.save()
            
            messages.success(request, f'Usuario {usuario.get_full_name()} creado exitosamente')
            return redirect('user_list')
            
        except ValidationError as e:
            print(f"❌ ERROR DE VALIDACIÓN EN VISTA USUARIO: {e}")
            # Capturar errores de validación del modelo
            for field, errors in e.error_dict.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
        except Exception as e:
            print(f"❌ ERROR GENERAL EN VISTA USUARIO: {e}")
            messages.error(request, f'Error al crear el usuario: {str(e)}')
    
    context = {
        'page_title': 'Registrar Nuevo Usuario',
        'modo': 'crear'
    }
    return render(request, 'usuarios/user_form.html', context)

@login_required
def user_edit(request, user_id):
    """Editar usuario existente - Solo control escolar y directivos"""
    # Verificar permisos
    if request.user.tipo_usuario not in ['control_escolar', 'directivo']:
        return render(request, 'core/403.html', status=403)
    
    usuario = get_object_or_404(Usuario, id=user_id)
    
    # PREVENIR edición de usuarios tipo alumno
    if usuario.tipo_usuario == 'alumno':
        messages.error(request, 'Los usuarios tipo "Alumno" se gestionan desde el módulo de Alumnos')
        return redirect('user_list')
    
    if request.method == 'POST':
        try:
            # Obtener nuevos datos del formulario
            nuevo_email = request.POST.get('email_institucional', 'Pendiente').strip()
            nueva_curp = request.POST.get('curp', 'N/A').strip().upper()
            nuevo_rfc = request.POST.get('rfc', 'N/A').strip().upper()
            
            print(f"📝 EDITANDO USUARIO - Nuevo Email: {nuevo_email}, Nueva CURP: {nueva_curp}, Nuevo RFC: {nuevo_rfc}")
            
            # Validaciones de duplicados ANTES de actualizar
            errores = []
            
            # Validar que email institucional sea único (excepto cuando es 'Pendiente' o 'N/A' o no cambió)
            if (nuevo_email not in ['Pendiente', 'N/A'] and 
                nuevo_email != usuario.email):
                for usuario_existente in Usuario.objects.exclude(pk=usuario.pk):
                    if usuario_existente.email == nuevo_email:
                        errores.append(f'El correo institucional "{nuevo_email}" ya le pertenece al usuario: {usuario_existente.get_full_name()}')
                        break
            
            # Validar que CURP sea único (excepto cuando es 'N/A' o no cambió)
            if nueva_curp != 'N/A' and nueva_curp != usuario.curp:
                for usuario_existente in Usuario.objects.exclude(pk=usuario.pk):
                    if usuario_existente.curp == nueva_curp:
                        errores.append(f'La CURP "{nueva_curp}" ya le pertenece al usuario: {usuario_existente.get_full_name()}')
                        break
            
            # Validar que RFC sea único (excepto cuando es 'N/A' o no cambió)
            if nuevo_rfc != 'N/A' and nuevo_rfc != usuario.rfc:
                for usuario_existente in Usuario.objects.exclude(pk=usuario.pk):
                    if usuario_existente.rfc == nuevo_rfc:
                        errores.append(f'El RFC "{nuevo_rfc}" ya le pertenece al usuario: {usuario_existente.get_full_name()}')
                        break
            
            # Si hay errores, mostrar todos
            if errores:
                for error in errores:
                    messages.error(request, error)
                return redirect('user_edit', user_id=user_id)
            
            # Actualizar información básica
            usuario.first_name = request.POST.get('nombre', 'N/A').strip()
            apellido_paterno = request.POST.get('apellido_paterno', 'N/A').strip()
            apellido_materno = request.POST.get('apellido_materno', 'N/A').strip()
            usuario.last_name = f"{apellido_paterno} {apellido_materno}"
            
            # Información personal
            usuario.curp = nueva_curp
            usuario.rfc = nuevo_rfc
            usuario.municipio_nacimiento = request.POST.get('municipio_nacimiento', 'N/A')
            
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            if fecha_nacimiento:
                usuario.fecha_nacimiento = fecha_nacimiento
            else:
                usuario.fecha_nacimiento = None
            
            usuario.sexo = request.POST.get('sexo', 'N/A')
            
            # Información de usuario
            usuario.tipo_usuario = request.POST.get('tipo_usuario', 'docente')
            usuario.turno = request.POST.get('turno', 'matutino')
            
            # Información de contacto
            usuario.email = nuevo_email
            
            password = request.POST.get('password_email_institucional', '')
            if password:
                usuario.set_password(password)
            
            usuario.email_personal = request.POST.get('email_personal', 'N/A').strip()
            usuario.telefono = request.POST.get('telefono', 'N/A')
            
            # Estado
            is_active = request.POST.get('estado', 'activo') == 'activo'
            usuario.is_active = is_active
            
            usuario.save()
            
            messages.success(request, f'Usuario {usuario.get_full_name()} actualizado exitosamente')
            return redirect('user_detail', user_id=usuario.id)
            
        except ValidationError as e:
            print(f"❌ ERROR DE VALIDACIÓN EN VISTA USUARIO: {e}")
            # Capturar errores de validación del modelo
            for field, errors in e.error_dict.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
        except Exception as e:
            print(f"❌ ERROR GENERAL EN VISTA USUARIO: {e}")
            messages.error(request, f'Error al actualizar el usuario: {str(e)}')
    
    context = {
        'usuario': usuario,
        'page_title': f'Editar {usuario.get_full_name()}',
        'modo': 'editar'
    }
    return render(request, 'usuarios/user_form.html', context)

@login_required
def user_delete(request, user_id):
    """Eliminar usuario - Solo control escolar y directivos"""
    if request.user.tipo_usuario not in ['control_escolar', 'directivo']:
        return render(request, 'core/403.html', status=403)

    usuario = get_object_or_404(Usuario, id=user_id)

    if usuario.tipo_usuario == 'alumno':
        messages.error(request, 'Los usuarios tipo "Alumno" se gestionan desde el módulo de Alumnos')
        return redirect('user_list')

    if request.method == 'POST':
        if not validar_clave_eliminacion(request, 'del_us_pass'):
            return redirect('user_detail', user_id=usuario.id)

        try:
            nombre_completo = usuario.get_full_name()
            usuario.delete()
            messages.success(request, f'Usuario {nombre_completo} eliminado exitosamente')
            return redirect('user_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar el usuario: {str(e)}')
            return redirect('user_detail', user_id=usuario.id)

    context = {
        'usuario': usuario,
        'page_title': f'Eliminar {usuario.get_full_name()}'
    }
    return render(request, 'usuarios/user_confirm_delete.html', context)