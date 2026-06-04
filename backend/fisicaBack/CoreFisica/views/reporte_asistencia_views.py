from django.http import JsonResponse
from django.db.models import Q, F, Subquery
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
import datetime
from pathlib import Path
from types import SimpleNamespace
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona, ReporteAsistencia, ReporteAsistenciaHistorial, AsignacionSemanal, SacafrancoFilaSemanal
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

ZONAS_VALIDAS = {'ZONA 1', 'ZONA 2', 'ZONA 3'}


def _normalize_zona_filter(zona_param):
    zona_raw = str(zona_param or '').strip()
    if not zona_raw:
        return ''
    zona_upper = zona_raw.upper()
    if zona_upper in ZONAS_VALIDAS:
        return f"Zona {zona_upper.split()[-1]}"
    return ''


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
        this_file.parents[i] for i in [4, 3] if i < len(this_file.parents)
    ] + [Path.cwd()]
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
    ws.merge_cells('G4:I4')

    for row in range(1, 5):
        for col in range(1, 10):
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

    title_text = str(ctx['titulo'] or '')
    title_font = 15
    max_title_w = title_w - 0.20 * inch
    while title_font > 9 and pdfmetrics.stringWidth(title_text, 'Helvetica-Bold', title_font) > max_title_w:
        title_font -= 1

    p.setFont('Helvetica-Bold', title_font)
    title_y = top - (top_h / 2) + 0.1 * inch
    p.drawCentredString(x_title + (title_w / 2), title_y, title_text)

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


def _normalize_estado_asistencia(value):
    v = str(value or '').strip().upper()
    if v in ('ASISTIO', 'FALTO'):
        return v
    return ''


def _is_auto_sacafranco_desc(desc):
    return str(desc or '').strip().upper().startswith('COBERTURA SACAFRANCO AUTO')


def _is_falto(item):
    return str(item.get('estado_asistencia') or '').strip().upper() == 'FALTO'


def _zona_sort_key(zona_titulo):
    z = str(zona_titulo or '').strip().lower()
    if z == 'zona 1':
        return (0, z)
    if z == 'zona 2':
        return (1, z)
    if z == 'zona 3':
        return (2, z)
    return (99, z)


def _normalize_zona_label(zona_titulo):
    z = str(zona_titulo or '').strip().lower()
    if z == 'zona 1':
        return 'Zona 1'
    if z == 'zona 2':
        return 'Zona 2'
    if z == 'zona 3':
        return 'Zona 3'
    return str(zona_titulo or '').strip()


def _format_zona_label(zona_titulo):
    label = _normalize_zona_label(zona_titulo)
    if label.lower().startswith('zona '):
        return label
    return f"Zona {label}" if label else 'Zona'


def _build_resumen_asistencia(data):
    evaluables = [item for item in data if item.get('asignacion_id')]
    faltos = sum(1 for item in evaluables if _is_falto(item))
    asistencias = max(len(evaluables) - faltos, 0)
    return asistencias, faltos


def _build_resumen_asistencia_por_zona(data):
    evaluables = [item for item in data if item.get('asignacion_id')]
    zonas = {}
    for item in evaluables:
        zona = _normalize_zona_label((item.get('zona_titulo') or 'SIN ZONA').strip())
        entry = zonas.setdefault(zona, {'total': 0, 'faltas': 0})
        entry['total'] += 1
        if _is_falto(item):
            entry['faltas'] += 1

    resumen = []
    for zona in sorted(zonas.keys(), key=_zona_sort_key):
        total = zonas[zona]['total']
        faltas = zonas[zona]['faltas']
        resumen.append({
            'zona': zona,
            'total': total,
            'asistencias': max(total - faltas, 0),
            'faltas': faltas,
        })
    return resumen


def _group_reporte_por_zona_y_provincia(data):
    zonas = {}
    for item in data:
        if item.get('asignacion_id'):
            zona = _normalize_zona_label((item.get('zona_titulo') or 'SIN ZONA').strip())
            provincia = (item.get('provincia') or 'SIN PROVINCIA').strip()
        else:
            zona = 'SIN ASIGNACION'
            provincia = 'SIN ASIGNACION'
        zonas.setdefault(zona, {}).setdefault(provincia, []).append(item)

    grouped = []
    for zona in sorted(zonas.keys(), key=_zona_sort_key):
        provincias = []
        for prov in sorted(zonas[zona].keys(), key=lambda v: str(v).lower()):
            provincias.append({
                'provincia': prov,
                'rows': zonas[zona][prov],
            })
        grouped.append({'zona': zona, 'provincias': provincias})
    return grouped


def _write_excel_resumen(ws, row_idx, asistencias, faltos, border):
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
    ws.merge_cells(start_row=row_idx, start_column=5, end_row=row_idx, end_column=9)

    left_cell = ws.cell(row=row_idx, column=1)
    left_cell.value = f"{asistencias}\nASISTENCIAS"
    left_cell.font = Font(bold=True, color='9C0006', size=12)
    left_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_cell.fill = PatternFill(start_color='E6B8BE', end_color='E6B8BE', fill_type='solid')

    right_cell = ws.cell(row=row_idx, column=5)
    right_cell.value = f"{faltos}\nFALTOS"
    right_cell.font = Font(bold=True, color='000000', size=12)
    right_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for col_idx in range(1, 10):
        ws.cell(row=row_idx, column=col_idx).border = border
    ws.row_dimensions[row_idx].height = 38
    return row_idx


def _reemplazo_esta_ocupado(persona_id, fecha_reporte=None, asignacion_id_actual=None):
    # A replacement must be a free person: no active assignment and not already used
    # as replacement on the same report date.
    if Asignacion.objects.filter(persona_id=persona_id, estado='ACTIVO').exists():
        return True, 'La persona seleccionada ya tiene una asignacion activa.'

    if fecha_reporte:
        qs = ReporteAsistencia.objects.filter(
            fecha_reporte=fecha_reporte,
            reemplazo_id=persona_id,
        )
        if asignacion_id_actual:
            qs = qs.exclude(asignacion_id=asignacion_id_actual)
        if qs.exists():
            return True, 'La persona seleccionada ya esta asignada como reemplazo en este reporte.'

    return False, ''


def _resolver_reemplazo_desde_request(request, fecha_reporte=None, asignacion_id_actual=None):
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

    ocupado, motivo = _reemplazo_esta_ocupado(
        persona_id=persona.id,
        fecha_reporte=fecha_reporte,
        asignacion_id_actual=asignacion_id_actual,
    )
    if ocupado:
        return None, JsonResponse(
            {'error': motivo},
            status=status.HTTP_400_BAD_REQUEST
        )

    return persona, None



def _build_reporte_asistencia_data(
    fecha=None,
    cliente_id=None,
    turno=None,
    exclude_sacafranco=False,
    zona='',
    q='',
    page=None,
    page_size=None,
    include_total=False,
):
    fecha_obj = None
    if fecha:
        try:
            fecha_obj = datetime.date.fromisoformat(str(fecha))
        except ValueError:
            fecha_obj = None

    hoy = timezone.localdate()
    fin_anio_actual = datetime.date(hoy.year, 12, 31)

    reporte_qs = ReporteAsistencia.objects.select_related('asignacion', 'modificado_por', 'reemplazo')
    # Solo considerar overrides de asignaciones activas
    reporte_qs = reporte_qs.filter(asignacion__estado='ACTIVO')
    historial_asig_ids_qs = ReporteAsistenciaHistorial.objects.none().values('asignacion_id')
    if fecha_obj:
        reporte_qs = reporte_qs.filter(fecha_reporte=fecha_obj)
        historial_asig_ids_qs = ReporteAsistenciaHistorial.objects.filter(
            fecha_reporte=fecha_obj,
            asignacion__estado='ACTIVO'
        ).values('asignacion_id').distinct()

    asig_qs = Asignacion.objects.select_related(
        'cliente', 'instalacion', 'instalacion__canton', 'instalacion__canton__provincia',
        'puesto', 'horario', 'persona'
    ).prefetch_related('instalacion__zonas').filter(
        persona__is_active=True,
        estado='ACTIVO'
    ).exclude(persona__tipo='SACAFRANCO')

    if fecha_obj:
        # Reporte por rango hasta fin de anio actual cuando la fecha es hoy/futura.
        if fecha_obj >= hoy:
            # Mantener visibilidad de asignaciones vigentes durante todo el anio actual.
            asig_qs = asig_qs.filter(anio=hoy.year)
            asig_qs = asig_qs.filter(
                Q(fecha__gte=fecha_obj, fecha__lte=fin_anio_actual) |
                Q(fecha__isnull=True) |
                Q(id__in=reporte_qs.values('asignacion_id')) |
                Q(id__in=historial_asig_ids_qs)
            )
        else:
            asig_qs = asig_qs.filter(anio=fecha_obj.year, mes=fecha_obj.month)
            asig_qs = asig_qs.filter(
                Q(fecha=fecha_obj) |
                Q(id__in=reporte_qs.values('asignacion_id')) |
                Q(id__in=historial_asig_ids_qs)
            )
    if cliente_id:
        asig_qs = asig_qs.filter(cliente_id=cliente_id)
    if zona:
        asig_qs = asig_qs.filter(instalacion__zonas__titulo__iexact=zona).distinct()
    if turno in ['Diurno', 'Nocturno']:
        asig_qs = asig_qs.filter(
            Q(puesto__horarios__turno=turno)
            | Q(puesto__horarios__turno='Ambos')
            # Horario con misma hora de ingreso/salida se interpreta como cobertura 24h
            | Q(horario__hora_ingreso=F('horario__hora_salida'))
        ).distinct()

    if exclude_sacafranco:
        # Excluir asignaciones marcadas como cobertura de sacafranco (F) en la fecha consultada.
        fecha_ref = fecha_obj or hoy
        day_field_map = {
            0: 'mon',
            1: 'tue',
            2: 'wed',
            3: 'thu',
            4: 'fri',
            5: 'sat',
            6: 'sun',
        }
        day_field = day_field_map.get(fecha_ref.weekday())
        if day_field:
            # Semana estilo calendario mensual del sistema (dia 1 y saltos de 7)
            month_base = fecha_ref.replace(day=1)
            week_start_month = month_base + datetime.timedelta(days=((fecha_ref.day - 1) // 7) * 7)
            # Semana estilo ISO (lunes)
            week_start_iso = fecha_ref - datetime.timedelta(days=fecha_ref.weekday())

            sacafranco_asig_ids = AsignacionSemanal.objects.filter(
                week_start__in=[week_start_month, week_start_iso],
                **{f"{day_field}__istartswith": 'F'}
            ).exclude(asignacion_id__isnull=True).values_list('asignacion_id', flat=True)

            asig_qs = asig_qs.exclude(id__in=sacafranco_asig_ids)

    term = (q or '').strip().lower()
    # Keep pagination in-memory for date report so BASE rows (NB/DB) can be merged reliably.
    use_db_pagination = bool(include_total and page and page_size and not term and not fecha_obj)
    ordered_qs = asig_qs.order_by('mes', 'fecha', 'id')

    total = None
    if use_db_pagination:
        total = ordered_qs.count()
        start = (int(page) - 1) * int(page_size)
        end = start + int(page_size)
        ordered_qs = ordered_qs[start:end]

    asig_list = list(ordered_qs)
    asig_ids = [a.id for a in asig_list]

    overrides = {}
    if fecha_obj:
        latest_hist_ids = ReporteAsistenciaHistorial.objects.filter(
            fecha_reporte=fecha_obj
        )
        if use_db_pagination and asig_ids:
            latest_hist_ids = latest_hist_ids.filter(asignacion_id__in=asig_ids)
        latest_hist_ids = latest_hist_ids.order_by('asignacion_id', '-creado_en').distinct('asignacion_id').values('id')

        hist_qs = ReporteAsistenciaHistorial.objects.select_related('usuario', 'reemplazo')
        hist_qs = hist_qs.filter(id__in=Subquery(latest_hist_ids)).order_by('asignacion_id')
        for h in hist_qs:
            is_auto_sacafranco = _is_auto_sacafranco_desc(h.descripcion)
            overrides[h.asignacion_id] = SimpleNamespace(
                codigo=h.codigo,
                estado=h.estado,
                estado_asistencia=getattr(h, 'estado_asistencia', None),
                descripcion=h.descripcion,
                reemplazo=h.reemplazo,
                persona_cobertura=h.reemplazo if is_auto_sacafranco else None,
                auto_sacafranco=is_auto_sacafranco,
                modificado_por=h.usuario,
                modificado_en=h.creado_en,
                row_color=h.row_color
            )

    reporte_iter = reporte_qs
    if use_db_pagination and asig_ids:
        reporte_iter = reporte_iter.filter(asignacion_id__in=asig_ids)
    for r in reporte_iter:
        if r.asignacion_id not in overrides:
            overrides[r.asignacion_id] = r

    data = []
    personas_con_asignacion = set()
    for asig in asig_list:
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
        auto_sacafranco = _is_auto_sacafranco_desc(getattr(override, 'descripcion', '')) if override else False
        persona_cobertura = None
        if override:
            persona_cobertura = getattr(override, 'persona_cobertura', None)
            if not persona_cobertura and auto_sacafranco:
                persona_cobertura = getattr(override, 'reemplazo', None)
        if auto_sacafranco and persona_cobertura:
            nombre_apellidos = f"{persona_cobertura.nombres} {persona_cobertura.apellidos}".strip()
        zona_titulo = ''
        provincia_nombre = ''
        if asig and asig.instalacion:
            # Use prefetched zones to avoid one DB hit per row.
            zona_obj = next(iter(asig.instalacion.zonas.all()), None)
            if zona_obj:
                zona_titulo = zona_obj.titulo
        if asig and asig.instalacion and asig.instalacion.canton and asig.instalacion.canton.provincia:
            provincia_nombre = asig.instalacion.canton.provincia.nombre
        reemplazo_nombre = ''
        reemplazo_id = None
        if override and override.reemplazo:
            reemplazo_id = override.reemplazo.id
            reemplazo_nombre = f"{override.reemplazo.nombres} {override.reemplazo.apellidos}".strip()
        if auto_sacafranco:
            reemplazo_id = None
            reemplazo_nombre = ''

        modificado_por_nombre = ''
        modificado_en_iso = None
        if override:
            if override.modificado_por:
                full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
                modificado_por_nombre = full_name or override.modificado_por.get_username()
            modificado_en_iso = override.modificado_en.isoformat() if override.modificado_en else None

        codigo_instalacion = getattr(asig.instalacion, 'codigo', '') if asig and asig.instalacion else ''
        estado_asistencia = _normalize_estado_asistencia(getattr(override, 'estado_asistencia', '') if override else '')
        estado = (getattr(override, 'estado', None) if override else None) or 'TURNO'
        descripcion = (override.descripcion or '') if override else ''
        if auto_sacafranco:
            puesto_nombre = ''
            horario_str = ''
            estado = ''
            estado_asistencia = ''
            descripcion = ''

        data.append({
            'asignacion_id': asig.id,
            'codigo': override.codigo if (override and override.codigo) else (codigo_instalacion or ''),
            'cliente': cliente_nombre,
            'puesto': puesto_nombre,
            'horario': horario_str,
            'nombre_apellidos': nombre_apellidos,
            'reemplazo_id': reemplazo_id,
            'reemplazo': reemplazo_nombre,
            'estado_asistencia': estado_asistencia,
            'estado': estado,
            'descripcion': descripcion,
            'modificado_por': modificado_por_nombre,
            'row_color': (override.row_color or '') if override else '',
            'modificado_en': modificado_en_iso,
            'zona_titulo': zona_titulo,
            'provincia': provincia_nombre,
        })

    # Include BASE rows (NB/DB) directly from sacafranco weekly calendar tokens.
    if fecha_obj and turno in ['Diurno', 'Nocturno']:
        day_key_map = {
            0: 'mon',
            1: 'tue',
            2: 'wed',
            3: 'thu',
            4: 'fri',
            5: 'sat',
            6: 'sun',
        }

        def _asig_active_on_date(asig, target_date):
            if not asig or getattr(asig, 'estado', '') != 'ACTIVO':
                return False
            if getattr(asig, 'recurring', False):
                start_date = getattr(asig, 'start_date', None)
                end_date = getattr(asig, 'end_date', None)
                if start_date and target_date < start_date:
                    return False
                if end_date and target_date > end_date:
                    return False
                return True
            fecha_asig = getattr(asig, 'fecha', None)
            if fecha_asig:
                return fecha_asig == target_date
            return (getattr(asig, 'mes', None) == target_date.month and getattr(asig, 'anio', None) == target_date.year)

        def _asig_turno_matches(asig, target_turno):
            tokens = set()
            try:
                horarios_qs = getattr(asig.puesto, 'horarios', None)
                if horarios_qs is not None:
                    turnos = horarios_qs.values_list('turno', flat=True)
                    tokens = {str(t or '').strip().lower() for t in turnos if t}
            except Exception:
                tokens = set()

            if any(t.startswith('a') for t in tokens):
                return True
            if target_turno == 'Diurno' and any(t.startswith('d') for t in tokens):
                return True
            if target_turno == 'Nocturno' and any(t.startswith('n') for t in tokens):
                return True

            try:
                if asig.horario and asig.horario.hora_ingreso == asig.horario.hora_salida:
                    return True
            except Exception:
                pass
            return False

        def _resolve_base_context(provincia_id_val, target_date, target_turno, zona_filter):
            qs = Asignacion.objects.select_related(
                'cliente', 'instalacion', 'instalacion__canton', 'instalacion__canton__provincia', 'puesto', 'horario', 'persona'
            ).prefetch_related('instalacion__zonas', 'puesto__horarios').filter(
                estado='ACTIVO',
                persona__is_active=True,
            ).exclude(persona__tipo='SACAFRANCO')

            if provincia_id_val:
                qs = qs.filter(instalacion__canton__provincia_id=provincia_id_val)
            if zona_filter:
                qs = qs.filter(instalacion__zonas__titulo__iexact=zona_filter).distinct()

            candidates = []
            for asig in qs.order_by('orden', 'id'):
                if not _asig_active_on_date(asig, target_date):
                    continue
                if not _asig_turno_matches(asig, target_turno):
                    continue
                candidates.append(asig)

            selected = None
            if candidates:
                def _rank(a):
                    cliente_nom = str(getattr(getattr(a, 'cliente', None), 'nombre_comercial', '') or '').upper()
                    pref_cliente = 0 if 'OCEANSECURITY' in cliente_nom else 1
                    orden_val = getattr(a, 'orden', None)
                    orden_rank = orden_val if isinstance(orden_val, int) else 999999
                    return (pref_cliente, orden_rank, a.id)

                selected = sorted(candidates, key=_rank)[0]

            if not selected:
                return {
                    'codigo': 'BASE',
                    'cliente': 'OCEANSECURITY',
                    'puesto': 'Libre en base',
                    'zona_titulo': zona_filter or 'SIN ZONA',
                }

            zona_titulo = zona_filter or ''
            try:
                zona_obj = next(iter(selected.instalacion.zonas.all()), None)
                if zona_obj and getattr(zona_obj, 'titulo', None):
                    zona_titulo = zona_obj.titulo
            except Exception:
                pass

            return {
                'codigo': str(getattr(getattr(selected, 'instalacion', None), 'codigo', '') or '').strip() or 'BASE',
                'cliente': getattr(getattr(selected, 'cliente', None), 'nombre_comercial', '') or 'OCEANSECURITY',
                'puesto': getattr(getattr(selected, 'puesto', None), 'nombre', '') or 'Libre en base',
                'zona_titulo': zona_titulo or 'SIN ZONA',
            }

        day_key = day_key_map.get(fecha_obj.weekday())
        token_expected = 'DB' if turno == 'Diurno' else 'NB'
        if day_key:
            month_base = fecha_obj.replace(day=1)
            week_start_month = month_base + datetime.timedelta(days=((fecha_obj.day - 1) // 7) * 7)
            week_start_iso = fecha_obj - datetime.timedelta(days=fecha_obj.weekday())

            sac_qs = SacafrancoFilaSemanal.objects.select_related(
                'sacafranco_fila', 'sacafranco_fila__persona', 'sacafranco_fila__provincia'
            ).filter(week_start__in=[week_start_month, week_start_iso])

            seen_fila_ids = set()
            for row in sac_qs:
                token_val = str(getattr(row, day_key, '') or '').strip().upper()
                if token_val != token_expected:
                    continue

                fila = getattr(row, 'sacafranco_fila', None)
                persona = getattr(fila, 'persona', None) if fila else None
                if not fila or not persona:
                    continue
                if fila.id in seen_fila_ids:
                    continue
                seen_fila_ids.add(fila.id)

                provincia_obj = getattr(fila, 'provincia', None) or getattr(persona, 'provincia', None)
                provincia_id_val = getattr(fila, 'provincia_id', None) or getattr(persona, 'provincia_id', None)
                provincia_nombre = getattr(provincia_obj, 'nombre', None) or 'SIN PROVINCIA'
                persona_nombre = f"{persona.nombres} {persona.apellidos}".strip()

                ctx = _resolve_base_context(
                    provincia_id_val=provincia_id_val,
                    target_date=fecha_obj,
                    target_turno=turno,
                    zona_filter=_normalize_zona_filter(zona) if zona else '',
                )

                data.append({
                    'asignacion_id': None,
                    'codigo': ctx.get('codigo') or 'BASE',
                    'cliente': ctx.get('cliente') or 'OCEANSECURITY',
                    'puesto': ctx.get('puesto') or 'Libre en base',
                    'horario': '',
                    'nombre_apellidos': persona_nombre or 'Libre en base',
                    'reemplazo_id': None,
                    'reemplazo': '',
                    'estado_asistencia': '',
                    'estado': 'TURNO',
                    'descripcion': 'Libre en base',
                    'modificado_por': '',
                    'row_color': '',
                    'modificado_en': None,
                    'zona_titulo': ctx.get('zona_titulo') or (_normalize_zona_filter(zona) if zona else 'SIN ZONA'),
                    'provincia': provincia_nombre,
                })

    if term:
        filtered = []
        for item in data:
            haystack = ' '.join([
                str(item.get('codigo') or ''),
                str(item.get('cliente') or ''),
                str(item.get('puesto') or ''),
                str(item.get('horario') or ''),
                str(item.get('nombre_apellidos') or ''),
                str(item.get('estado') or ''),
                str(item.get('estado_asistencia') or ''),
                str(item.get('reemplazo') or ''),
                str(item.get('descripcion') or ''),
                str(item.get('zona_titulo') or ''),
                str(item.get('provincia') or ''),
            ]).lower()
            if term in haystack:
                filtered.append(item)
        data = filtered

    if include_total:
        if use_db_pagination:
            return data, int(total or 0), True
        return data, len(data), False

    return data

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_asistencia(request):
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    turno = request.GET.get('turno')
    q = (request.GET.get('q') or '').strip()
    zona = _normalize_zona_filter(request.GET.get('zona'))
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        page_size = min(page_size, 200)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Parámetros de paginación inválidos'}, status=400)

    exclude_sacafranco = str(request.GET.get('exclude_sacafranco', '')).strip() == '1'
    data, total, db_paginated = _build_reporte_asistencia_data(
        fecha=fecha,
        cliente_id=cliente_id,
        turno=turno,
        exclude_sacafranco=exclude_sacafranco,
        zona=zona,
        q=q,
        page=page,
        page_size=page_size,
        include_total=True,
    )

    start = (page - 1) * page_size
    end = start + page_size
    page_results = data if db_paginated else data[start:end]
    total_pages = (total + page_size - 1) // page_size if total else 1

    return JsonResponse({
        'results': page_results,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'zona': zona or None,
    }, safe=False, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def insertar_reporte_asistencia(request, asignacion_id):
    if not request.user.has_perm('CoreFisica.change_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

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

    override.codigo = getattr(asignacion.instalacion, 'codigo', None)

    for field in ['estado', 'estado_asistencia', 'descripcion', 'row_color']:
        if field in request.data:
            val = request.data.get(field) or None
            setattr(override, field, val)

    fecha_reporte = override.fecha_reporte
    if 'fecha' in request.data:
        fecha_param = request.data.get('fecha')
        if fecha_param in [None, '', 'null']:
            fecha_reporte = None
        else:
            try:
                fecha_reporte = datetime.date.fromisoformat(str(fecha_param))
            except ValueError:
                fecha_reporte = None

    reemplazo_result, err = _resolver_reemplazo_desde_request(
        request,
        fecha_reporte=fecha_reporte,
        asignacion_id_actual=asignacion_id,
    )
    if err:
        return err
    if reemplazo_result != 'no-enviado':
        override.reemplazo = reemplazo_result

    if request.user and request.user.is_authenticated:
        override.modificado_por = request.user
    override.fecha_reporte = fecha_reporte
    override.modificado_en = timezone.now()
    override.save()

    try:
        ReporteAsistenciaHistorial.objects.create(
            reporte=override,
            asignacion=asignacion,
            fecha_reporte=override.fecha_reporte,
            usuario=request.user if request.user and request.user.is_authenticated else None,
            codigo=override.codigo,
            estado_asistencia=override.estado_asistencia,
            estado=override.estado,
            reemplazo=override.reemplazo,
            descripcion=override.descripcion,
            row_color=override.row_color
        )
    except Exception:
        pass

    modificado_por_nombre = ''
    if override.modificado_por:
        full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
        modificado_por_nombre = full_name or override.modificado_por.get_username()

    reemplazo_nombre = ''
    if override.reemplazo:
        reemplazo_nombre = f"{override.reemplazo.nombres} {override.reemplazo.apellidos}".strip()

    return JsonResponse({
        'codigo': override.codigo or '',
        'estado_asistencia': _normalize_estado_asistencia(override.estado_asistencia),
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
def historial_reporte_asistencia(request, asignacion_id):
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    fecha = request.GET.get('fecha')
    qs = ReporteAsistenciaHistorial.objects.select_related('usuario', 'reemplazo').filter(
        asignacion_id=asignacion_id
    )
    if fecha:
        try:
            fecha_obj = datetime.date.fromisoformat(str(fecha))
            qs = qs.filter(fecha_reporte=fecha_obj)
        except ValueError:
            pass

    data = []
    for h in qs:
        usuario_nombre = ''
        if h.usuario:
            full_name = f"{h.usuario.first_name} {h.usuario.last_name}".strip()
            usuario_nombre = full_name or h.usuario.get_username()
        reemplazo_nombre = ''
        if h.reemplazo:
            reemplazo_nombre = f"{h.reemplazo.nombres} {h.reemplazo.apellidos}".strip()
        data.append({
            'fecha_reporte': h.fecha_reporte.isoformat() if h.fecha_reporte else None,
            'usuario': usuario_nombre,
            'codigo': h.codigo or '',
            'estado_asistencia': _normalize_estado_asistencia(h.estado_asistencia),
            'estado': h.estado or '',
            'reemplazo': reemplazo_nombre,
            'descripcion': h.descripcion or '',
            'row_color': h.row_color or '',
            'creado_en': h.creado_en.isoformat() if h.creado_en else None,
        })

    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reporte_asistencia_excel(request):
    if not request.user.has_perm('CoreFisica.export_reporte_asistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    q = (request.GET.get('q') or '').strip()
    zona = _normalize_zona_filter(request.GET.get('zona'))
    headers = [
        'NOMINATIVO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ASISTENCIA', 'REEMPLAZO', 'ESTADO', 'DESCRIPCIÓN',
    ]
    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def render_sheet(ws, turno_val):
        data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno_val, zona=zona, q=q)
        header_ctx = _build_header_context(request, fecha, turno_val)
        asistencias, faltos = _build_resumen_asistencia(data)
        grouped = _group_reporte_por_zona_y_provincia(data)
        zona_resumen = []

        _draw_excel_header(ws, header_ctx, border)

        header_row = 6
        data_start_row = header_row + 1

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.value = header
            cell.border = border
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')

        current_row = data_start_row
        for zona_group in grouped:
            # Fila de zona
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
            zona_cell = ws.cell(row=current_row, column=1)
            zona_cell.value = _normalize_zona_label(zona_group['zona'])
            zona_cell.font = Font(bold=True, size=11)
            zona_cell.alignment = Alignment(horizontal='left', vertical='center')
            for col_idx in range(1, 10):
                ws.cell(row=current_row, column=col_idx).border = border
            ws.row_dimensions[current_row].height = 24
            current_row += 1

            zona_items = []
            for prov_group in zona_group['provincias']:
                # Fila de provincia
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
                prov_cell = ws.cell(row=current_row, column=1)
                prov_cell.value = str(prov_group['provincia']).upper()
                prov_cell.font = Font(bold=True, size=10)
                prov_cell.alignment = Alignment(horizontal='left', vertical='center')
                for col_idx in range(1, 10):
                    ws.cell(row=current_row, column=col_idx).border = border
                ws.row_dimensions[current_row].height = 22
                current_row += 1

                for item in prov_group['rows']:
                    zona_items.append(item)
                    row_hex = _normalize_hex_color(item.get('row_color'))
                    row_fill = PatternFill(start_color=row_hex, end_color=row_hex, fill_type='solid') if row_hex else None
                    row_vals = [
                        item.get('codigo', ''),
                        item.get('cliente', ''),
                        item.get('puesto', ''),
                        item.get('horario', ''),
                        item.get('nombre_apellidos', ''),
                        'ASISTE' if item.get('estado_asistencia') == 'ASISTIO' else ('FALTO' if item.get('estado_asistencia') == 'FALTO' else ''),
                        item.get('reemplazo', ''),
                        item.get('estado', ''),
                        item.get('descripcion', ''),
                    ]
                    for col_idx, value in enumerate(row_vals, start=1):
                        cell = ws.cell(row=current_row, column=col_idx)
                        cell.value = value
                        cell.border = border
                        if row_fill:
                            cell.fill = row_fill
                        if col_idx == 9:
                            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                        else:
                            cell.alignment = Alignment(horizontal='center', vertical='center')
                    ws.row_dimensions[current_row].height = 32
                    current_row += 1

            zona_asistencias, zona_faltos = _build_resumen_asistencia(zona_items)
            zona_resumen.append((zona_group['zona'], zona_asistencias, zona_faltos))
            _write_excel_resumen(ws, current_row, zona_asistencias, zona_faltos, border)
            current_row += 2

        column_widths = {
            1: 11,  # Codigo
            2: 18,  # Cliente
            3: 23,  # Puesto
            4: 12,  # Horario
            5: 40,  # Nombre y Apellidos
            6: 14,  # Asistencia
            7: 38,  # Reemplazo
            8: 12,  # Estado
            9: 28,  # Descripcion
        }
        for col_idx, width in column_widths.items():
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        # Resumen global removido; se deja solo el resumen por zona.
        current_row += 1
        for zona_label, zona_asistencias, zona_faltos in zona_resumen:
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=2)
            ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=5)
            ws.merge_cells(start_row=current_row, start_column=6, end_row=current_row, end_column=9)

            zcell = ws.cell(row=current_row, column=1)
            zcell.value = _format_zona_label(zona_label)
            zcell.font = Font(bold=True)
            zcell.alignment = Alignment(horizontal='left', vertical='center')

            acell = ws.cell(row=current_row, column=3)
            acell.value = f"Asistencias: {zona_asistencias}"
            acell.alignment = Alignment(horizontal='center', vertical='center')

            fcell = ws.cell(row=current_row, column=6)
            fcell.value = f"Faltas: {zona_faltos}"
            fcell.alignment = Alignment(horizontal='center', vertical='center')

            for col_idx in range(1, 10):
                ws.cell(row=current_row, column=col_idx).border = border
            current_row += 1

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'DIURNO'
    render_sheet(ws, 'Diurno')

    ws_nocturno = wb.create_sheet('NOCTURNO')
    render_sheet(ws_nocturno, 'Nocturno')

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.xlsx"'
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response.write(output.getvalue())
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reporte_asistencia_pdf(request):
    if not request.user.has_perm('CoreFisica.export_reporte_asistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    turno = request.GET.get('turno')
    q = (request.GET.get('q') or '').strip()
    zona = _normalize_zona_filter(request.GET.get('zona'))
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno, zona=zona, q=q)
    header_ctx = _build_header_context(request, fecha, turno)
    asistencias, faltos = _build_resumen_asistencia(data)
    grouped = _group_reporte_por_zona_y_provincia(data)
    zona_resumen = []

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=landscape(letter))
    width, height = landscape(letter)

    x_margin = 0.5 * inch
    y_margin = 0.5 * inch

    headers = [
        'NOMINATIVO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ASISTENCIA', 'REEMPLAZO', 'ESTADO', 'DESCRIPCIÓN',
    ]

    col_widths = [0.75, 1.15, 1.1, 0.6, 1.75, 0.7, 0.8, 1.5, 1.0]
    col_widths = [w * inch for w in col_widths]

    def ensure_space(y_cursor, needed_height):
        if y_cursor < y_margin + needed_height:
            p.showPage()
            page_width, page_height = landscape(letter)
            new_y = _draw_pdf_header(p, page_width, page_height, x_margin, y_margin, header_ctx)
            new_y = _draw_pdf_table_headers(p, x_margin, new_y, headers, col_widths)
            p.setFont('Helvetica', 6)
            return new_y
        return y_cursor

    def draw_group_row(y_cursor, text, font_size=7):
        y_cursor = ensure_space(y_cursor, 0.3 * inch)
        p.setFont('Helvetica-Bold', font_size)
        p.setFillColor(colors.black)
        p.drawString(x_margin + 6, y_cursor, text)
        p.setFont('Helvetica', 6)
        return y_cursor - 0.2 * inch

    def draw_resumen(y_cursor, asistencias_val, faltos_val):
        y_cursor = ensure_space(y_cursor, 0.9 * inch)
        box_h = 0.55 * inch
        box_gap = 1.2 * inch
        box_w = ((width - (2 * x_margin)) - box_gap) / 2

        x1 = x_margin
        x2 = x1 + box_w + box_gap
        y_bottom = y_cursor - box_h

        p.setStrokeColor(colors.black)

        p.setFillColor(colors.HexColor('#E6B8BE'))
        p.rect(x1, y_bottom, box_w, box_h, stroke=1, fill=1)

        p.setFillColor(colors.white)
        p.rect(x2, y_bottom, box_w, box_h, stroke=1, fill=1)

        p.setFont('Helvetica-Bold', 11)
        p.setFillColor(colors.HexColor('#9C0006'))
        p.drawCentredString(x1 + (box_w / 2), y_bottom + 0.34 * inch, str(asistencias_val))
        p.drawCentredString(x1 + (box_w / 2), y_bottom + 0.12 * inch, 'ASISTENCIAS')

        p.setFillColor(colors.black)
        p.drawCentredString(x2 + (box_w / 2), y_bottom + 0.34 * inch, str(faltos_val))
        p.drawCentredString(x2 + (box_w / 2), y_bottom + 0.12 * inch, 'FALTOS')

        return y_bottom - 0.3 * inch

    y = _draw_pdf_header(p, width, height, x_margin, y_margin, header_ctx)
    y = _draw_pdf_table_headers(p, x_margin, y, headers, col_widths)
    p.setFont('Helvetica', 6)

    for zona_group in grouped:
        y = draw_group_row(y, _normalize_zona_label(zona_group['zona']), 8)
        zona_items = []
        for prov_group in zona_group['provincias']:
            y = draw_group_row(y, str(prov_group['provincia']).upper(), 7)
            for item in prov_group['rows']:
                zona_items.append(item)
                y = ensure_space(y, 0.3 * inch)

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
                    'ASISTE' if item.get('estado_asistencia') == 'ASISTIO' else ('FALTO' if item.get('estado_asistencia') == 'FALTO' else ''),
                    item.get('reemplazo', ''),
                    item.get('estado', ''),
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

        zona_asistencias, zona_faltos = _build_resumen_asistencia(zona_items)
        zona_resumen.append((zona_group['zona'], zona_asistencias, zona_faltos))
        y = draw_resumen(y, zona_asistencias, zona_faltos)

    if zona_resumen:
        y = ensure_space(y, 0.4 * inch)
        p.setFont('Helvetica', 7)
        for zona_label, zona_asistencias, zona_faltos in zona_resumen:
            label = _format_zona_label(zona_label)
            p.setFont('Helvetica-Bold', 7)
            p.drawString(x_margin, y, f"{label}:")
            p.setFont('Helvetica', 7)
            p.drawString(x_margin + 1.0 * inch, y, f"Asistencias: {zona_asistencias}")
            p.drawString(x_margin + 3.2 * inch, y, f"Faltas: {zona_faltos}")
            y -= 0.18 * inch
        y -= 0.1 * inch

    p.showPage()
    p.save()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.pdf"'
    output.seek(0)
    response.write(output.getvalue())
    return response