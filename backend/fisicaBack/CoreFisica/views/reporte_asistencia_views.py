from django.http import JsonResponse
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
import datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona, ReporteAsistencia
import openpyxl
from openpyxl.styles import Alignment, Border, Side, Font
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics


TIPOS_REEMPLAZO_PERMITIDOS = set(ReporteAsistencia.TIPOS_REEMPLAZO)


def _fit_text_to_width(text, max_width, font_name='Helvetica', font_size=7):
    s = str(text) if text is not None else ''
    if not s:
        return ''
    if pdfmetrics.stringWidth(s, font_name, font_size) <= max_width:
        return s

    ellipsis = '...'
    ellipsis_w = pdfmetrics.stringWidth(ellipsis, font_name, font_size)
    allowed = max_width - ellipsis_w
    if allowed <= 0:
        return ''

    while s and pdfmetrics.stringWidth(s, font_name, font_size) > allowed:
        s = s[:-1]
    return s + ellipsis


def _resolver_reemplazo_desde_request(request):
    if 'reemplazo_id' not in request.data:
        return 'no-enviado', None

    reemplazo_id = request.data.get('reemplazo_id')
    if reemplazo_id in [None, '', 'null']:
        return None, None

    try:
        reemplazo_id = int(reemplazo_id)
    except (TypeError, ValueError):
        return None, JsonResponse(
            {'error': 'reemplazo_id debe ser un entero valido'},
            status=status.HTTP_400_BAD_REQUEST
        )

    persona = Persona.objects.filter(id=reemplazo_id, is_active=True).first()
    if not persona:
        return None, JsonResponse(
            {'error': 'La persona enviada en reemplazo_id no existe o esta inactiva'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if persona.tipo not in TIPOS_REEMPLAZO_PERMITIDOS:
        return None, JsonResponse(
            {'error': f'El tipo {persona.tipo} no puede ser reemplazo. Permitidos: {sorted(TIPOS_REEMPLAZO_PERMITIDOS)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return persona, None



def _build_reporte_asistencia_data(fecha=None, cliente_id=None):
    fecha_obj = None
    if fecha:
        try:
            fecha_obj = datetime.date.fromisoformat(str(fecha))
        except ValueError:
            fecha_obj = None

    hoy = timezone.localdate()
    fin_anio_actual = datetime.date(hoy.year, 12, 31)

    reporte_qs = ReporteAsistencia.objects.select_related('asignacion', 'modificado_por', 'reemplazo')
    if fecha_obj:
        if fecha_obj >= hoy:
            # Desde la fecha filtrada hasta fin de anio actual.
            reporte_qs = reporte_qs.filter(
                Q(modificado_en__date__gte=fecha_obj, modificado_en__date__lte=fin_anio_actual) |
                Q(modificado_en__isnull=True, created_at__date__gte=fecha_obj, created_at__date__lte=fin_anio_actual)
            )
        else:
            # Para fechas pasadas, mantener filtro diario exacto.
            reporte_qs = reporte_qs.filter(
                Q(modificado_en__date=fecha_obj) |
                Q(modificado_en__isnull=True, created_at__date=fecha_obj)
            )

    overrides = {
        r.asignacion_id: r
        for r in reporte_qs
    }

    asig_qs = Asignacion.objects.select_related(
        'cliente', 'instalacion', 'puesto', 'horario', 'persona'
    ).filter(persona__is_active=True)

    if fecha_obj:
        # Reporte por rango hasta fin de anio actual cuando la fecha es hoy/futura.
        if fecha_obj >= hoy:
            # Mantener visibilidad de asignaciones vigentes durante todo el anio actual.
            asig_qs = asig_qs.filter(anio=hoy.year)
            asig_qs = asig_qs.filter(
                Q(fecha__gte=fecha_obj, fecha__lte=fin_anio_actual) |
                Q(fecha__isnull=True) |
                Q(id__in=reporte_qs.values('asignacion_id'))
            )
        else:
            asig_qs = asig_qs.filter(anio=fecha_obj.year, mes=fecha_obj.month)
            asig_qs = asig_qs.filter(
                Q(fecha=fecha_obj) |
                Q(id__in=reporte_qs.values('asignacion_id'))
            )
    if cliente_id:
        asig_qs = asig_qs.filter(cliente_id=cliente_id)

    data = []
    personas_con_asignacion = set()
    for asig in asig_qs.order_by('mes', 'fecha', 'id'):
        p = asig.persona
        personas_con_asignacion.add(p.id)
        override = overrides.get(asig.id)

        cliente_nombre = getattr(asig.cliente, 'nombre_comercial', '') if asig else ''
        
        puesto_nombre = getattr(asig.puesto, 'nombre', '') if asig else ''
        if not puesto_nombre and asig:
            puesto_nombre = getattr(asig.puesto, 'tipo', '')
        horario_str = ''
        if asig and asig.horario:
            horario_str = f"{asig.horario.hora_ingreso.strftime('%H:%M')} - {asig.horario.hora_salida.strftime('%H:%M')}"
        nombre_apellidos = f"{p.nombres} {p.apellidos}".strip()
        reemplazo_nombre = ''
        reemplazo_id = None
        if override and override.reemplazo:
            reemplazo_id = override.reemplazo.id
            reemplazo_nombre = f"{override.reemplazo.nombres} {override.reemplazo.apellidos}".strip()
        modificado_por_nombre = ''
        modificado_en_iso = None
        if override:
            if override.modificado_por:
                full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
                modificado_por_nombre = full_name or override.modificado_por.get_username()
            modificado_en_iso = override.modificado_en.isoformat() if override.modificado_en else None

        data.append({
            'asignacion_id': asig.id,
            'codigo': override.codigo if (override and override.codigo) else '',
            'cliente': cliente_nombre,
            'puesto': puesto_nombre,
            'horario': horario_str,
            'nombre_apellidos': nombre_apellidos,
            'reemplazo_id': reemplazo_id,
            'reemplazo': reemplazo_nombre,
            'estado': (override.estado or 'TURNO') if override else 'TURNO',
            'descripcion': (override.descripcion or '') if override else '',
            'modificado_por': modificado_por_nombre,
            'row_color': (override.row_color or '') if override else '',
            'modificado_en': modificado_en_iso,
        })

    # Asegura que tambien se muestren personas activas sin asignacion.
    for p in Persona.objects.filter(is_active=True).order_by('apellidos', 'nombres'):
        if p.id in personas_con_asignacion:
            continue
        data.append({
            'asignacion_id': None,
            'codigo': '',
            'cliente': '',
            'puesto': '',
            'horario': '',
            'nombre_apellidos': f"{p.nombres} {p.apellidos}".strip(),
            'reemplazo_id': None,
            'reemplazo': '',
            'estado': '',
            'descripcion': '',
            'modificado_por': '',
            'row_color': '',
            'modificado_en': None,
        })

    return data

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_asistencia(request):
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id)
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def insertar_reporte_asistencia(request, asignacion_id):
    override, _ = ReporteAsistencia.objects.get_or_create(asignacion_id=asignacion_id)

    asignacion = Asignacion.objects.select_related(
        'persona', 'cliente', 'instalacion', 'puesto', 'horario'
    ).filter(id=asignacion_id).first()
    if not asignacion:
        return JsonResponse({'error': 'Asignacion no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    override.persona = asignacion.persona
    override.cliente = asignacion.cliente
    override.instalacion = asignacion.instalacion
    override.puesto = asignacion.puesto
    override.horario = asignacion.horario
    override.puesto_tipo = getattr(asignacion.puesto, 'tipo', None) if asignacion.puesto else None

    for field in ['codigo', 'estado', 'descripcion', 'row_color']:
        if field in request.data:
            val = request.data.get(field) or None
            setattr(override, field, val)

    reemplazo_result, err = _resolver_reemplazo_desde_request(request)
    if err:
        return err
    if reemplazo_result != 'no-enviado':
        override.reemplazo = reemplazo_result

    if request.user and request.user.is_authenticated:
        override.modificado_por = request.user
    override.modificado_en = timezone.now()
    override.save()

    modificado_por_nombre = ''
    if override.modificado_por:
        full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
        modificado_por_nombre = full_name or override.modificado_por.get_username()

    reemplazo_nombre = ''
    if override.reemplazo:
        reemplazo_nombre = f"{override.reemplazo.nombres} {override.reemplazo.apellidos}".strip()

    return JsonResponse({
        'codigo': override.codigo or '',
        'estado': override.estado or 'TURNO',
        'descripcion': override.descripcion or '',
        'reemplazo_id': override.reemplazo_id,
        'reemplazo': reemplazo_nombre,
        'modificado_por': modificado_por_nombre,
        'row_color': override.row_color or '',
        'modificado_en': override.modificado_en.isoformat() if override.modificado_en else None,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reporte_asistencia_excel(request):
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Reporte Asistencia'

    headers = [
        'CÓDIGO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO', 'DESCRIPCIÓN',
    ]
    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header
        cell.border = border
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for row_idx, item in enumerate(data, start=2):
        row_vals = [
            item.get('codigo', ''),
            item.get('cliente', ''),
            item.get('puesto', ''),
            item.get('horario', ''),
            item.get('nombre_apellidos', ''),
            item.get('estado', ''),
            item.get('reemplazo', ''),
            item.get('descripcion', ''),
        ]
        for col_idx, value in enumerate(row_vals, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.border = border
            if col_idx == 8:
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[row_idx].height = 32

    # Anchos en proporcion similar al PDF: [0.8, 1.3, 1.3, 1.2, 1.8, 1.6, 0.8, 2.2]
    column_widths = {
        1: 11,  # Codigo
        2: 18,  # Cliente
        3: 23,  # Puesto
        4: 12,  # Horario
        5: 40,  # Nombre y Apellidos
        6: 12,  # Estado
        7: 40,  # Reemplazo
        8: 28,  # Descripcion
    }
    for col_idx, width in column_widths.items():
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.xlsx"'
    wb.save(response)
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reporte_asistencia_pdf(request):
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.pdf"'

    p = canvas.Canvas(response, pagesize=landscape(letter))
    width, height = landscape(letter)

    x_margin = 0.5 * inch
    y_margin = 0.5 * inch
    y = height - y_margin

    headers = [
        'CÓDIGO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO', 'DESCRIPCIÓN',
    ]
    col_widths = [0.8, 1.3, 1.3, 0.75, 1.9, 0.8, 1.9, 1.1]
    col_widths = [w * inch for w in col_widths]

    p.setFont('Helvetica-Bold', 12)
    p.drawString(x_margin, y, 'Reporte de Asistencia')
    y -= 0.3 * inch

    p.setFont('Helvetica-Bold', 8)
    x = x_margin
    for i, header in enumerate(headers):
        header_w = pdfmetrics.stringWidth(header, 'Helvetica-Bold', 8)
        p.drawString(x + max((col_widths[i] - header_w) / 2, 0), y, header)
        x += col_widths[i]

    y -= 0.25 * inch
    p.setFont('Helvetica', 7)

    for item in data:
        if y < y_margin + 0.5 * inch:
            p.showPage()
            width, height = landscape(letter)
            y = height - y_margin

            p.setFont('Helvetica-Bold', 12)
            p.drawString(x_margin, y, 'Reporte de Asistencia')
            y -= 0.3 * inch

            p.setFont('Helvetica-Bold', 8)
            x = x_margin
            for i, header in enumerate(headers):
                header_w = pdfmetrics.stringWidth(header, 'Helvetica-Bold', 8)
                p.drawString(x + max((col_widths[i] - header_w) / 2, 0), y, header)
                x += col_widths[i]
            y -= 0.25 * inch
            p.setFont('Helvetica', 7)

        row_vals = [
            item.get('codigo', ''),
            item.get('cliente', ''),
            item.get('puesto', ''),
            item.get('horario', ''),
            item.get('nombre_apellidos', ''),
            item.get('estado', ''),
            item.get('reemplazo', ''),
            (item.get('descripcion', '') or '')[:120],
        ]

        x = x_margin
        for i, value in enumerate(row_vals):
            text = str(value) if value is not None else ''
            text = _fit_text_to_width(text, col_widths[i] - 4, 'Helvetica', 7)
            txt_w = pdfmetrics.stringWidth(text, 'Helvetica', 7)
            p.drawString(x + max((col_widths[i] - txt_w) / 2, 0), y, text)
            x += col_widths[i]

        y -= 0.2 * inch

    p.showPage()
    p.save()
    return response