from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q
from core.decorators import control_escolar_required
from .models import Alumno
from evaluaciones.models import Carrera, Calificacion, Materia, Unidad
from django.db import IntegrityError
from django.core.exceptions import ValidationError

@control_escolar_required
def student_list(request):
    """Lista de todos los alumnos - Solo control escolar"""
    alumnos = Alumno.objects.all().order_by('grupo', 'apellido_paterno', 'apellido_materno', 'nombre')
    
    # Búsqueda por nombre o matrícula
    search_query = request.GET.get('search', '')
    if search_query:
        alumnos = alumnos.filter(
            Q(nombre__icontains=search_query) |
            Q(apellido_paterno__icontains=search_query) |
            Q(apellido_materno__icontains=search_query) |
            Q(matricula__icontains=search_query)
        )
    
    # Filtros
    estado_filter = request.GET.get('estado', '')
    carrera_filter = request.GET.get('carrera', '')
    grupo_filter = request.GET.get('grupo', '')
    if grupo_filter:
        alumnos = alumnos.filter(grupo=grupo_filter)
    
    if estado_filter:
        alumnos = alumnos.filter(estado=estado_filter)
    if carrera_filter:
        alumnos = alumnos.filter(carrera_id=carrera_filter)
    
    carreras = Carrera.objects.all()
    
    # Paginación - 20 elementos por página
    paginator = Paginator(alumnos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'alumnos': page_obj,
        'carreras': carreras,
        'estado_filter': estado_filter,
        'carrera_filter': carrera_filter,
        'grupo_filter': grupo_filter,
        'search_query': search_query,
        'page_title': 'Lista de Alumnos'
    }
    return render(request, 'alumnos/student_list.html', context)

@control_escolar_required
def student_detail(request, student_id):
    """Detalle de un alumno específico - Solo control escolar"""
    alumno = get_object_or_404(Alumno, id=student_id)
    calificaciones = Calificacion.objects.filter(alumno=alumno).select_related('unidad', 'unidad__carrera')
    
    # DEBUG: Verificar calificaciones cargadas
    print(f"🔍 DEBUG STUDENT_DETAIL - Alumno: {alumno.nombre_completo()}")
    print(f"🔍 DEBUG STUDENT_DETAIL - Calificaciones cargadas: {calificaciones.count()}")
    for calif in calificaciones:
        print(f"🔍 DEBUG STUDENT_DETAIL - {calif.unidad.codigo}: {calif.calificacion}")
    
    # Obtener unidades de la carrera del alumno
    unidades_carrera = []
    materias_carrera = []
    materias_calificadas = 0
    materias_por_calificar = 0
    promedio_general = None
    
    if alumno.carrera:
        # Obtener TODAS las unidades de la carrera
        unidades_carrera = Unidad.objects.filter(
            carrera=alumno.carrera
        ).prefetch_related('materias').order_by('numero')
        
        # Obtener TODAS las materias de la carrera (para mostrar en el modal)
        materias_carrera = Materia.objects.filter(
            carrera=alumno.carrera
        ).prefetch_related('unidades').order_by('semestre', 'nombre')
        
        # Calcular estadísticas por UNIDADES
        materias_calificadas = calificaciones.count()
        materias_por_calificar = unidades_carrera.count() - materias_calificadas
        
        # Promedio general (de todas las unidades calificadas)
        if calificaciones.exists():
            suma_calificaciones = sum(calif.calificacion for calif in calificaciones if calif.calificacion)
            promedio_general = round(suma_calificaciones / calificaciones.count(), 2)
    
    context = {
        'alumno': alumno,
        'calificaciones': calificaciones,
        'unidades_carrera': unidades_carrera,
        'materias_carrera': materias_carrera,
        'materias_calificadas': materias_calificadas,
        'materias_por_calificar': materias_por_calificar,
        'promedio_general': promedio_general,
        'page_title': f'Detalle de {alumno.nombre_completo()}'
    }
    return render(request, 'alumnos/student_detail.html', context)

@control_escolar_required
def student_create(request):
    """Crear nuevo alumno - Solo control escolar"""
    carreras = Carrera.objects.all()
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            matricula = request.POST.get('matricula', 'PENDIENTE').strip().upper()
            curp = request.POST.get('curp', 'N/A').strip().upper()
            rfc = request.POST.get('rfc', 'N/A').strip().upper()
            email_institucional = request.POST.get('email_institucional', 'Pendiente').strip()
            
            # Validaciones de duplicados - BUSCANDO EN TODOS LOS REGISTROS
            errores = []
            
            # Validar matrícula (esto funciona porque no está cifrada)
            if matricula != 'PENDIENTE':
                if Alumno.objects.filter(matricula=matricula).exists():
                    alumno_existente = Alumno.objects.get(matricula=matricula)
                    errores.append(f'La matrícula "{matricula}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
            
            # Para campos cifrados, buscar en TODOS los registros
            if curp != 'N/A':
                for alumno_existente in Alumno.objects.all():
                    if alumno_existente.curp == curp:  # Comparar valores descifrados
                        errores.append(f'La CURP "{curp}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
                        break
            
            if rfc != 'N/A':
                for alumno_existente in Alumno.objects.all():
                    if alumno_existente.rfc == rfc:  # Comparar valores descifrados
                        errores.append(f'El RFC "{rfc}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
                        break
            
            if email_institucional not in ['Pendiente', 'N/A']:
                if not email_institucional.endswith('@edubc.mx'):
                    errores.append('El correo institucional debe terminar con @edubc.mx')
                else:
                    for alumno_existente in Alumno.objects.all():
                        if alumno_existente.email_institucional == email_institucional:
                            errores.append(f'El correo institucional "{email_institucional}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
                            break
            
            # Validar grupo
            grupo = request.POST.get('grupo', '101').strip()
            if not grupo or len(grupo) != 3 or not grupo.isdigit():
                messages.error(request, 'El grupo debe tener exactamente 3 dígitos numéricos')
                context = {
                    'carreras': carreras,
                    'page_title': 'Registrar Nuevo Alumno',
                    'modo': 'crear',
                    'alumno': request.POST
                }
                return render(request, 'alumnos/student_form.html', context)
            
            # Si hay errores, mostrar todos
            if errores:
                for error in errores:
                    messages.error(request, error)
                context = {
                    'carreras': carreras,
                    'page_title': 'Registrar Nuevo Alumno',
                    'modo': 'crear',
                    'alumno': request.POST
                }
                return render(request, 'alumnos/student_form.html', context)
            
            # Crear nuevo alumno si no hay errores
            alumno = Alumno()
            
            # Información básica
            alumno.matricula = matricula
            alumno.grupo = grupo
            alumno.curp = curp
            alumno.rfc = rfc
            alumno.nombre = request.POST.get('nombre', 'N/A').strip()
            alumno.apellido_paterno = request.POST.get('apellido_paterno', 'N/A').strip()
            alumno.apellido_materno = request.POST.get('apellido_materno', 'N/A').strip()
            
            # Información personal
            alumno.municipio_nacimiento = request.POST.get('municipio_nacimiento', 'N/A')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            if fecha_nacimiento:
                alumno.fecha_nacimiento = fecha_nacimiento
            alumno.sexo = request.POST.get('sexo', 'N/A')
            
            # Información académica previa
            alumno.institucion_procedencia = request.POST.get('institucion_procedencia', 'N/A')
            alumno.municipio_institucion = request.POST.get('municipio_institucion', 'N/A')
            alumno.clave_escuela = request.POST.get('clave_escuela', 'N/A')
            fecha_terminacion = request.POST.get('fecha_terminacion_prepa')
            if fecha_terminacion:
                alumno.fecha_terminacion_prepa = fecha_terminacion
            promedio_prepa = request.POST.get('promedio_prepa')
            if promedio_prepa:
                alumno.promedio_prepa = float(promedio_prepa)
            alumno.constancia_terminacion = request.POST.get('constancia_terminacion', 'no')
            
            # Información académica actual
            carrera_id = request.POST.get('carrera')
            if carrera_id:
                alumno.carrera = Carrera.objects.get(id=carrera_id)
            promedio_anterior = request.POST.get('promedio_semestre_anterior')
            if promedio_anterior:
                alumno.promedio_semestre_anterior = float(promedio_anterior)
            alumno.semestre_actual = request.POST.get('semestre_actual', 1)
            alumno.turno = request.POST.get('turno', 'matutino')
            alumno.plan = request.POST.get('plan', 2023)
            
            # Información de contacto
            alumno.email_institucional = email_institucional
            alumno.password_email_institucional = request.POST.get('password_email_institucional', 'N/A')
            alumno.email_personal = request.POST.get('email_personal', 'N/A').strip()
            alumno.telefono = request.POST.get('telefono', 'N/A')
            
            # Estado
            alumno.estado = request.POST.get('estado', 'activo')
            
            # GUARDAR - esto ejecutará las validaciones del modelo
            alumno.save()
            
            messages.success(request, f'Alumno {alumno.nombre_completo()} creado exitosamente')
            print("✅ ALUMNO CREADO EXITOSAMENTE")
            return redirect('student_list')
            
        except ValidationError as e:
            print(f"❌ ERROR DE VALIDACIÓN EN VISTA: {e}")
            # Capturar errores de validación del modelo
            for field, errors in e.error_dict.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
            
            # Volver a mostrar el formulario con los datos
            context = {
                'carreras': carreras,
                'page_title': 'Registrar Nuevo Alumno',
                'modo': 'crear',
                'alumno': request.POST  # Pasar los datos del POST
            }
            return render(request, 'alumnos/student_form.html', context)
            
        except Exception as e:
            print(f"❌ ERROR GENERAL EN VISTA: {e}")
            messages.error(request, f'Error al crear el alumno: {str(e)}')
            
            # Volver a mostrar el formulario con los datos
            context = {
                'carreras': carreras,
                'page_title': 'Registrar Nuevo Alumno',
                'modo': 'crear',
                'alumno': request.POST  # Pasar los datos del POST
            }
            return render(request, 'alumnos/student_form.html', context)
    
    # GET request - mostrar formulario vacío
    context = {
        'carreras': carreras,
        'page_title': 'Registrar Nuevo Alumno',
        'modo': 'crear'
    }
    return render(request, 'alumnos/student_form.html', context)

@control_escolar_required
def student_edit(request, student_id):
    """Editar alumno existente - Solo control escolar"""
    alumno = get_object_or_404(Alumno, id=student_id)
    carreras = Carrera.objects.all()
    
    if request.method == 'POST':
        try:
            # Obtener nuevos datos del formulario
            nueva_matricula = request.POST.get('matricula', 'PENDIENTE').strip().upper()
            nueva_curp = request.POST.get('curp', 'N/A').strip().upper()
            nuevo_rfc = request.POST.get('rfc', 'N/A').strip().upper()
            nuevo_email_institucional = request.POST.get('email_institucional', 'Pendiente').strip()
            nuevo_grupo = request.POST.get('grupo', '000').strip()
            
            # Validaciones de duplicados - BUSCANDO EN TODOS LOS REGISTROS
            errores = []
            
            # Validar matrícula
            if (nueva_matricula != 'PENDIENTE' and 
                nueva_matricula != alumno.matricula):
                if Alumno.objects.filter(matricula=nueva_matricula).exists():
                    alumno_existente = Alumno.objects.get(matricula=nueva_matricula)
                    errores.append(f'La matrícula "{nueva_matricula}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
            
            # Para campos cifrados, buscar en TODOS los registros (excepto el actual)
            if nueva_curp != 'N/A' and nueva_curp != alumno.curp:
                for alumno_existente in Alumno.objects.exclude(pk=alumno.pk):
                    if alumno_existente.curp == nueva_curp:
                        errores.append(f'La CURP "{nueva_curp}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
                        break
            
            if nuevo_rfc != 'N/A' and nuevo_rfc != alumno.rfc:
                for alumno_existente in Alumno.objects.exclude(pk=alumno.pk):
                    if alumno_existente.rfc == nuevo_rfc:
                        errores.append(f'El RFC "{nuevo_rfc}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
                        break
            
            if (nuevo_email_institucional not in ['Pendiente', 'N/A'] and 
                nuevo_email_institucional != alumno.email_institucional):
                if not nuevo_email_institucional.endswith('@edubc.mx'):
                    errores.append('El correo institucional debe terminar con @edubc.mx')
                else:
                    for alumno_existente in Alumno.objects.exclude(pk=alumno.pk):
                        if alumno_existente.email_institucional == nuevo_email_institucional:
                            errores.append(f'El correo institucional "{nuevo_email_institucional}" ya le pertenece al alumno: {alumno_existente.nombre_completo()}')
                            break
            
            if not nuevo_grupo or len(nuevo_grupo) != 3 or not nuevo_grupo.isdigit():
                messages.error(request, 'El grupo debe tener exactamente 3 dígitos numéricos')
                return redirect('student_edit', student_id=student_id)
            
            # Si hay errores, mostrar todos
            if errores:
                for error in errores:
                    messages.error(request, error)
                return redirect('student_edit', student_id=student_id)
            
            # Actualizar información
            alumno.matricula = nueva_matricula
            alumno.curp = nueva_curp
            alumno.rfc = nuevo_rfc
            alumno.apellido_paterno = request.POST.get('apellido_paterno', 'N/A').strip()
            alumno.apellido_materno = request.POST.get('apellido_materno', 'N/A').strip()
            alumno.grupo = nuevo_grupo
            
            # Información personal
            alumno.municipio_nacimiento = request.POST.get('municipio_nacimiento', 'N/A')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            if fecha_nacimiento:
                alumno.fecha_nacimiento = fecha_nacimiento
            else:
                alumno.fecha_nacimiento = None
            alumno.sexo = request.POST.get('sexo', 'N/A')
            
            # Información académica previa
            alumno.institucion_procedencia = request.POST.get('institucion_procedencia', 'N/A')
            alumno.municipio_institucion = request.POST.get('municipio_institucion', 'N/A')
            alumno.clave_escuela = request.POST.get('clave_escuela', 'N/A')
            fecha_terminacion = request.POST.get('fecha_terminacion_prepa')
            if fecha_terminacion:
                alumno.fecha_terminacion_prepa = fecha_terminacion
            else:
                alumno.fecha_terminacion_prepa = None
            promedio_prepa = request.POST.get('promedio_prepa')
            if promedio_prepa:
                alumno.promedio_prepa = float(promedio_prepa)
            else:
                alumno.promedio_prepa = None
            alumno.constancia_terminacion = request.POST.get('constancia_terminacion', 'no')
            
            # Información académica actual
            carrera_id = request.POST.get('carrera')
            if carrera_id:
                alumno.carrera = Carrera.objects.get(id=carrera_id)
            else:
                alumno.carrera = None
            promedio_anterior = request.POST.get('promedio_semestre_anterior')
            if promedio_anterior:
                alumno.promedio_semestre_anterior = float(promedio_anterior)
            else:
                alumno.promedio_semestre_anterior = None
            alumno.semestre_actual = request.POST.get('semestre_actual', 1)
            alumno.turno = request.POST.get('turno', 'matutino')
            alumno.plan = request.POST.get('plan', 2023)
            
            # Información de contacto
            alumno.email_institucional = nuevo_email_institucional
            alumno.password_email_institucional = request.POST.get('password_email_institucional', 'N/A')
            alumno.email_personal = request.POST.get('email_personal', 'N/A').strip()
            alumno.telefono = request.POST.get('telefono', 'N/A')
            
            # Estado
            alumno.estado = request.POST.get('estado', 'activo')
            
            # GUARDAR - esto ejecutará las validaciones del modelo
            alumno.save()
            
            messages.success(request, f'Alumno {alumno.nombre_completo()} actualizado exitosamente')
            print("✅ ALUMNO ACTUALIZADO EXITOSAMENTE")
            return redirect('student_detail', student_id=alumno.id)
            
        except ValidationError as e:
            print(f"❌ ERROR DE VALIDACIÓN EN VISTA: {e}")
            # Capturar errores de validación del modelo
            for field, errors in e.error_dict.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
        except Exception as e:
            print(f"❌ ERROR GENERAL EN VISTA: {e}")
            messages.error(request, f'Error al actualizar el alumno: {str(e)}')
    
    context = {
        'alumno': alumno,
        'carreras': carreras,
        'page_title': f'Editar {alumno.nombre_completo()}',
        'modo': 'editar'
    }
    return render(request, 'alumnos/student_form.html', context)

@control_escolar_required
def student_delete(request, student_id):
    """Eliminar alumno - Solo control escolar"""
    alumno = get_object_or_404(Alumno, id=student_id)
    
    if request.method == 'POST':
        try:
            nombre_completo = alumno.nombre_completo()
            alumno.delete()
            messages.success(request, f'Alumno {nombre_completo} eliminado exitosamente')
            return redirect('student_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar el alumno: {str(e)}')
    
    context = {
        'alumno': alumno,
        'page_title': f'Eliminar {alumno.nombre_completo()}'
    }
    return render(request, 'alumnos/student_confirm_delete.html', context)

@control_escolar_required
def student_update_grades(request, student_id):
    """Actualizar calificaciones del alumno por UNIDAD - Solo control escolar"""
    alumno = get_object_or_404(Alumno, id=student_id)
    
    if request.method == 'POST':
        try:
            print(f"🔍 DEBUG - Procesando calificaciones por UNIDAD para alumno: {alumno.nombre_completo()}")
            
            # Obtener TODOS los campos del POST que empiecen con "calificacion_"
            campos_calificacion = [key for key in request.POST.keys() if key.startswith('calificacion_')]
            print(f"🔍 DEBUG - Campos encontrados en POST: {len(campos_calificacion)}")
            
            for campo in campos_calificacion:
                # Extraer el ID de la UNIDAD del nombre del campo
                unidad_id = campo.replace('calificacion_', '')
                calificacion_valor = request.POST.get(campo, '').strip()
                
                print(f"🔍 DEBUG - Procesando: {campo} = '{calificacion_valor}'")
                
                try:
                    unidad = Unidad.objects.get(id=unidad_id)
                    
                    # Si el campo está vacío o es "N/A", eliminar la calificación existente
                    if not calificacion_valor or calificacion_valor.lower() == 'n/a':
                        deleted_count, _ = Calificacion.objects.filter(
                            alumno=alumno, 
                            unidad=unidad
                        ).delete()
                        print(f"🔍 DEBUG - Calificación eliminada para {unidad.codigo}: {deleted_count}")
                    else:
                        # Convertir a decimal y guardar/actualizar
                        calificacion_decimal = float(calificacion_valor)
                        
                        # Crear o actualizar calificación por UNIDAD
                        calificacion, created = Calificacion.objects.update_or_create(
                            alumno=alumno,
                            unidad=unidad,
                            defaults={
                                'calificacion': calificacion_decimal,
                                'periodo': f"2025-{alumno.semestre_actual}"
                            }
                        )
                        
                        print(f"🔍 DEBUG - Calificación {'CREADA' if created else 'ACTUALIZADA'} para {unidad.codigo}: {calificacion.calificacion}")
                        
                except Unidad.DoesNotExist:
                    print(f"❌ ERROR - Unidad con ID {unidad_id} no existe")
                    continue
                except ValueError as e:
                    print(f"❌ ERROR en valor: {e}")
                    continue
            
            # VERIFICAR DESPUÉS DE GUARDAR
            calificaciones_despues = Calificacion.objects.filter(alumno=alumno)
            print(f"🔍 DEBUG - Calificaciones después de guardar: {calificaciones_despues.count()}")
            for calif in calificaciones_despues:
                print(f"🔍 DEBUG - Calificación guardada: {calif.unidad.codigo} = {calif.calificacion}")
            
            messages.success(request, f'Calificaciones de {alumno.nombre_completo()} actualizadas exitosamente')
            
        except Exception as e:
            print(f"❌ ERROR general: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error al actualizar las calificaciones: {str(e)}')
    
    return redirect('student_detail', student_id=student_id)