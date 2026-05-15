from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse, FileResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.conf import settings
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views.decorators.clickjacking import xframe_options_exempt
from django.db.models import Q
from django.utils import timezone

from weasyprint import HTML
import os

from core.decorators import constancias_required
from .models import Constancia
from alumnos.models import Alumno
from administracion.models import ConfiguracionSistema


FIRMA_IZQUIERDA_DEFAULT = 'Vo.Bo. Subdirección Académica'
FIRMA_DERECHA_DEFAULT = 'DRA. LIUBA ABIYOVA TÉLLEZ OSUNA'


def es_alumno(user):
    return getattr(user, 'tipo_usuario', None) == 'alumno'


def puede_gestionar_constancias(user):
    tipo_usuario = getattr(user, 'tipo_usuario', None)

    return (
        user.is_superuser
        or user.is_staff
        or tipo_usuario in ['control_escolar', 'directivo', 'administrador']
    )


def obtener_alumno_de_usuario(user):
    """
    Obtiene el registro Alumno relacionado con el usuario autenticado.

    El modelo Alumno sincroniza usuarios con nombres como:
    - alumno_<id>
    - alumno_<matricula>
    Además, el email del usuario puede coincidir con el correo institucional
    o con el correo técnico alumno_<id>@edubc.mx.
    """

    if not es_alumno(user):
        return None

    username = (user.username or '').strip()

    if username.startswith('alumno_'):
        identificador = username.replace('alumno_', '', 1).strip()

        if identificador.isdigit():
            alumno = Alumno.objects.filter(id=int(identificador)).first()
            if alumno:
                return alumno

        if identificador:
            alumno = Alumno.objects.filter(matricula__iexact=identificador).first()
            if alumno:
                return alumno

    email_usuario = (user.email or '').strip().lower()

    if email_usuario:
        if email_usuario.startswith('alumno_') and email_usuario.endswith('@edubc.mx'):
            posible_id = email_usuario.replace('alumno_', '', 1).split('@')[0]

            if posible_id.isdigit():
                alumno = Alumno.objects.filter(id=int(posible_id)).first()
                if alumno:
                    return alumno

        for alumno in Alumno.objects.all():
            email_institucional = (alumno.email_institucional or '').strip().lower()
            email_para_usuario = (alumno.obtener_email_para_usuario() or '').strip().lower()

            if email_usuario in [email_institucional, email_para_usuario]:
                return alumno

    return None


def puede_ver_constancia(user, constancia):
    if puede_gestionar_constancias(user):
        return True

    if es_alumno(user):
        alumno = obtener_alumno_de_usuario(user)
        return alumno is not None and constancia.alumno_id == alumno.id

    return False


@constancias_required
def certificate_list(request):
    """
    Lista de constancias.

    Los alumnos no deben ver esta pantalla porque contiene constancias
    generadas para otros alumnos. Si un alumno entra por URL directa,
    se redirige a generar su propia constancia.
    """

    if es_alumno(request.user):
        return redirect('generate_certificate')

    constancias_list = Constancia.objects.all().select_related('alumno').order_by('-fecha_generacion')

    search_query = request.GET.get('search', '')
    if search_query:
        constancias_list = constancias_list.filter(
            Q(alumno__nombre__icontains=search_query)
            | Q(alumno__apellido_paterno__icontains=search_query)
            | Q(alumno__apellido_materno__icontains=search_query)
            | Q(alumno__matricula__icontains=search_query)
        )

    tipo_filter = request.GET.get('tipo', '')
    estado_filter = request.GET.get('estado', '')

    if tipo_filter:
        constancias_list = constancias_list.filter(tipo_constancia=tipo_filter)

    if estado_filter:
        constancias_list = constancias_list.filter(estado=estado_filter)

    paginator = Paginator(constancias_list, 10)
    page_number = request.GET.get('page')
    constancias = paginator.get_page(page_number)

    context = {
        'constancias': constancias,
        'search_query': search_query,
        'tipo_filter': tipo_filter,
        'estado_filter': estado_filter,
        'page_title': 'Lista de Constancias',
    }

    return render(request, 'constancias/certificate_list.html', context)

@constancias_required
def generate_certificate(request):
    """
    Generar una nueva constancia.

    - Control escolar/directivo/admin puede seleccionar cualquier alumno.
    - Alumno solo puede generar constancia para sí mismo.
    - Lema y firmas se toman desde Administración.
    """

    configuracion = ConfiguracionSistema.obtener()
    usuario_es_alumno = es_alumno(request.user)
    alumno_actual = obtener_alumno_de_usuario(request.user) if usuario_es_alumno else None

    if usuario_es_alumno and alumno_actual is None:
        messages.error(
            request,
            'No se encontró un registro de alumno vinculado a tu usuario. Contacta a Control Escolar.'
        )
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            if usuario_es_alumno:
                alumno = alumno_actual
                fecha_emision = timezone.localdate()
                costo = 0.0
            else:
                alumno_id = request.POST.get('alumno')

                if not alumno_id:
                    messages.error(request, 'Debes seleccionar un alumno.')
                    return redirect('generate_certificate')

                alumno = Alumno.objects.get(id=alumno_id)
                fecha_emision = request.POST.get('fecha_emision')
                costo = float(request.POST.get('costo', 0.0))

            constancia = Constancia.objects.create(
                alumno=alumno,
                tipo_constancia='estudios',
                fecha_emision=fecha_emision,
                estado='generada',
                firma_izquierda=configuracion.firma_izquierda_constancia,
                firma_derecha=configuracion.firma_derecha_constancia,
                costo=costo,
                lema_anio=configuracion.lema_anio,
            )

            html_string = render_to_string('constancias/certificate_template.html', {
                'constancia': constancia,
                'logo_izquierdo': request.build_absolute_uri(static('img/logobc.jpg')),
                'logo_central': request.build_absolute_uri(static('img/logobn.jpg')),
            })

            html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
            pdf_content = html.write_pdf()

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

    if usuario_es_alumno:
        alumnos = Alumno.objects.filter(id=alumno_actual.id)
    else:
        alumnos = Alumno.objects.all().order_by('apellido_paterno', 'apellido_materno', 'nombre')

    context = {
        'alumnos': alumnos,
        'alumno_actual': alumno_actual,
        'es_alumno': usuario_es_alumno,
        'lema_actual': configuracion.lema_anio,
        'firma_izquierda_actual': configuracion.firma_izquierda_constancia,
        'firma_derecha_actual': configuracion.firma_derecha_constancia,
        'page_title': 'Generar Constancia',
    }

    return render(request, 'constancias/generate_certificate.html', context)


@constancias_required
def view_certificate(request, certificate_id):
    """Ver una constancia específica."""

    constancia = get_object_or_404(Constancia, id=certificate_id)

    if not puede_ver_constancia(request.user, constancia):
        messages.error(request, 'No tienes permisos para ver esta constancia.')
        return redirect('dashboard')

    context = {
        'constancia': constancia,
        'page_title': f'Constancia de {constancia.alumno.nombre_completo()}',
    }

    return render(request, 'constancias/view_certificate.html', context)


@constancias_required
def download_certificate(request, certificate_id):
    """Descargar una constancia en PDF."""

    constancia = get_object_or_404(Constancia, id=certificate_id)

    if not puede_ver_constancia(request.user, constancia):
        messages.error(request, 'No tienes permisos para descargar esta constancia.')
        return redirect('dashboard')

    if constancia.archivo_pdf and constancia.archivo_pdf.name:
        try:
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

    messages.error(request, 'El archivo PDF no está disponible')
    return redirect('view_certificate', certificate_id=certificate_id)


@xframe_options_exempt
@constancias_required
def view_pdf(request, certificate_id):
    """Vista especial para mostrar PDF en iframe."""

    constancia = get_object_or_404(Constancia, id=certificate_id)

    if not puede_ver_constancia(request.user, constancia):
        return HttpResponseForbidden('No tienes permisos para ver este PDF.')

    if constancia.archivo_pdf and constancia.archivo_pdf.name:
        try:
            response = FileResponse(
                constancia.archivo_pdf.open(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="constancia_{constancia.alumno.matricula}.pdf"'
            return response

        except Exception:
            return HttpResponse('Error al cargar el PDF', status=500)

    return HttpResponse('PDF no disponible', status=404)