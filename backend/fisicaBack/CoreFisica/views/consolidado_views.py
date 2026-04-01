from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
import datetime
import openpyxl
from openpyxl.styles import Alignment, Border, Side, Font
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from ..models import Consolidado, PersonalConsola, Asignacion
from .reporte_asistencia_views import _build_reporte_asistencia_data

ALLOWED_TURNOS = {choice[0] for choice in PersonalConsola.TURNOS}
ALLOWED_TIPOS = {choice[0] for choice in Consolidado.TIPOS}
TIPO_CONSOLA = 'CONSOLa'
TIPO_GUARDIA = 'GUARDIA'


def _parse_fecha(fecha_param):
    if fecha_param:
        try:
            return datetime.date.fromisoformat(str(fecha_param))
        except ValueError:
            pass
    return timezone.localdate()


def _build_consolidado_data(fecha, turno):
    fecha_obj = _parse_fecha(fecha)
    turno_val = turno if turno in ALLOWED_TURNOS else None

    consolidados_qs = Consolidado.objects.filter(fecha=fecha_obj)
    if turno_val:
        consolidados_qs = consolidados_qs.filter(turno=turno_val)
    consolidado_map = {
        (c.tipo, c.referencia_id): c
        for c in consolidados_qs
    }

    consola_qs = PersonalConsola.objects.filter(is_active=True)
    if turno_val:
        consola_qs = consola_qs.filter(turno=turno_val)
    consola_qs = consola_qs.order_by('apellidos', 'nombres')

    data = []
    for item in consola_qs:
        cons = consolidado_map.get((TIPO_CONSOLA, item.id))
        data.append({
            'consolidado_id': cons.id if cons else None,
            'fecha': fecha_obj.isoformat(),
            'turno': turno_val or item.turno,
            'tipo': TIPO_CONSOLA,
            'referencia_id': item.id,
            'nominativo': '',
            'proyecto': '',
            'apellidos': item.apellidos,
            'nombres': item.nombres,
            'estado': item.tipo,
            'observacion': cons.observacion if cons else '',
            'zona': 'PERSONAL DE CONSOLA'
        })

    reporte_rows = _build_reporte_asistencia_data(fecha=fecha_obj.isoformat(), turno=turno_val)
    asig_ids = [r.get('asignacion_id') for r in reporte_rows if r.get('asignacion_id')]
    asig_map = {}
    if asig_ids:
        asig_qs = Asignacion.objects.select_related('instalacion').filter(id__in=asig_ids)
        asig_map = {a.id: a for a in asig_qs}

    for row in reporte_rows:
        asig_id = row.get('asignacion_id')
        if not asig_id:
            continue
        cons = consolidado_map.get((TIPO_GUARDIA, asig_id))
        asig = asig_map.get(asig_id)
        proyecto = getattr(asig.instalacion, 'nombre', '') if asig and asig.instalacion else ''
        nombre_apellidos = (row.get('nombre_apellidos') or '').strip()
        data.append({
            'consolidado_id': cons.id if cons else None,
            'fecha': fecha_obj.isoformat(),
            'turno': turno_val or '',
            'tipo': TIPO_GUARDIA,
            'referencia_id': asig_id,
            'nominativo': row.get('codigo') or '',
            'proyecto': proyecto,
            'apellidos': nombre_apellidos,
            'nombres': '',
            'estado': row.get('estado') or '',
            'observacion': cons.observacion if cons else '',
            'zona': (row.get('zona_titulo') or 'SIN ZONA').strip(),
            'provincia': (row.get('provincia') or 'SIN PROVINCIA').strip()
        })

    return data


def _group_guardias_por_zona(data):
    guardias = [d for d in data if d.get('tipo') == TIPO_GUARDIA]
    zonas = {}
    for item in guardias:
        zona = item.get('zona') or 'SIN ZONA'
        if zona not in zonas:
            zonas[zona] = []
        zonas[zona].append(item)
    ordered_zonas = sorted(zonas.keys())
    return [(zona, zonas[zona]) for zona in ordered_zonas]


def _serialize_item(item: Consolidado):
    return {
        'id': item.id,
        'fecha': item.fecha.isoformat() if item.fecha else None,
        'turno': item.turno,
        'tipo': item.tipo,
        'referencia_id': item.referencia_id,
        'observacion': item.observacion or ''
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_consolidado(request):
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    tipo = request.GET.get('tipo')
    referencia_id = request.GET.get('referencia_id')

    qs = Consolidado.objects.all()
    if fecha:
        fecha_obj = parse_date(fecha)
        if fecha_obj:
            qs = qs.filter(fecha=fecha_obj)
    if turno:
        qs = qs.filter(turno=turno)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if referencia_id:
        try:
            ref_id = int(referencia_id)
            qs = qs.filter(referencia_id=ref_id)
        except (TypeError, ValueError):
            pass

    data = [_serialize_item(item) for item in qs.order_by('fecha', 'turno', 'tipo', 'referencia_id')]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_consolidado_armado(request):
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    data = _build_consolidado_data(fecha, turno)
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_consolidado(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    fecha = parse_date(data.get('fecha')) if data.get('fecha') else None
    turno = data.get('turno')
    tipo = data.get('tipo')
    referencia_id = data.get('referencia_id')
    observacion = (data.get('observacion') or '').strip() or None

    if not fecha or not turno or not tipo or referencia_id in [None, '']:
        return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

    if turno not in ALLOWED_TURNOS:
        return JsonResponse({'error': 'Turno invalido'}, status=400)

    if tipo not in ALLOWED_TIPOS:
        return JsonResponse({'error': 'Tipo invalido'}, status=400)

    try:
        referencia_id = int(referencia_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'referencia_id invalido'}, status=400)

    item = Consolidado.objects.create(
        fecha=fecha,
        turno=turno,
        tipo=tipo,
        referencia_id=referencia_id,
        observacion=observacion
    )

    return JsonResponse(_serialize_item(item), status=201)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_consolidado(request, id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    item = Consolidado.objects.filter(id=id).first()
    if not item:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    if 'fecha' in data:
        fecha = parse_date(data.get('fecha')) if data.get('fecha') else None
        if fecha:
            item.fecha = fecha

    if 'turno' in data:
        turno = data.get('turno')
        if turno in ALLOWED_TURNOS:
            item.turno = turno

    if 'tipo' in data:
        tipo = data.get('tipo')
        if tipo in ALLOWED_TIPOS:
            item.tipo = tipo

    if 'referencia_id' in data:
        try:
            item.referencia_id = int(data.get('referencia_id'))
        except (TypeError, ValueError):
            pass

    if 'observacion' in data:
        item.observacion = (data.get('observacion') or '').strip() or None

    item.save()
    return JsonResponse(_serialize_item(item))


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_consolidado(request, id):
    item = Consolidado.objects.filter(id=id).first()
    if not item:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    item.delete()
    return JsonResponse({'message': 'Registro eliminado'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_consolidado_excel(request):
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    data = _build_consolidado_data(fecha, turno)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Consolidado'

    fecha_label = _parse_fecha(fecha).strftime('%d/%m/%Y')
    turno_label = (turno or 'TODOS').upper()
    operador = ''
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        operador = f"{user.first_name} {user.last_name}".strip() or user.get_username()

    ws['A1'] = f"FECHA: {fecha_label}"
    ws['C1'] = f"TURNO: {turno_label}"
    ws['E1'] = f"REPORTA: {operador}"

    headers = ['NOMINATIVO', 'PROYECTO', 'APELLIDOS Y NOMBRE', 'ESTADO', 'OBSERVACIONES']
    header_row = 3

    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.value = header
        cell.border = border
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_idx = header_row + 1

    consola_rows = [d for d in data if d.get('tipo') == TIPO_CONSOLA]
    if consola_rows:
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=5)
        cell = ws.cell(row=row_idx, column=1)
        cell.value = 'PERSONAL DE CONSOLA Y OFICINAS'
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        for col in range(1, 6):
            c = ws.cell(row=row_idx, column=col)
            c.border = border
        row_idx += 1

        for item in consola_rows:
            nombre = f"{item.get('apellidos', '')} {item.get('nombres', '')}".strip()
            values = [
                item.get('nominativo', ''),
                item.get('proyecto', ''),
                nombre,
                item.get('estado', ''),
                item.get('observacion', ''),
            ]
            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = value
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')
            row_idx += 1

    for zona, items in _group_guardias_por_zona(data):
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=5)
        cell = ws.cell(row=row_idx, column=1)
        cell.value = str(zona).upper()
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        for col in range(1, 6):
            c = ws.cell(row=row_idx, column=col)
            c.border = border
        row_idx += 1

        for item in items:
            nombre = f"{item.get('apellidos', '')} {item.get('nombres', '')}".strip()
            values = [
                item.get('nominativo', ''),
                item.get('proyecto', ''),
                nombre,
                item.get('estado', ''),
                item.get('observacion', ''),
            ]
            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = value
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')
            row_idx += 1

    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 36
    ws.column_dimensions['C'].width = 38
    ws.column_dimensions['D'].width = 16
    ws.column_dimensions['E'].width = 40

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="consolidado.xlsx"'
    wb.save(response)
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_consolidado_pdf(request):
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    data = _build_consolidado_data(fecha, turno)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="consolidado.pdf"'

    p = canvas.Canvas(response, pagesize=landscape(letter))
    width, height = landscape(letter)
    x_margin = 0.5 * inch
    y_margin = 0.5 * inch

    fecha_label = _parse_fecha(fecha).strftime('%d/%m/%Y')
    turno_label = (turno or 'TODOS').upper()
    operador = ''
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        operador = f"{user.first_name} {user.last_name}".strip() or user.get_username()

    p.setFont('Helvetica-Bold', 11)
    p.drawString(x_margin, height - y_margin, f"FECHA: {fecha_label}")
    p.drawString(x_margin + 3.5 * inch, height - y_margin, f"TURNO: {turno_label}")
    p.drawRightString(width - x_margin, height - y_margin, f"REPORTA: {operador}")

    headers = ['NOMINATIVO', 'PROYECTO', 'APELLIDOS Y NOMBRE', 'ESTADO', 'OBSERVACIONES']
    col_widths = [1.2, 2.4, 2.6, 1.2, 2.6]
    col_widths = [w * inch for w in col_widths]

    y = height - y_margin - 0.4 * inch
    p.setFont('Helvetica-Bold', 8)
    x = x_margin
    for i, header in enumerate(headers):
        p.drawString(x + 2, y, header)
        x += col_widths[i]

    y -= 0.2 * inch
    p.setFont('Helvetica', 7)

    def ensure_space(y_cursor):
        if y_cursor < y_margin + 0.4 * inch:
            p.showPage()
            p.setFont('Helvetica-Bold', 8)
            x = x_margin
            for i, header in enumerate(headers):
                p.drawString(x + 2, height - y_margin, header)
                x += col_widths[i]
            return height - y_margin - 0.25 * inch
        return y_cursor

    def draw_section(label, y_cursor, font_size=8):
        y_cursor = ensure_space(y_cursor)
        p.setFont('Helvetica-Bold', font_size)
        p.setFillColor(colors.black)
        p.drawString(x_margin + 2, y_cursor, label)
        p.setFont('Helvetica', 7)
        return y_cursor - 0.2 * inch

    consola_rows = [d for d in data if d.get('tipo') == TIPO_CONSOLA]
    if consola_rows:
        y = draw_section('PERSONAL DE CONSOLA Y OFICINAS', y)
        for item in consola_rows:
            y = ensure_space(y)
            nombre = f"{item.get('apellidos', '')} {item.get('nombres', '')}".strip()
            row_vals = [
                item.get('nominativo', ''),
                item.get('proyecto', ''),
                nombre,
                item.get('estado', ''),
                item.get('observacion', ''),
            ]
            x = x_margin
            for i, val in enumerate(row_vals):
                text = str(val or '')
                max_width = col_widths[i] - 6
                while pdfmetrics.stringWidth(text, 'Helvetica', 7) > max_width and len(text) > 0:
                    text = text[:-1]
                p.drawString(x + 2, y, text)
                x += col_widths[i]
            y -= 0.18 * inch

    for zona, items in _group_guardias_por_zona(data):
        y = draw_section(str(zona).upper(), y)
        for item in items:
            y = ensure_space(y)
            nombre = f"{item.get('apellidos', '')} {item.get('nombres', '')}".strip()
            row_vals = [
                item.get('nominativo', ''),
                item.get('proyecto', ''),
                nombre,
                item.get('estado', ''),
                item.get('observacion', ''),
            ]
            x = x_margin
            for i, val in enumerate(row_vals):
                text = str(val or '')
                max_width = col_widths[i] - 6
                while pdfmetrics.stringWidth(text, 'Helvetica', 7) > max_width and len(text) > 0:
                    text = text[:-1]
                p.drawString(x + 2, y, text)
                x += col_widths[i]
            y -= 0.18 * inch

    p.showPage()
    p.save()
    return response
