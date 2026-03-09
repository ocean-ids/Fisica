from django.http import JsonResponse
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona, ReporteAsistencia
import openpyxl
from openpyxl.styles import Alignment, Border, Side
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch



def _build_reporte_asistencia_data(fecha=None, cliente_id=None):
    overrides = {
        r.asignacion_id: r
        for r in ReporteAsistencia.objects.select_related('asignacion', 'modificado_por')
    }

    asig_qs = Asignacion.objects.select_related(
        'cliente', 'instalacion', 'puesto', 'horario', 'persona'
    ).filter(persona__is_active=True)

    if fecha:
        
        asig_qs = asig_qs.filter(Q(fecha=fecha) | Q(fecha__isnull=True))
    if cliente_id:
        asig_qs = asig_qs.filter(cliente_id=cliente_id)

    
    asig_map = {}
    for a in asig_qs.order_by('id'):
        asig_map.setdefault(a.persona_id, a)

    data = []
    personas = Persona.objects.filter(is_active=True).order_by('apellidos', 'nombres')
    for p in personas:
        asig = asig_map.get(p.id)
        override = overrides.get(asig.id) if asig else None

        cliente_nombre = getattr(asig.cliente, 'nombre_comercial', '') if asig else ''
        
        puesto_nombre = getattr(asig.puesto, 'nombre', '') if asig else ''
        if not puesto_nombre and asig:
            puesto_nombre = getattr(asig.puesto, 'tipo', '')
        horario_str = ''
        if asig and asig.horario:
            horario_str = f"{asig.horario.hora_ingreso.strftime('%H:%M')} - {asig.horario.hora_salida.strftime('%H:%M')}"
        nombre_apellidos = f"{p.nombres} {p.apellidos}".strip()

        data.append({
            'asignacion_id': asig.id if asig else None,
            'codigo': override.codigo if (asig and override and override.codigo) else '',
            'cliente': cliente_nombre,
            'puesto': puesto_nombre,
            'horario': horario_str,
            'nombre_apellidos': nombre_apellidos,
            'estado': (override.estado or 'TURNO') if (asig and override) else ('TURNO' if asig else ''),
            'descripcion': (override.descripcion or '') if override else '',
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
    for field in ['codigo', 'estado', 'descripcion']:
        if field in request.data:
            val = request.data.get(field) or None
            setattr(override, field, val)
    if request.user and request.user.is_authenticated:
        override.modificado_por = request.user
    override.modificado_en = timezone.now()
    override.save()
    modificado_por_nombre = ''
    if override.modificado_por:
        full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
        modificado_por_nombre = full_name or override.modificado_por.get_username()
    return JsonResponse({
        'codigo': override.codigo or '',
        'estado': override.estado or 'TURNO',
        'descripcion': override.descripcion or '',
        'modificado_por': modificado_por_nombre,
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
        'Código', 'Cliente', 'Puesto', 'Horario',
        'Nombre y Apellidos', 'Estado', 'Descripción',
    ]
    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header
        cell.border = border

    for row_idx, item in enumerate(data, start=2):
        row_vals = [
            item.get('codigo', ''),
            item.get('cliente', ''),
            item.get('puesto', ''),
            item.get('horario', ''),
            item.get('nombre_apellidos', ''),
            item.get('estado', ''),
            item.get('descripcion', ''),
        ]
        for col_idx, value in enumerate(row_vals, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.border = border
            if col_idx in (1, 4, 6):
                cell.alignment = Alignment(horizontal='center')

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
        'Código', 'Cliente', 'Puesto', 'Horario',
        'Nombre y Apellidos', 'Estado', 'Descripción',
    ]
    col_widths = [0.9, 1.5, 1.5, 1.4, 2.0, 0.9, 3.0]
    col_widths = [w * inch for w in col_widths]

    p.setFont('Helvetica-Bold', 12)
    p.drawString(x_margin, y, 'Reporte de Asistencia')
    y -= 0.3 * inch

    p.setFont('Helvetica-Bold', 8)
    x = x_margin
    for i, header in enumerate(headers):
        p.drawString(x, y, header)
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
                p.drawString(x, y, header)
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
            (item.get('descripcion', '') or '')[:120],
        ]

        x = x_margin
        for i, value in enumerate(row_vals):
            text = str(value) if value is not None else ''
            p.drawString(x, y, text)
            x += col_widths[i]

        y -= 0.2 * inch

    p.showPage()
    p.save()
    return response