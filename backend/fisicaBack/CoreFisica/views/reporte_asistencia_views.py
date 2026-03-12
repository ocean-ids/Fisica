from django.http import JsonResponse
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
import datetime
from pathlib import Path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona, ReporteAsistencia
import openpyxl
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils.units import pixels_to_EMU
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader


TIPOS_REEMPLAZO_PERMITIDOS = set(ReporteAsistencia.TIPOS_REEMPLAZO)
HEADER_TITULO = 'FR REPORTE DE ASISTENCIA SEGURIDAD FÍSICA'
HEADER_VERSION = '.01'
HEADER_FECHA_APROBACION = '12-Aug-22'

DIAS_SEMANA_ES = [
    'LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO'
]


def _parse_fecha_reporte(fecha_param):
    if fecha_param:
        try:
            return datetime.date.fromisoformat(str(fecha_param))
        except ValueError:
            pass
    return timezone.localdate()


def _build_operador_consola(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return ''
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.get_username()


def _format_fecha_reporte_es(fecha_obj):
    dia = DIAS_SEMANA_ES[fecha_obj.weekday()]
    return f"{dia} {fecha_obj.strftime('%d/%m/%Y')}"


def _find_logo_path():
    this_file = Path(__file__).resolve()
    root_candidates = [
        this_file.parents[4],
        this_file.parents[3],
        Path.cwd(),
    ]
    relative_candidates = [
        Path('frontendf/public/logodescargable.jpg'),
        Path('frontendf/public/favicon.png'),
        Path('frontendf/public/logo.png'),
        Path('frontendf/src/assets/images/logo.png'),
        Path('src/assets/images/logo.png'),
    ]

    for root in root_candidates:
        for rel in relative_candidates:
            candidate = root / rel
            if candidate.exists():
                return candidate
    return None


def _build_header_context(request, fecha, turno):
    fecha_obj = _parse_fecha_reporte(fecha)
    turno_label = turno if turno in ['Diurno', 'Nocturno'] else 'TODOS'
    return {
        'titulo': HEADER_TITULO,
        'version': HEADER_VERSION,
        'fecha_aprobacion': HEADER_FECHA_APROBACION,
        'fecha_reporte': _format_fecha_reporte_es(fecha_obj),
        'turno': turno_label,
        'operador_consola': _build_operador_consola(request),
        'logo_path': _find_logo_path(),
    }


def _draw_excel_header(ws, ctx, border):
    ws.merge_cells('A1:B2')
    ws.merge_cells('C1:F2')
    ws.merge_cells('A4:D4')
    ws.merge_cells('E4:F4')
    ws.merge_cells('G4:H4')

    for row in range(1, 5):
        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    ws['C1'] = ctx['titulo']
    ws['C1'].font = Font(bold=True, size=14)

    ws['G1'] = 'Versión:'
    ws['H1'] = ctx['version']
    ws['G2'] = 'Fecha de aprobación:'
    ws['H2'] = ctx['fecha_aprobacion']
    ws['G1'].font = ws['G2'].font = Font(bold=True, size=10)
    ws['H1'].font = ws['H2'].font = Font(bold=True, size=10)

    ws['A4'] = f"FECHA: {ctx['fecha_reporte']}"
    ws['E4'] = f"TURNO: {ctx['turno'].upper()}"
    ws['G4'] = f"OPERADOR DE CONSOLA: {ctx['operador_consola']}"
    ws['A4'].font = ws['E4'].font = ws['G4'].font = Font(bold=True, size=11)

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 10
    ws.row_dimensions[4].height = 24

    if ctx['logo_path']:
        try:
            img = XLImage(str(ctx['logo_path']))

            # Escalar proporcionalmente dentro del recuadro A1:B2 (sin deformar)
            box_w_px = 203
            box_h_px = 74
            padding_px = 6
            max_w = box_w_px - (padding_px * 2)
            max_h = box_h_px - (padding_px * 2)

            orig_w = max(float(img.width), 1.0)
            orig_h = max(float(img.height), 1.0)
            scale = min(max_w / orig_w, max_h / orig_h)

            final_w = int(orig_w * scale)
            final_h = int(orig_h * scale)
            img.width = final_w
            img.height = final_h

            x_offset_px = int((box_w_px - final_w) / 2)
            y_offset_px = int((box_h_px - final_h) / 2)

            img.anchor = OneCellAnchor(
                _from=AnchorMarker(
                    col=0,
                    row=0,
                    colOff=pixels_to_EMU(max(x_offset_px, 0)),
                    rowOff=pixels_to_EMU(max(y_offset_px, 0)),
                ),
                ext=XDRPositiveSize2D(
                    cx=pixels_to_EMU(final_w),
                    cy=pixels_to_EMU(final_h),
                ),
            )
            ws.add_image(img)
        except Exception:
            pass


def _draw_pdf_header(p, width, height, x_margin, y_margin, ctx):
    table_w = width - (2 * x_margin)
    top = height - y_margin

    top_h = 0.95 * inch
    info_h = 0.32 * inch

    logo_w = 1.8 * inch
    title_w = 4.8 * inch

    x_logo = x_margin
    x_title = x_logo + logo_w
    x_meta = x_title + title_w

    p.setStrokeColor(colors.black)
    p.rect(x_margin, top - top_h, table_w, top_h, stroke=1, fill=0)
    p.line(x_title, top - top_h, x_title, top)
    p.line(x_meta, top - top_h, x_meta, top)

    p.line(x_meta, top - (top_h / 2), x_margin + table_w, top - (top_h / 2))

    if ctx['logo_path']:
        try:
            logo = ImageReader(str(ctx['logo_path']))
            draw_w = logo_w * 0.62
            draw_h = top_h * 0.62
            draw_x = x_logo + ((logo_w - draw_w) / 2)
            draw_y = (top - top_h) + ((top_h - draw_h) / 2)
            p.drawImage(
                logo,
                draw_x,
                draw_y,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception:
            pass

    p.setFont('Helvetica-Bold', 15)
    title_y = top - (top_h / 2) + 0.1 * inch
    p.drawCentredString(x_title + (title_w / 2), title_y, ctx['titulo'])

    p.setFont('Helvetica-Bold', 10)
    p.drawString(x_meta + 8, top - 0.28 * inch, 'Versión:')
    p.drawRightString(x_margin + table_w - 8, top - 0.28 * inch, ctx['version'])

    p.drawString(x_meta + 8, top - 0.75 * inch, 'Fecha de aprobación:')
    p.drawRightString(x_margin + table_w - 8, top - 0.75 * inch, ctx['fecha_aprobacion'])

    info_top = top - top_h
    p.rect(x_margin, info_top - info_h, table_w, info_h, stroke=1, fill=0)

    info_a_w = 2.8 * inch
    info_b_w = 2.3 * inch
    x_info_b = x_margin + info_a_w
    x_info_c = x_info_b + info_b_w

    p.line(x_info_b, info_top - info_h, x_info_b, info_top)
    p.line(x_info_c, info_top - info_h, x_info_c, info_top)

    p.setFont('Helvetica-Bold', 10)
    text_y = info_top - 0.22 * inch
    p.drawString(x_margin + 8, text_y, f"FECHA: {ctx['fecha_reporte']}")
    p.drawString(x_info_b + 8, text_y, f"TURNO: {ctx['turno'].upper()}")
    p.drawString(x_info_c + 8, text_y, f"OPERADOR DE CONSOLA: {ctx['operador_consola']}")

    return info_top - info_h - 0.2 * inch


def _draw_pdf_table_headers(p, x_margin, y, headers, col_widths):
    p.setFont('Helvetica-Bold', 8)
    x = x_margin
    for i, header in enumerate(headers):
        header_w = pdfmetrics.stringWidth(header, 'Helvetica-Bold', 8)
        p.drawString(x + max((col_widths[i] - header_w) / 2, 0), y, header)
        x += col_widths[i]
    return y - 0.25 * inch


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


def _normalize_hex_color(color_value):
    c = str(color_value or '').strip()
    if not c:
        return None
    if c.startswith('#'):
        c = c[1:]
    if len(c) != 6:
        return None
    try:
        int(c, 16)
    except ValueError:
        return None
    return c.upper()


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



def _build_reporte_asistencia_data(fecha=None, cliente_id=None, turno=None):
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
    if turno in ['Diurno', 'Nocturno']:
        asig_qs = asig_qs.filter(puesto__horarios__turno=turno).distinct()

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
    turno = request.GET.get('turno')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno)
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
    turno = request.GET.get('turno')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno)
    header_ctx = _build_header_context(request, fecha, turno)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Reporte Asistencia'

    headers = [
        'CÓDIGO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO', 'DESCRIPCIÓN',
    ]
    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    _draw_excel_header(ws, header_ctx, border)

    header_row = 6
    data_start_row = header_row + 1

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.value = header
        cell.border = border
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for row_idx, item in enumerate(data, start=data_start_row):
        row_hex = _normalize_hex_color(item.get('row_color'))
        row_fill = PatternFill(start_color=row_hex, end_color=row_hex, fill_type='solid') if row_hex else None
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
            if row_fill:
                cell.fill = row_fill
            if col_idx == 8:
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[row_idx].height = 32

    
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
    turno = request.GET.get('turno')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno)
    header_ctx = _build_header_context(request, fecha, turno)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.pdf"'

    p = canvas.Canvas(response, pagesize=landscape(letter))
    width, height = landscape(letter)

    x_margin = 0.5 * inch
    y_margin = 0.5 * inch

    headers = [
        'CÓDIGO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO', 'DESCRIPCIÓN',
    ]
    
    col_widths = [0.8, 1.25, 1.2, 0.65, 1.95, 0.9, 1.9, 1.05]
    col_widths = [w * inch for w in col_widths]

    y = _draw_pdf_header(p, width, height, x_margin, y_margin, header_ctx)
    y = _draw_pdf_table_headers(p, x_margin, y, headers, col_widths)
    p.setFont('Helvetica', 6)

    for item in data:
        if y < y_margin + 0.5 * inch:
            p.showPage()
            width, height = landscape(letter)
            y = _draw_pdf_header(p, width, height, x_margin, y_margin, header_ctx)
            y = _draw_pdf_table_headers(p, x_margin, y, headers, col_widths)
            p.setFont('Helvetica', 6)

        row_hex = _normalize_hex_color(item.get('row_color'))
        if row_hex:
            x_bg = x_margin
            p.saveState()
            p.setFillColor(colors.HexColor(f"#{row_hex}"))
            for w in col_widths:
                p.rect(x_bg, y - 0.06 * inch, w, 0.18 * inch, stroke=0, fill=1)
                x_bg += w
            p.restoreState()

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
            text = _fit_text_to_width(text, col_widths[i] - 4, 'Helvetica', 6)
            txt_w = pdfmetrics.stringWidth(text, 'Helvetica', 6)
            p.drawString(x + max((col_widths[i] - txt_w) / 2, 0), y, text)
            x += col_widths[i]

        y -= 0.2 * inch

    p.showPage()
    p.save()
    return response