from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q
from core.decorators import control_escolar_or_directivo_required
from .models import Alumno, normalizar_email_institucional
from evaluaciones.models import Carrera, Calificacion, Materia, Unidad
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
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

@control_escolar_or_directivo_required
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

@control_escolar_or_directivo_required
def student_detail(request, student_id):
    """Detalle de un alumno específico - Solo control escolar"""
    alumno = get_object_or_404(Alumno, id=student_id)

    materias_carrera = []
    materias_modal = []
    resumen_materias = []
    max_parciales = 0
    componentes_capturados = 0
    componentes_totales = 0
    promedio_general = None

    calificaciones = Calificacion.objects.filter(
        alumno=alumno
    ).select_related(
        'unidad',
        'unidad__carrera',
        'unidad__materia'
    ).order_by(
        'unidad__materia__semestre',
        'unidad__codigo',
        'tipo_calificacion',
        'numero_parcial'
    )

    if alumno.carrera:
        materias_carrera = Materia.objects.filter(
            carrera=alumno.carrera,
            activa=True
        ).select_related('unidad').order_by('semestre', 'nombre')

        max_parciales = max((materia.parciales for materia in materias_carrera), default=0)

        mapa_calificaciones = {}
        for calif in calificaciones:
            if calif.tipo_calificacion == 'parcial':
                mapa_calificaciones[(calif.unidad_id, 'parcial', calif.numero_parcial)] = calif
            elif calif.tipo_calificacion == 'evidencia_final':
                mapa_calificaciones[(calif.unidad_id, 'evidencia_final', None)] = calif

        valores_globales = []

        for materia in materias_carrera:
            parciales_render = []
            valores_materia = []

            for n in range(1, max_parciales + 1):
                if n <= materia.parciales:
                    calif = mapa_calificaciones.get((materia.unidad_id, 'parcial', n))
                    valor = calif.calificacion if calif else ''
                    parciales_render.append({
                        'habilitado': True,
                        'numero': n,
                        'valor': valor
                    })
                    if calif and calif.calificacion is not None:
                        valores_materia.append(float(calif.calificacion))
                        valores_globales.append(float(calif.calificacion))
                else:
                    parciales_render.append({
                        'habilitado': False,
                        'numero': n,
                        'valor': ''
                    })

            evidencia = mapa_calificaciones.get((materia.unidad_id, 'evidencia_final', None))
            evidencia_valor = evidencia.calificacion if evidencia else ''

            if evidencia and evidencia.calificacion is not None:
                valores_materia.append(float(evidencia.calificacion))
                valores_globales.append(float(evidencia.calificacion))

            promedio_materia = round(sum(valores_materia) / len(valores_materia), 2) if valores_materia else None
            ultima_fecha = None
            if evidencia and evidencia.fecha_registro:
                ultima_fecha = evidencia.fecha_registro
            else:
                fechas = [
                    mapa_calificaciones[(materia.unidad_id, 'parcial', n)].fecha_registro
                    for n in range(1, materia.parciales + 1)
                    if (materia.unidad_id, 'parcial', n) in mapa_calificaciones
                ]
                ultima_fecha = max(fechas) if fechas else None

            materias_modal.append({
                'materia': materia,
                'unidad': materia.unidad,
                'parciales_render': parciales_render,
                'evidencia_final': evidencia_valor
            })

            resumen_materias.append({
                'materia': materia,
                'unidad': materia.unidad,
                'promedio': promedio_materia,
                'fecha': ultima_fecha
            })

        componentes_totales = sum(materia.parciales + 1 for materia in materias_carrera)
        componentes_capturados = len(valores_globales)
        promedio_general = round(sum(valores_globales) / len(valores_globales), 2) if valores_globales else None

    context = {
        'alumno': alumno,
        'calificaciones': calificaciones,
        'materias_carrera': materias_carrera,
        'materias_modal': materias_modal,
        'resumen_materias': resumen_materias,
        'max_parciales_range': range(1, max_parciales + 1),
        'materias_calificadas': componentes_capturados,
        'materias_por_calificar': max(componentes_totales - componentes_capturados, 0),
        'promedio_general': promedio_general,
        'page_title': f'Detalle de {alumno.nombre_completo()}'
    }
    return render(request, 'alumnos/student_detail.html', context)

@control_escolar_or_directivo_required
def student_create(request):
    """Crear nuevo alumno - Solo control escolar"""
    carreras = Carrera.objects.all()
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            matricula = request.POST.get('matricula', 'PENDIENTE').strip().upper()
            curp = request.POST.get('curp', 'N/A').strip().upper()
            rfc = request.POST.get('rfc', 'N/A').strip().upper()
            email_institucional = normalizar_email_institucional(
                request.POST.get('email_institucional', 'PENDIENTE')
            )
            
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
            
            if email_institucional not in ['PENDIENTE', 'N/A']:
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

@control_escolar_or_directivo_required
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
            nuevo_email_institucional = normalizar_email_institucional(
                request.POST.get('email_institucional', 'PENDIENTE')
            )
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
            
            if (nuevo_email_institucional not in ['PENDIENTE', 'N/A'] and 
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

@control_escolar_or_directivo_required
def student_delete(request, student_id):
    """Eliminar alumno - Solo control escolar y directivos"""
    alumno = get_object_or_404(Alumno, id=student_id)

    if request.method == 'POST':
        if not validar_clave_eliminacion(request, 'del_al_pass'):
            return redirect('student_detail', student_id=alumno.id)

        try:
            nombre_completo = alumno.nombre_completo()
            alumno.delete()
            messages.success(request, f'Alumno {nombre_completo} eliminado exitosamente')
            return redirect('student_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar el alumno: {str(e)}')
            return redirect('student_detail', student_id=alumno.id)

    context = {
        'alumno': alumno,
        'page_title': f'Eliminar {alumno.nombre_completo()}'
    }
    return render(request, 'alumnos/student_confirm_delete.html', context)

@control_escolar_or_directivo_required
def student_update_grades(request, student_id):
    alumno = get_object_or_404(Alumno, id=student_id)

    if request.method == 'POST':
        try:
            periodo = request.POST.get('periodo', f"2025-{alumno.semestre_actual}")
            campos = [key for key in request.POST.keys() if key.startswith('nota__')]

            for campo in campos:
                partes = campo.split('__')
                # nota__unidad_id__parcial__1
                # nota__unidad_id__evidencia_final
                if len(partes) < 3:
                    continue

                unidad_id = int(partes[1])
                tipo = partes[2]
                numero_parcial = int(partes[3]) if tipo == 'parcial' and len(partes) == 4 else None
                valor = request.POST.get(campo, '').strip()

                unidad = Unidad.objects.select_related('materia').get(id=unidad_id, carrera=alumno.carrera)
                materia = getattr(unidad, 'materia', None)

                if not materia:
                    continue

                if tipo == 'parcial' and numero_parcial and numero_parcial > materia.parciales:
                    continue

                filtros = {
                    'alumno': alumno,
                    'unidad': unidad,
                    'periodo': periodo,
                    'tipo_calificacion': tipo,
                    'numero_parcial': numero_parcial if tipo == 'parcial' else None,
                }

                if not valor or valor.lower() == 'n/a':
                    Calificacion.objects.filter(**filtros).delete()
                    continue

                try:
                    calificacion_decimal = Decimal(valor)
                except InvalidOperation:
                    continue

                Calificacion.objects.update_or_create(
                    **filtros,
                    defaults={
                        'calificacion': calificacion_decimal,
                    }
                )

            messages.success(request, f'Calificaciones de {alumno.nombre_completo()} actualizadas exitosamente')

        except Exception as e:
            messages.error(request, f'Error al actualizar las calificaciones: {str(e)}')

    return redirect('student_detail', student_id=student_id)