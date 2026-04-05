from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.core.paginator import Paginator
from core.decorators import constancias_required
from .models import Constancia
from alumnos.models import Alumno
import os
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
from django.templatetags.static import static
from django.views.decorators.clickjacking import xframe_options_exempt
from django.db.models import Q

@constancias_required
def certificate_list(request):
    """Lista de todas las constancias con paginación"""
    constancias_list = Constancia.objects.all().select_related('alumno').order_by('-fecha_generacion')
    
    # Búsqueda por nombre o matrícula del alumno
    search_query = request.GET.get('search', '')
    if search_query:
        constancias_list = constancias_list.filter(
            Q(alumno__nombre__icontains=search_query) |
            Q(alumno__apellido_paterno__icontains=search_query) |
            Q(alumno__apellido_materno__icontains=search_query) |
            Q(alumno__matricula__icontains=search_query)
        )
    
    # Filtros
    tipo_filter = request.GET.get('tipo', '')
    estado_filter = request.GET.get('estado', '')
    
    if tipo_filter:
        constancias_list = constancias_list.filter(tipo_constancia=tipo_filter)
    if estado_filter:
        constancias_list = constancias_list.filter(estado=estado_filter)
    
    # Paginación - 10 elementos por página
    paginator = Paginator(constancias_list, 10)
    page_number = request.GET.get('page')
    constancias = paginator.get_page(page_number)
    
    context = {
        'constancias': constancias,
        'search_query': search_query,
        'tipo_filter': tipo_filter,
        'estado_filter': estado_filter,
        'page_title': 'Lista de Constancias'
    }
    return render(request, 'constancias/certificate_list.html', context)

@constancias_required
def generate_certificate(request):
    """Generar una nueva constancia"""
    if request.method == 'POST':
        try:
            alumno_id = request.POST.get('alumno')
            fecha_emision = request.POST.get('fecha_emision')
            firma_izquierda = request.POST.get('firma_izquierda', 'Vo.Bo. Subdirección Académica')
            firma_derecha = request.POST.get('firma_derecha', 'DRA. LIUBA ABIYOVA TÉLLEZ OSUNA')
            costo = float(request.POST.get('costo', 0.0))
            lema_anio = request.POST.get('lema_anio', '') 
            
            alumno = Alumno.objects.get(id=alumno_id)
            
            # Crear la constancia (siempre de estudios)
            constancia = Constancia.objects.create(
                alumno=alumno,
                tipo_constancia='estudios',  # Siempre será de estudios
                fecha_emision=fecha_emision,
                estado='generada',
                firma_izquierda=firma_izquierda,
                firma_derecha=firma_derecha,
                costo=costo,
                lema_anio=lema_anio  # Nuevo campo
            )
            
            # Generar PDF, render con contexto que incluye URLS absolutas de las imageness
            html_string = render_to_string('constancias/certificate_template.html', {
                'constancia': constancia,
                'logo_izquierdo': request.build_absolute_uri(static('img/logobc.jpg')),
                'logo_central':   request.build_absolute_uri(static('img/logobn.jpg')), 
            })
            
            # Generar PDF con WeasyPrint
            html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
            pdf_content = html.write_pdf()

            # Guardar el PDF
            pdf_filename = f'constancia_{constancia.id}_{alumno.matricula}.pdf'
            pdf_path = f'constancias/{pdf_filename}'
            full_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(pdf_content)
            
            constancia.archivo_pdf.name = pdf_path
            constancia.save()
            
            messages.success(request, f'Constancia generada exitosamente para {alumno.nombre_completo()}')
            return redirect('view_certificate', certificate_id=constancia.id)
            
        except Exception as e:
            messages.error(request, f'Error al generar la constancia: {str(e)}')
    
    # Si es GET, mostrar el formulario con todos los alumnos
    alumnos = Alumno.objects.all().order_by('apellido_paterno', 'apellido_materno', 'nombre')
    
    context = {
        'alumnos': alumnos,
        'page_title': 'Generar Constancia'
    }
    return render(request, 'constancias/generate_certificate.html', context)

@constancias_required
def view_certificate(request, certificate_id):
    """Ver una constancia específica - Muestra el PDF directamente"""
    constancia = get_object_or_404(Constancia, id=certificate_id)
    
    context = {
        'constancia': constancia,
        'page_title': f'Constancia de {constancia.alumno.nombre_completo()}'
    }
    return render(request, 'constancias/view_certificate.html', context)

@constancias_required
def download_certificate(request, certificate_id):
    """Descargar una constancia en PDF"""
    constancia = get_object_or_404(Constancia, id=certificate_id)
    
    if constancia.archivo_pdf and constancia.archivo_pdf.name:
        try:
            # Usar FileResponse para una descarga eficiente
            response = FileResponse(
                constancia.archivo_pdf.open(),
                as_attachment=True,
                filename=f'constancia_{constancia.alumno.matricula}.pdf'
            )
            response['Content-Type'] = 'application/pdf'
            return response
        except Exception as e:
            messages.error(request, f'Error al descargar el archivo: {str(e)}')
            return redirect('view_certificate', certificate_id=certificate_id)
    else:
        messages.error(request, 'El archivo PDF no está disponible')
        return redirect('view_certificate', certificate_id=certificate_id)

@xframe_options_exempt
@constancias_required
def view_pdf(request, certificate_id):
    """Vista especial para mostrar PDF en iframe"""
    constancia = get_object_or_404(Constancia, id=certificate_id)
    
    if constancia.archivo_pdf and constancia.archivo_pdf.name:
        try:
            response = FileResponse(
                constancia.archivo_pdf.open(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="constancia_{constancia.alumno.matricula}.pdf"'
            return response
        except Exception as e:
            return HttpResponse("Error al cargar el PDF", status=500)
    else:
        return HttpResponse("PDF no disponible", status=404)