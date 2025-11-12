# evaluaciones/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse  
from core.decorators import control_escolar_required
from .models import Calificacion, Materia, ActaEvaluacion, Carrera, Unidad
from alumnos.models import Alumno
import pandas as pd
import os
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from django.db import models
from django.views.decorators.clickjacking import xframe_options_exempt
from django.templatetags.static import static

@control_escolar_required
def grade_list(request):
    """Lista de calificaciones"""
    calificaciones = Calificacion.objects.all().select_related('alumno', 'materia')
    
    # Filtrar por parámetros GET
    carrera = request.GET.get('carrera')
    semestre = request.GET.get('semestre')
    materia_id = request.GET.get('materia')
    
    if carrera:
        calificaciones = calificaciones.filter(alumno__carrera=carrera)
    if semestre:
        calificaciones = calificaciones.filter(alumno__semestre_actual=semestre)
    if materia_id:
        calificaciones = calificaciones.filter(materia_id=materia_id)
    
    materias = Materia.objects.all()
    
    context = {
        'calificaciones': calificaciones,
        'materias': materias,
        'carrera_filter': carrera,
        'semestre_filter': semestre,
        'materia_filter': materia_id,
        'page_title': 'Lista de Calificaciones'
    }
    return render(request, 'evaluaciones/grade_list.html', context)

@control_escolar_required
def import_grades(request):
    if request.method == 'POST':
        try:
            excel_file = request.FILES['excel_file']
            carrera = request.POST['carrera']
            semestre = request.POST['semestre']
            
            # Leer el archivo Excel
            df = pd.read_excel(excel_file)
            
            # Validar columnas requeridas
            required_columns = ['MATRICULA', 'MATERIA', 'CALIFICACION']
            for col in required_columns:
                if col not in df.columns:
                    messages.error(request, f'Falta la columna requerida: {col}')
                    return redirect('import_grades')
            
            # Procesar cada fila
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    matricula = str(row['MATRICULA']).strip()
                    nombre_materia = str(row['MATERIA']).strip()  # Cambiado a nombre en lugar de código
                    calificacion_val = float(row['CALIFICACION'])
                    
                    alumno = Alumno.objects.get(matricula=matricula)
                    materia = Materia.objects.get(nombre=nombre_materia)
                    
                    # Crear o actualizar calificación
                    calificacion, created = Calificacion.objects.update_or_create(
                        alumno=alumno,
                        materia=materia,
                        periodo=f"2025-{semestre}",
                        defaults={'calificacion': calificacion_val}
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error en fila {index + 2}: {e}")
            
            messages.success(request, f'Importación completada: {success_count} registros exitosos, {error_count} errores')
            return redirect('grade_list')
            
        except Exception as e:
            messages.error(request, f'Error al importar el archivo: {str(e)}')
    
    # Si es GET, mostrar el formulario
    context = {
        'page_title': 'Importar Calificaciones'
    }
    return render(request, 'evaluaciones/import_grades.html', context)

@control_escolar_required
def generate_transcript(request):
    """Generar acta de evaluación"""
    if request.method == 'POST':
        try:
            carrera = request.POST['carrera']
            semestre = request.POST['semestre']
            grupo = request.POST['grupo']
            materia_id = request.POST['materia']
            periodo = request.POST['periodo']
            fecha_emision = request.POST['fecha_emision']
            
            materia = Materia.objects.get(id=materia_id)
            
            # Crear el acta
            acta = ActaEvaluacion.objects.create(
                carrera_id=carrera,
                semestre=semestre,
                grupo=grupo,
                materia=materia,
                periodo=periodo,
                fecha_emision=fecha_emision,
                estado='generada'
            )
            
            # Obtener calificaciones para este acta
            calificaciones = Calificacion.objects.filter(
                alumno__carrera=carrera,
                alumno__semestre_actual=semestre,
                materia=materia,
                periodo=periodo
            ).select_related('alumno')
            
            # Generar PDF
            html_string = render_to_string('evaluaciones/transcript_template.html', {
                'acta': acta,
                'calificaciones': calificaciones,
                'total_alumnos': calificaciones.count(),
                'promedio_grupo': calificaciones.aggregate(avg=models.Avg('calificacion'))['calificacion__avg'] or 0
            })
            
            html = HTML(string=html_string)
            result = html.write_pdf()
            
            # Guardar el PDF
            pdf_path = f'actas/{acta.id}_{acta.materia.nombre.replace(" ", "_")}_{acta.grupo}.pdf'
            full_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(result)
            
            acta.archivo_pdf = pdf_path
            acta.save()
            
            messages.success(request, f'Acta generada exitosamente para {materia.nombre}')
            return redirect('view_transcript', transcript_id=acta.id)
            
        except Exception as e:
            messages.error(request, f'Error al generar el acta: {str(e)}')
    
    # Si es GET, mostrar el formulario
    materias = Materia.objects.all()
    
    context = {
        'materias': materias,
        'page_title': 'Generar Acta de Evaluación'
    }
    return render(request, 'evaluaciones/generate_transcript.html', context)

@control_escolar_required
def view_transcript(request, transcript_id):
    """Ver un acta de evaluación específica"""
    acta = get_object_or_404(ActaEvaluacion, id=transcript_id)
    calificaciones = Calificacion.objects.filter(
        alumno__carrera=acta.carrera,
        alumno__semestre_actual=acta.semestre,
        materia=acta.materia,
        periodo=acta.periodo
    ).select_related('alumno')
    
    context = {
        'acta': acta,
        'calificaciones': calificaciones,
        'total_alumnos': calificaciones.count(),
        'promedio_grupo': calificaciones.aggregate(avg=models.Avg('calificacion'))['calificacion__avg'] or 0,
        'page_title': f'Acta de {acta.materia.nombre}'
    }
    return render(request, 'evaluaciones/view_transcript.html', context)

@control_escolar_required
def download_transcript(request, transcript_id):
    """Descargar un acta en PDF"""
    acta = get_object_or_404(ActaEvaluacion, id=transcript_id)
    
    if acta.archivo_pdf:
        file_path = acta.archivo_pdf.path
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="acta_{acta.materia.nombre.replace(" ", "_")}_{acta.grupo}.pdf"'
            return response
    
    messages.error(request, 'El archivo PDF no está disponible')
    return redirect('view_transcript', transcript_id=transcript_id)

@control_escolar_required
def lista_carreras(request):
    """Lista todas las carreras"""
    carreras = Carrera.objects.all().order_by('id')
    
    context = {
        'carreras': carreras,
        'page_title': 'Gestión de Carreras'
    }
    return render(request, 'evaluaciones/carreras/lista_carreras.html', context)

@control_escolar_required
def agregar_carrera(request):
    """Agregar una nueva carrera"""
    if request.method == 'POST':
        try:
            nombre = request.POST['nombre']
            tipo_carrera = request.POST['tipo_carrera']
            numero_semestres = request.POST['numero_semestres']
            plan = request.POST['plan']
            codigo = request.POST.get('codigo', '')
            numero_unidades = int(request.POST.get('numero_unidades', 2))
            
            # Crear la carrera
            carrera = Carrera.objects.create(
                nombre=nombre,
                tipo_carrera=tipo_carrera,
                numero_semestres=numero_semestres,
                plan=plan,
                codigo=codigo
            )
            
            # Crear unidades automáticamente basadas en el número especificado
            año_plan = str(carrera.plan)[-2:]
            
            for i in range(1, numero_unidades + 1):
                Unidad.objects.create(
                    carrera=carrera,
                    numero=i,
                    nombre=f'Unidad {i}',
                )
            
            messages.success(request, f'Carrera "{nombre}" agregada exitosamente con {numero_unidades} unidades')
            return redirect('lista_carreras')
            
        except Exception as e:
            messages.error(request, f'Error al agregar la carrera: {str(e)}')
    
    context = {
        'page_title': 'Agregar Carrera',
        'modo': 'agregar'
    }
    return render(request, 'evaluaciones/carreras/form_carrera.html', context)

@control_escolar_required
def editar_carrera(request, carrera_id):
    """Editar una carrera existente"""
    carrera = get_object_or_404(Carrera, id=carrera_id)
    
    if request.method == 'POST':
        try:
            numero_unidades_nuevo = int(request.POST.get('numero_unidades', carrera.unidades.count()))
            numero_unidades_actual = carrera.unidades.count()
            
            # Actualizar información básica
            carrera.nombre = request.POST['nombre']
            carrera.tipo_carrera = request.POST['tipo_carrera']
            carrera.numero_semestres = request.POST['numero_semestres']
            carrera.plan = request.POST['plan']
            carrera.codigo = request.POST.get('codigo', '')
            carrera.activa = 'activa' in request.POST
            
            carrera.save()
            
            # Manejar cambio en el número de unidades
            if numero_unidades_nuevo != numero_unidades_actual:
                año_plan = str(carrera.plan)[-2:]
                
                if numero_unidades_nuevo > numero_unidades_actual:
                    # Agregar unidades nuevas
                    for i in range(numero_unidades_actual + 1, numero_unidades_nuevo + 1):
                        Unidad.objects.create(
                            carrera=carrera,
                            numero=i,
                            nombre=f'Unidad {i}'
                        )
                    messages.info(request, f'Se agregaron {numero_unidades_nuevo - numero_unidades_actual} unidades nuevas')
                    
                elif numero_unidades_nuevo < numero_unidades_actual:
                    # Eliminar unidades sobrantes (solo si no tienen materias)
                    unidades_a_eliminar = carrera.unidades.filter(numero__gt=numero_unidades_nuevo)
                    unidades_con_materias = []
                    unidades_eliminadas = 0
                    
                    for unidad in unidades_a_eliminar:
                        if unidad.materias.exists():
                            unidades_con_materias.append(unidad.codigo)
                        else:
                            unidad.delete()
                            unidades_eliminadas += 1
                    
                    if unidades_con_materias:
                        messages.warning(request, f'No se pudieron eliminar {len(unidades_con_materias)} unidades porque tienen materias: {", ".join(unidades_con_materias)}')
            
            messages.success(request, f'Carrera "{carrera.nombre}" actualizada exitosamente')
            return redirect('detalle_carrera', carrera_id=carrera.id)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la carrera: {str(e)}')
    
    context = {
        'carrera': carrera,
        'page_title': f'Editar {carrera.nombre}',
        'modo': 'editar'
    }
    return render(request, 'evaluaciones/carreras/form_carrera.html', context)

@control_escolar_required
def detalle_carrera(request, carrera_id):
    """Ver detalle de una carrera"""
    carrera = get_object_or_404(Carrera, id=carrera_id)
    unidades = carrera.unidades.all().prefetch_related('materias')  # VOLVER A prefetch_related
    
    # Obtener materias por semestre
    materias_por_semestre = {}
    for semestre in range(1, carrera.numero_semestres + 1):
        materias_por_semestre[semestre] = Materia.objects.filter(
            carrera=carrera,
            semestre=semestre
        ).prefetch_related('unidades')
    
    context = {
        'carrera': carrera,
        'unidades': unidades,
        'materias_por_semestre': materias_por_semestre,
        'page_title': f'Detalle de {carrera.nombre}'
    }
    return render(request, 'evaluaciones/carreras/detalle_carrera.html', context)

@control_escolar_required
def eliminar_carrera(request, carrera_id):
    """Eliminar una carrera"""
    carrera = get_object_or_404(Carrera, id=carrera_id)
    
    if request.method == 'POST':
        try:
            nombre = carrera.nombre
            carrera.delete()
            messages.success(request, f'Carrera "{nombre}" eliminada exitosamente')
        except Exception as e:
            messages.error(request, f'Error al eliminar la carrera: {str(e)}')
    
    return redirect('lista_carreras')

@control_escolar_required
def agregar_materia(request, carrera_id):
    """Agregar una materia a una carrera"""
    carrera = get_object_or_404(Carrera, id=carrera_id)
    
    if request.method == 'POST':
        try:
            nombre = request.POST['nombre']
            semestre = int(request.POST['semestre'])
            unidades_ids = request.POST.getlist('unidades')
            creditos = float(request.POST.get('creditos', 8.0))
            horas = int(request.POST.get('horas', 64))
            
            # Validar que las unidades no estén ya asignadas
            unidades_con_materia = []
            for unidad_id in unidades_ids:
                unidad = Unidad.objects.get(id=unidad_id)
                if unidad.materias.exists():
                    unidades_con_materia.append(unidad.codigo)
            
            if unidades_con_materia:
                messages.error(request, f'Las siguientes unidades ya están asignadas: {", ".join(unidades_con_materia)}')
                return redirect('detalle_carrera', carrera_id=carrera_id)
            
            # Crear la materia
            materia = Materia.objects.create(
                carrera=carrera,
                nombre=nombre,
                semestre=semestre,
                creditos=creditos,
                horas=horas
            )
            
            # Asignar las unidades seleccionadas
            if unidades_ids:
                unidades = Unidad.objects.filter(id__in=unidades_ids, carrera=carrera)
                materia.unidades.set(unidades)
            
            messages.success(request, f'Materia "{nombre}" agregada exitosamente')
            
        except Exception as e:
            messages.error(request, f'Error al agregar la materia: {str(e)}')
    
    return redirect('detalle_carrera', carrera_id=carrera_id)

@control_escolar_required
def eliminar_materia(request, materia_id):
    """Eliminar una materia"""
    materia = get_object_or_404(Materia, id=materia_id)
    carrera_id = materia.carrera.id
    
    if request.method == 'POST':
        try:
            nombre = materia.nombre
            materia.delete()
            messages.success(request, f'Materia "{nombre}" eliminada exitosamente')
        except Exception as e:
            messages.error(request, f'Error al eliminar la materia: {str(e)}')
    
    return redirect('detalle_carrera', carrera_id=carrera_id)

@control_escolar_required
def editar_materia(request, materia_id):
    """Editar una materia existente"""
    materia = get_object_or_404(Materia, id=materia_id)
    
    if request.method == 'POST':
        try:
            # Guardar las unidades actuales para comparar después
            unidades_actuales = set(materia.unidades.values_list('id', flat=True))
            
            materia.nombre = request.POST['nombre']
            materia.semestre = int(request.POST['semestre'])
            nuevas_unidades_ids = set(request.POST.getlist('unidades'))
            materia.creditos = float(request.POST.get('creditos', 8.0))
            materia.horas = int(request.POST.get('horas', 64))
            materia.activa = 'activa' in request.POST
            
            # Validar que las nuevas unidades no estén ya asignadas a otras materias
            unidades_a_agregar = nuevas_unidades_ids - unidades_actuales
            unidades_con_materia = []
            
            for unidad_id in unidades_a_agregar:
                unidad = Unidad.objects.get(id=unidad_id)
                if unidad.materias.exclude(pk=materia.id).exists():
                    unidades_con_materia.append(unidad.codigo)
            
            if unidades_con_materia:
                messages.error(request, f'Las siguientes unidades ya están asignadas a otras materias: {", ".join(unidades_con_materia)}')
                return redirect('detalle_carrera', carrera_id=materia.carrera.id)
            
            materia.save()
            
            # Actualizar las unidades
            if nuevas_unidades_ids:
                unidades = Unidad.objects.filter(id__in=nuevas_unidades_ids, carrera=materia.carrera)
                materia.unidades.set(unidades)
            
            messages.success(request, f'Materia "{materia.nombre}" actualizada exitosamente')
        except Exception as e:
            messages.error(request, f'Error al actualizar la materia: {str(e)}')
    
    return redirect('detalle_carrera', carrera_id=materia.carrera.id)

@control_escolar_required
def cambiar_estado_materia(request, materia_id):
    """Cambiar el estado activo/inactivo de una materia"""
    materia = get_object_or_404(Materia, id=materia_id)
    
    if request.method == 'POST':
        try:
            materia.activa = not materia.activa
            materia.save()
            
            estado = "activada" if materia.activa else "desactivada"
            messages.success(request, f'Materia "{materia.nombre}" {estado} exitosamente')
        except Exception as e:
            messages.error(request, f'Error al cambiar el estado de la materia: {str(e)}')
    
    return redirect('detalle_carrera', carrera_id=materia.carrera.id)

@control_escolar_required
def obtener_datos_materia(request, materia_id):
    """Obtener datos de una materia para edición (AJAX)"""
    try:
        materia = get_object_or_404(Materia, id=materia_id)
        
        # Obtener IDs de las unidades asignadas a esta materia
        unidades_ids = list(materia.unidades.values_list('id', flat=True))  # CAMBIADO: unidades en lugar de unidades_asignadas
        
        return JsonResponse({
            'nombre': materia.nombre,
            'semestre': materia.semestre,
            'unidades_ids': unidades_ids,
            'creditos': float(materia.creditos),
            'horas': materia.horas,
            'activa': materia.activa
        })
    except Exception as e:
        # Log del error para debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en obtener_datos_materia: {str(e)}")
        
        return JsonResponse({
            'error': str(e)
        }, status=500)
    
# evaluaciones/views.py (agregar temporalmente para debugging)
@control_escolar_required
def debug_materia(request, materia_id):
    """Vista temporal para debugging"""
    materia = get_object_or_404(Materia, id=materia_id)
    
    print("=== DEBUG MATERIA ===")
    print(f"Materia: {materia.nombre}")
    print(f"Unidades asignadas: {list(materia.unidades.values_list('id', 'codigo'))}")
    print("=====================")
    
    return JsonResponse({
        'debug': 'ok',
        'materia': materia.nombre,
        'unidades': list(materia.unidades.values_list('id', flat=True))
    })

@control_escolar_required
def asignar_materias_unidades_sin_asignar(request, carrera_id):
    """Asignar materias automáticamente a unidades sin asignar"""
    carrera = get_object_or_404(Carrera, id=carrera_id)
    
    try:
        unidades_sin_materia = Unidad.objects.filter(carrera=carrera, materias__isnull=True)
        materias_sin_unidades = Materia.objects.filter(carrera=carrera, unidades__isnull=True)
        
        unidades_asignadas = 0
        
        for unidad in unidades_sin_materia:
            # Buscar una materia sin unidades para esta unidad
            materia_disponible = materias_sin_unidades.first()
            if materia_disponible:
                materia_disponible.unidades.add(unidad)
                unidades_asignadas += 1
                print(f"✅ Unidad {unidad.codigo} asignada a {materia_disponible.nombre}")
        
        messages.success(request, f'Se asignaron {unidades_asignadas} unidades a materias existentes')
        
    except Exception as e:
        messages.error(request, f'Error al asignar materias: {str(e)}')
    
    return redirect('detalle_carrera', carrera_id=carrera_id)

@control_escolar_required
def acta_list(request):
    """Lista de todas las actas de evaluación - Similar a certificate_list"""
    actas = ActaEvaluacion.objects.all().order_by('-fecha_generacion')
    
    context = {
        'actas': actas,
        'page_title': 'Lista de Actas de Evaluación'
    }
    return render(request, 'evaluaciones/acta_list.html', context)

@control_escolar_required
def generate_acta(request):
    """Generar una nueva acta de evaluación"""
    carreras = Carrera.objects.all()
    
    if request.method == 'POST':
        try:
            carrera_id = request.POST.get('carrera')
            semestre = request.POST.get('semestre')
            grupo = request.POST.get('grupo')
            turno = request.POST.get('turno')
            materia_id = request.POST.get('materia')
            ciclo_escolar = request.POST.get('ciclo_escolar')
            total_horas = request.POST.get('total_horas')
            fecha_emision = request.POST.get('fecha_emision')
            
            carrera = Carrera.objects.get(id=carrera_id)
            materia = Materia.objects.get(id=materia_id)
            
            # Crear el acta
            acta = ActaEvaluacion.objects.create(
                carrera=carrera,
                semestre=semestre,
                grupo=grupo,
                materia=materia,
                periodo=ciclo_escolar,
                fecha_emision=fecha_emision,
                estado='generada',
                generada_por=request.user
            )
            
            # Obtener calificaciones para este acta
            calificaciones = Calificacion.objects.filter(
                alumno__carrera=carrera,
                alumno__semestre_actual=semestre,
                unidad__materias=materia,
                periodo=ciclo_escolar
            ).select_related('alumno', 'unidad')
            
            # Obtener unidades de la materia
            unidades = Unidad.objects.filter(materias=materia).order_by('numero')
            
            # Calcular estadísticas
            acta.total_alumnos = calificaciones.values('alumno').distinct().count()
            acta.alumnos_evaluados = calificaciones.exclude(calificacion__isnull=True).count()
            
            if calificaciones.exists():
                calificaciones_validas = calificaciones.exclude(calificacion__isnull=True)
                if calificaciones_validas.exists():
                    total_calificaciones = sum(calif.calificacion for calif in calificaciones_validas)
                    acta.promedio_grupo = total_calificaciones / calificaciones_validas.count()
            
            acta.save()
            
            # Generar PDF
            html_string = render_to_string('evaluaciones/acta_template.html', {
                'acta': acta,
                'calificaciones': calificaciones,
                'unidades': unidades,
                'turno': turno,
                'ciclo_escolar': ciclo_escolar,
                'total_horas': total_horas,
                'logo_izquierdo': request.build_absolute_uri(static('img/logobc.jpg')),
                'logo_central': request.build_absolute_uri(static('img/logobn.jpg')),
            })
            
            html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
            pdf_content = html.write_pdf()

            pdf_filename = f'acta_{acta.id}_{materia.nombre.replace(" ", "_")}_{grupo}.pdf'
            pdf_path = f'actas/{pdf_filename}'
            full_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(pdf_content)
            
            acta.archivo_pdf.name = pdf_path
            acta.save()
            
            messages.success(request, f'Acta de evaluación generada exitosamente para {materia.nombre}')
            return redirect('view_acta', acta_id=acta.id)
            
        except Exception as e:
            messages.error(request, f'Error al generar el acta: {str(e)}')
    
    # Si es GET, mostrar el formulario
    context = {
        'carreras': carreras,
        'page_title': 'Generar Acta de Evaluación'
    }
    return render(request, 'evaluaciones/generate_acta.html', context)

@control_escolar_required
def view_acta(request, acta_id):
    """Ver una acta específica - Similar a view_certificate"""
    acta = get_object_or_404(ActaEvaluacion, id=acta_id)
    
    context = {
        'acta': acta,
        'page_title': f'Acta de {acta.materia.nombre}'
    }
    return render(request, 'evaluaciones/view_acta.html', context)

@control_escolar_required
def download_acta(request, acta_id):
    """Descargar una acta en PDF - Similar a download_certificate"""
    acta = get_object_or_404(ActaEvaluacion, id=acta_id)
    
    if acta.archivo_pdf and acta.archivo_pdf.name:
        try:
            response = FileResponse(
                acta.archivo_pdf.open(),
                as_attachment=True,
                filename=f'acta_{acta.materia.nombre.replace(" ", "_")}_{acta.grupo}.pdf'
            )
            response['Content-Type'] = 'application/pdf'
            return response
        except Exception as e:
            messages.error(request, f'Error al descargar el archivo: {str(e)}')
            return redirect('view_acta', acta_id=acta_id)
    else:
        messages.error(request, 'El archivo PDF no está disponible')
        return redirect('view_acta', acta_id=acta_id)

@xframe_options_exempt
@control_escolar_required
def view_acta_pdf(request, acta_id):
    """Vista especial para mostrar PDF en iframe - Similar a view_pdf"""
    acta = get_object_or_404(ActaEvaluacion, id=acta_id)
    
    if acta.archivo_pdf and acta.archivo_pdf.name:
        try:
            response = FileResponse(
                acta.archivo_pdf.open(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="acta_{acta.materia.nombre.replace(" ", "_")}_{acta.grupo}.pdf"'
            return response
        except Exception as e:
            return HttpResponse("Error al cargar el PDF", status=500)
    else:
        return HttpResponse("PDF no disponible", status=404)
    
@control_escolar_required
def obtener_materias_por_carrera(request, carrera_id):
    """Obtener materias de una carrera específica (AJAX)"""
    try:
        carrera = get_object_or_404(Carrera, id=carrera_id)
        materias = Materia.objects.filter(carrera=carrera, activa=True).order_by('nombre')
        
        materias_data = []
        for materia in materias:
            materias_data.append({
                'id': materia.id,
                'nombre': materia.nombre,
                'semestre': materia.semestre,
                'codigo': materia.unidades.first().codigo if materia.unidades.exists() else 'N/A'
            })
        
        return JsonResponse({'materias': materias_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)