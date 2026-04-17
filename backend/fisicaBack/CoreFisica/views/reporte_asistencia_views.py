from django.http import JsonResponse
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
import datetime
from pathlib import Path
from types import SimpleNamespace
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona, ReporteAsistencia, ReporteAsistenciaHistorial, AsignacionSemanal
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

# Funciones auxiliares para el reporte de asistencia
def _parse_fecha_reporte(fecha_param):
    if fecha_param:
        try:
            return datetime.date.fromisoformat(str(fecha_param))
        except ValueError:
            pass
    return timezone.localdate()

# Función para construir el nombre del operador de consola a partir del request. Si el usuario no está autenticado, se devuelve una cadena vacía. Si el usuario tiene un nombre completo (first_name + last_name), se devuelve ese nombre; de lo contrario, se devuelve el nombre de usuario. Esto se utiliza para mostrar quién generó el reporte en la sección de operador de consola del encabezado del reporte.
def _build_operador_consola(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return ''
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.get_username()

# Función para formatear la fecha del reporte en español, incluyendo el día de la semana. Se utiliza la lista DIAS_SEMANA_ES para obtener el nombre del día correspondiente al número de día de la semana que devuelve fecha_obj.weekday(). Luego se formatea la fecha en el formato "DÍA DD/MM/YYYY" para mostrarlo en el encabezado del reporte.
def _format_fecha_reporte_es(fecha_obj):
    dia = DIAS_SEMANA_ES[fecha_obj.weekday()]
    return f"{dia} {fecha_obj.strftime('%d/%m/%Y')}"

# Función para encontrar la ruta del logo que se incluirá en el reporte. Se buscan varias rutas relativas comunes dentro del proyecto, partiendo desde diferentes posibles raíces (como el directorio del archivo actual o el directorio de trabajo). Si se encuentra un archivo de imagen válido en alguna de las rutas, se devuelve su ruta; de lo contrario, se devuelve None. Esto permite incluir un logo personalizado en el reporte si está disponible, mejorando la presentación visual del mismo.
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

# Función para construir el contexto del encabezado del reporte de asistencia. Toma el request, la fecha y el turno como parámetros. La función formatea la fecha utilizando _format_fecha_reporte_es, determina el turno (Diurno, Nocturno o TODOS) y obtiene el nombre del operador de consola a partir del request. También busca la ruta del logo para incluirlo en el contexto. El resultado es un diccionario con toda la información necesaria para renderizar el encabezado del reporte de asistencia de manera consistente y profesional.
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

# Funciones auxiliares para formatear el reporte de asistencia, como dibujar el encabezado en Excel o PDF, ajustar el texto para que quepa en las celdas, normalizar colores, construir resúmenes de asistencia por zona, etc. Estas funciones ayudan a mantener el código organizado y reutilizable al generar los reportes de asistencia en diferentes formatos.
def _draw_excel_header(ws, ctx, border):
    # Se definen las celdas que se van a fusionar para crear el diseño del encabezado del reporte en Excel. Esto incluye fusionar las celdas A1:B2 para el logo, C1:F2 para el título, A4:D4 para la fecha, E4:F4 para el turno y G4:H4 para el operador de consola. Luego se aplica un borde a todas las celdas del área del encabezado y se centra el texto tanto horizontal como verticalmente. Finalmente, se asignan los valores correspondientes al título, versión, fecha de aprobación, fecha del reporte, turno y operador de consola en las celdas fusionadas, aplicando formato de fuente y ajustando la altura de las filas para mejorar la presentación visual del encabezado.
    ws.merge_cells('A1:B2')
    ws.merge_cells('C1:F2')
    ws.merge_cells('A4:D4')
    ws.merge_cells('E4:F4')
    ws.merge_cells('G4:H4')

    # el for iterando sobre las filas 1 a 4 y columnas 1 a 8 para aplicar el borde y la alineación a todas las celdas del área del encabezado, asegurando que el diseño sea consistente y profesional. Esto incluye las celdas fusionadas y las celdas individuales dentro de esa área.
    for row in range(1, 5):
        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # se asigna el titulo del reporte a la celda C1, aplicando formato de fuente en negrita y tamaño 14 para destacarlo. Luego se asignan los valores de versión y fecha de aprobación en las celdas G1, H1, G2 y H2 respectivamente, aplicando formato de fuente en negrita y tamaño 10 para diferenciarlos del título. Finalmente, se asignan los valores de fecha del reporte, turno y operador de consola en las celdas A4, E4 y G4 respectivamente, aplicando formato de fuente en negrita y tamaño 11 para resaltar esta información clave en el encabezado del reporte.
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

    # ws.row_dimensions se utiliza para ajustar la altura de las filas del encabezado en el archivo Excel. Esto es importante para asegurarse de que el contenido del encabezado, como el título, la versión, la fecha de aprobación y la información del operador de consola, se muestre de manera clara y legible, especialmente si el texto es largo o si se incluye un logo que requiere más espacio vertical. En este caso, se asignan alturas específicas a las filas 1, 2, 3 y 4 para mejorar la presentación visual del encabezado del reporte.
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

# Funcion para dibujar el encabezado del reporte de asistencia en formato PDF utilizando la biblioteca ReportLab. Se define el diseño del encabezado, incluyendo la posición y tamaño de las secciones para el logo, título, versión, fecha de aprobación, fecha del reporte, turno y operador de consola. Se dibujan rectángulos y líneas para estructurar visualmente el encabezado, se incluye el logo si está disponible y se asignan los valores correspondientes a cada sección con formato de fuente adecuado para resaltar la información clave del reporte.
def _draw_pdf_header(p, width, height, x_margin, y_margin, ctx):

    # table_w calcula el ancho disponible para el contenido del encabezado restando los márgenes izquierdo y derecho del ancho total de la página. top calcula la posición vertical inicial para dibujar el encabezado, partiendo desde la parte superior de la página y restando el margen superior. Estos cálculos son esenciales para posicionar correctamente los elementos del encabezado dentro de los límites definidos por los márgenes, asegurando que el diseño sea consistente y profesional en el formato PDF.
    table_w = width - (2 * x_margin)
    
    # top calcula la posición vertical inicial para dibujar el encabezado, partiendo desde la parte superior de la página y restando el margen superior.
    top = height - y_margin
    # top_h define la altura del área del encabezado principal, mientras que info_h define la altura del área de información adicional.
    top_h = 0.95 * inch
    # info_h define la altura del área de información adicional en el encabezado.
    info_h = 0.32 * inch
    #logo_w define el ancho reservado para el logo dentro del encabezado, mientras que title_w define el ancho reservado para el título del reporte. Estos valores son importantes para estructurar visualmente el encabezado y asegurar que cada elemento tenga suficiente espacio para mostrarse de manera clara y legible.
    logo_w = 1.8 * inch
    # title_w define el ancho reservado para el título del reporte dentro del encabezado.
    title_w = 4.8 * inch
    # x_logo, x_title y x_meta definen las posiciones horizontales de inicio para el logo, el título y la sección de metadatos respectivamente.
    x_logo = x_margin
    # x_title define la posición horizontal de inicio para el título del reporte.
    x_title = x_logo + logo_w
    # x_meta define la posición horizontal de inicio para la sección de metadatos.
    x_meta = x_title + title_w

    # se dibujan rectángulos y líneas para estructurar visualmente el encabezado, se incluye el logo si está disponible y se asignan los valores correspondientes a cada sección con formato de fuente adecuado para resaltar la información clave del reporte.
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

# Función para dibujar los encabezados de la tabla en el reporte de asistencia en formato PDF. Toma como parámetros el objeto canvas, los márgenes, la posición vertical inicial, los encabezados de las columnas y los anchos de las columnas. La función establece la fuente en negrita y tamaño 8 para los encabezados, luego itera sobre cada encabezado y lo dibuja centrado dentro de su respectiva columna utilizando el ancho definido en col_widths. Finalmente, devuelve la nueva posición vertical después de dibujar los encabezados, ajustada para dejar espacio entre el encabezado y las filas de datos que se dibujarán a continuación.
def _draw_pdf_table_headers(p, x_margin, y, headers, col_widths):
    p.setFont('Helvetica-Bold', 8)
    x = x_margin
    for i, header in enumerate(headers):
        header_w = pdfmetrics.stringWidth(header, 'Helvetica-Bold', 8)
        p.drawString(x + max((col_widths[i] - header_w) / 2, 0), y, header)
        x += col_widths[i]
    return y - 0.25 * inch

#
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

# Función para normalizar un valor de color hexadecimal. Toma un valor de color como entrada, lo convierte a una cadena y lo limpia de espacios. Si el valor está vacío, se devuelve None. Si el valor comienza con '#', se elimina el símbolo. Luego se verifica que la longitud del valor sea exactamente 6 caracteres y que todos los caracteres sean válidos en un código hexadecimal (0-9, A-F). Si el valor es válido, se devuelve en mayúsculas; de lo contrario, se devuelve None. Esta función es útil para asegurar que los valores de color utilizados en el reporte sean consistentes y válidos.
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

# Funcion para determinar si un item de asistencia se considera como "falto". Un item se considera "falto" si tiene un reemplazo asignado, ya sea por su ID o por su texto (que no debe ser vacío ni un guion). Esta función es utilizada para calcular el número de asistencias y faltas en el reporte, ya que un item con reemplazo indica que la persona no asistió a su asignación original.    
def _is_falto(item):
    reemplazo_id = item.get('reemplazo_id')
    reemplazo_txt = str(item.get('reemplazo') or '').strip()
    return (reemplazo_id is not None) or (reemplazo_txt not in ['', '-'])

# Funcion para generar una clave de ordenamiento para las zonas en el reporte de asistencia. Toma el título de la zona como entrada, lo convierte a minúsculas y lo limpia de espacios. Si el título coincide con "zona 1", "zona 2" o "zona 3", se asigna un valor numérico específico (0, 1 o 2 respectivamente) para asegurar que estas zonas se ordenen primero en el reporte. Para cualquier otro título de zona, se asigna un valor numérico alto (99) para que se ordenen después de las zonas principales, y se utiliza el título en minúsculas como criterio secundario de ordenamiento. Esto permite que las zonas se presenten en un orden lógico y consistente en el reporte.
def _zona_sort_key(zona_titulo):
    z = str(zona_titulo or '').strip().lower()
    if z == 'zona 1':
        return (0, z)
    if z == 'zona 2':
        return (1, z)
    if z == 'zona 3':
        return (2, z)
    return (99, z)

# Funcion para normalizar el titulo de una zona en el reporte de asistencia. Toma el titulo de la zona como entrada, lo convierte a una cadena, lo limpia de espacios y lo convierte a minúsculas. Si el título coincide con "zona 1", "zona 2" o "zona 3", se devuelve el título normalizado con la primera letra en mayúscula (por ejemplo, "Zona 1"). Para cualquier otro título de zona, se devuelve el título original limpio de espacios. Esta función es útil para asegurar que los títulos de las zonas se presenten de manera consistente en el reporte, especialmente si los datos de entrada pueden variar en formato o estilo.
def _normalize_zona_label(zona_titulo):
    z = str(zona_titulo or '').strip().lower()
    if z == 'zona 1':
        return 'Zona 1'
    if z == 'zona 2':
        return 'Zona 2'
    if z == 'zona 3':
        return 'Zona 3'
    return str(zona_titulo or '').strip()

#Funcion para formatear el titulo de una zona en el reporte de asistencia. Toma el título de la zona como entrada, lo normaliza utilizando _normalize_zona_label y luego verifica si el título ya comienza con "Zona". Si es así, se devuelve el título tal cual; de lo contrario, se agrega "Zona" al principio del título normalizado. Si el título está vacío después de la normalización, se devuelve simplemente "Zona". Esta función asegura que los títulos de las zonas en el reporte tengan un formato consistente y claro para los lectores.
def _format_zona_label(zona_titulo):
    label = _normalize_zona_label(zona_titulo)
    if label.lower().startswith('zona '):
        return label
    return f"Zona {label}" if label else 'Zona'

# Funcion para construir un resumen de asistencia a partir de los datos del reporte. Toma una lista de items de asistencia como entrada, filtra aquellos que tienen una asignación válida (es decir, que tienen un 'asignacion_id'), y luego cuenta cuántos de esos items se consideran "faltos" utilizando la función _is_falto. El número de asistencias se calcula restando el número de faltos del total de items evaluables, asegurándose de que el resultado no sea negativo. La función devuelve una tupla con el número total de asistencias y faltos, que se utiliza para mostrar un resumen general de la asistencia en el reporte.
def _build_resumen_asistencia(data):
    evaluables = [item for item in data if item.get('asignacion_id')]
    faltos = sum(1 for item in evaluables if _is_falto(item))
    asistencias = max(len(evaluables) - faltos, 0)
    return asistencias, faltos

# Funcion para construir un resumen de asistencia por zona a partir de los datos del reporte. Toma una lista de items de asistencia como entrada, filtra aquellos que tienen una asignación válida, y luego agrupa los items por zona utilizando un diccionario. Para cada zona, se cuenta el número total de items y el número de faltos utilizando la función _is_falto. Luego se construye una lista de resúmenes por zona, ordenada por el título de la zona utilizando la función _zona_sort_key para asegurar un orden lógico (por ejemplo, "Zona 1" antes que "Zona 2"). Cada resumen incluye el nombre de la zona, el total de items, el número de asistencias (calculado restando los faltos del total) y el número de faltas. Esta función permite mostrar un desglose detallado de la asistencia por zona en el reporte.
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

# Funcion para agrupar los datos del reporte de asistencia por zona y provincia. Toma una lista de items de asistencia como entrada, y para cada item con una asignación válida, extrae el título de la zona y el nombre de la provincia asociados a esa asignación. Luego agrupa los items en un diccionario anidado donde la primera clave es el título de la zona y la segunda clave es el nombre de la provincia. Cada grupo contiene una lista de items que pertenecen a esa combinación específica de zona y provincia. Finalmente, se construye una lista ordenada de zonas, donde cada zona contiene una lista ordenada de provincias, y cada provincia contiene su lista correspondiente de items. Esta función permite organizar los datos del reporte de asistencia de manera estructurada para facilitar su presentación y análisis por zona y provincia.
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

# Funcion para escribir el resumen de asistencia general en el reporte de asistencia en formato Excel. Toma como parámetros la hoja de cálculo, el índice de fila donde se debe escribir el resumen, el número total de asistencias, el número total de faltas y el estilo de borde a aplicar. La función fusiona las celdas correspondientes para crear dos áreas: una para mostrar el número de asistencias y otra para mostrar el número de faltas. Luego asigna los valores de asistencias y faltas a las celdas fusionadas, aplicando formato de fuente en negrita, color y alineación para resaltar esta información clave en el reporte. Finalmente, se aplica el borde a todas las celdas del área del resumen y se ajusta
def _write_excel_resumen(ws, row_idx, asistencias, faltos, border):
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
    ws.merge_cells(start_row=row_idx, start_column=5, end_row=row_idx, end_column=8)

    left_cell = ws.cell(row=row_idx, column=1)
    left_cell.value = f"{asistencias}\nASISTENCIAS"
    left_cell.font = Font(bold=True, color='9C0006', size=12)
    left_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_cell.fill = PatternFill(start_color='E6B8BE', end_color='E6B8BE', fill_type='solid')

    right_cell = ws.cell(row=row_idx, column=5)
    right_cell.value = f"{faltos}\nFALTOS"
    right_cell.font = Font(bold=True, color='000000', size=12)
    right_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for col_idx in range(1, 9):
        ws.cell(row=row_idx, column=col_idx).border = border
    ws.row_dimensions[row_idx].height = 38
    return row_idx

# Funcion para escribir el resumen de asistencia por zona en el reporte de asistencia en formato Excel. Toma como parámetros la hoja de cálculo, el índice de fila donde se debe escribir el resumen, una lista de resúmenes por zona (cada uno con el nombre de la zona, el total de items, el número de asistencias y el número de faltas) y el estilo de borde a aplicar. La función itera sobre cada resumen por zona, fusiona las celdas correspondientes para crear áreas para cada zona, asigna los valores de asistencias y faltas a las celdas fusionadas con formato de fuente en negrita, color y alineación para resaltar esta información clave en el reporte. Finalmente, se aplica el borde a todas las celdas del área del resumen por zona y se ajusta la altura de las filas para mejorar la presentación visual del resumen.
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


# Función principal para construir los datos del reporte de asistencia. Toma varios parámetros de filtro como fecha, cliente_id, turno y una opción para excluir asignaciones de sacafranco. La función consulta la base de datos para obtener las asignaciones activas y sus reportes de asistencia relacionados, aplicando los filtros correspondientes. Luego construye un diccionario de overrides para manejar cambios en los reportes de asistencia, y finalmente itera sobre las asignaciones para construir una lista de datos que incluye información relevante como el cliente, la instalación, el puesto, el horario, la persona asignada, la zona y cualquier reemplazo asociado. Esta función es esencial para preparar los datos que se mostrarán en el reporte de asistencia en diferentes formatos (Excel, PDF) y asegurar que se presenten de manera precisa y completa.
def _build_reporte_asistencia_data(fecha=None, cliente_id=None, turno=None, exclude_sacafranco=False):
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
    if fecha_obj:
        reporte_qs = reporte_qs.filter(fecha_reporte=fecha_obj)

    overrides = {}
    if fecha_obj:
        hist_qs = ReporteAsistenciaHistorial.objects.select_related('usuario', 'reemplazo')
        hist_qs = hist_qs.filter(fecha_reporte=fecha_obj).order_by('asignacion_id', '-creado_en')
        for h in hist_qs:
            if h.asignacion_id in overrides:
                continue
            overrides[h.asignacion_id] = SimpleNamespace(
                codigo=h.codigo,
                estado=h.estado,
                descripcion=h.descripcion,
                reemplazo=h.reemplazo,
                modificado_por=h.usuario,
                modificado_en=h.creado_en,
                row_color=h.row_color
            )

    for r in reporte_qs:
        if r.asignacion_id not in overrides:
            overrides[r.asignacion_id] = r

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
        asig_qs = asig_qs.filter(
            Q(puesto__horarios__turno=turno) | Q(puesto__horarios__turno='Ambos')
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

    # se construye una lista de datos que incluye información relevante como el cliente, la instalación, el puesto, el horario, la persona asignada, la zona y cualquier reemplazo asociado. Esta función es esencial para preparar los datos que se mostrarán en el reporte de asistencia en diferentes formatos (Excel, PDF) y asegurar que se presenten de manera precisa y completa.
    data = []
    # Se utiliza un conjunto para rastrear las personas que tienen asignaciones, lo que puede ser útil para filtrar o analizar los datos posteriormente, por ejemplo, para identificar personas sin asignaciones o para calcular estadísticas relacionadas con la asistencia.
    personas_con_asignacion = set()

    # Se itera sobre las asignaciones obtenidas de la base de datos, ordenadas por mes, fecha y ID. Para cada asignación, se extrae la información relevante como el cliente, la instalación, el puesto, el horario, la persona asignada y cualquier override relacionado con esa asignación. Luego se construye un diccionario con esta información y se agrega a la lista de datos que se utilizará para generar el reporte de asistencia. Este proceso asegura que cada fila del reporte contenga toda la información necesaria para mostrar un panorama completo de las asignaciones y su estado en la fecha consultada.
    for asig in asig_qs.order_by('mes', 'fecha', 'id'):
        p = asig.persona
        personas_con_asignacion.add(p.id)
        override = overrides.get(asig.id)

        # Se utiliza getattr para obtener el nombre comercial del cliente, asegurando que siempre se muestre alguna información relevante sobre el cliente en el reporte de asistencia.
        cliente_nombre = getattr(asig.cliente, 'nombre_comercial', '') if asig else ''

        # se utiliza getattr para obtener el nombre del puesto, y si no está disponible, se intenta obtener el tipo del puesto. Esto permite manejar casos donde el nombre del puesto no esté definido pero el tipo sí lo esté, asegurando que siempre se muestre alguna información relevante sobre el puesto en el reporte de asistencia.
        puesto_nombre = getattr(asig.puesto, 'nombre', '') if asig else ''
        if not puesto_nombre and asig:
            puesto_nombre = getattr(asig.puesto, 'tipo', '')
        horario_str = ''
        if asig and asig.horario:
            horario_str = f"{asig.horario.hora_ingreso.strftime('%H:%M')} - {asig.horario.hora_salida.strftime('%H:%M')}"
        nombre_apellidos = f"{p.nombres} {p.apellidos}".strip()
        zona_titulo = ''
        provincia_nombre = ''
        if asig and asig.instalacion:
            zona_obj = asig.instalacion.zonas.order_by('id').first()
            if zona_obj:
                zona_titulo = zona_obj.titulo
        if asig and asig.instalacion and asig.instalacion.canton and asig.instalacion.canton.provincia:
            provincia_nombre = asig.instalacion.canton.provincia.nombre
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
        
        # Se utiliza getattr para obtener el código de la instalación, asegurando que siempre se muestre alguna información relevante sobre la instalación en el reporte de asistencia.
        codigo_instalacion = getattr(asig.instalacion, 'codigo', '') if asig and asig.instalacion else ''
        data.append({
            'asignacion_id': asig.id,
            'codigo': override.codigo if (override and override.codigo) else (codigo_instalacion or ''),
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
            'zona_titulo': zona_titulo,
            'provincia': provincia_nombre,
        })
    return data

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_asistencia(request):
    # si el ususario no tiene permiso para ver el reporte de aistencia, se devuelve una respuesta JSON con un mensaje de error y un código de estado 403 (Forbidden). Esto asegura que solo los usuarios autorizados puedan acceder a la información del reporte de asistencia, protegiendo así los datos sensibles y manteniendo la seguridad de la aplicación.
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    # se definen los parámetros de filtro para la consulta del reporte de asistencia, incluyendo la fecha, el ID del cliente, el turno y una opción para excluir asignaciones de sacafranco. Luego se llama a la función _build_reporte_asistencia_data con estos parámetros para obtener los datos del reporte de asistencia, que se devuelven en formato JSON con un código de estado 200 (OK). Esto permite que los usuarios autorizados puedan consultar el reporte de asistencia con diferentes filtros para obtener la información específica que necesitan.
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    turno = request.GET.get('turno')
    exclude_sacafranco = str(request.GET.get('exclude_sacafranco', '')).strip() == '1'
    data = _build_reporte_asistencia_data(
        fecha=fecha,
        cliente_id=cliente_id,
        turno=turno,
        exclude_sacafranco=exclude_sacafranco
    )
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def insertar_reporte_asistencia(request, asignacion_id):
    # si el usuario no tiene permiso para modificar el reporte de asistencia, se devuelve una respuesta JSON con un mensaje de error y un código de estado 403 (Forbidden). Esto asegura que solo los usuarios autorizados puedan modificar la información del reporte de asistencia, protegiendo así los datos sensibles y manteniendo la seguridad de la aplicación.
    if not request.user.has_perm('CoreFisica.change_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    # se obtiene o crea un objeto ReporteAsistencia para la asignación especificada. Esto permite que se pueda insertar o actualizar la información del reporte de asistencia de manera eficiente.
    override, _ = ReporteAsistencia.objects.get_or_create(asignacion_id=asignacion_id)

    # se obtienen los datos de la asignacion relacionado con el reporte de asistencia utilizando select_related para optimizar la consulta. Si no se encuentra la asignacion, se devuelve una respuesta JSON con un mensaje de error y un código de estado 404 (Not Found). Esto asegura que el reporte de asistencia solo se pueda modificar para asignaciones válidas y existentes, manteniendo la integridad de los datos en la aplicación.
    asignacion = Asignacion.objects.select_related(
        'persona', 'cliente', 'instalacion', 'puesto', 'horario'
    ).filter(id=asignacion_id).first()
    if not asignacion:
        return JsonResponse({'error': 'Asignacion no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    # se actualizan los campos del reporte de asistencia con la información de la asignación y los datos enviados en la solicitud. Se utiliza getattr para obtener el código de la instalación, asegurando que siempre se muestre alguna información relevante sobre la instalación en el reporte de asistencia. Luego se resuelve el reemplazo a partir de los datos de la solicitud, y si se encuentra un error en este proceso, se devuelve la respuesta de error correspondiente. Finalmente, se guarda el reporte de asistencia actualizado en la base de datos.
    override.persona = asignacion.persona
    override.cliente = asignacion.cliente
    override.instalacion = asignacion.instalacion
    override.puesto = asignacion.puesto
    override.horario = asignacion.horario
    override.puesto_tipo = getattr(asignacion.puesto, 'tipo', None) if asignacion.puesto else None

    # Se utiliza getattr para obtener el código de la instalación, asegurando que siempre se muestre alguna información relevante sobre la instalación en el reporte de asistencia.
    override.codigo = getattr(asignacion.instalacion, 'codigo', None)

    # se iteran los campos 'estado', 'descripcion' y 'row_color' para actualizar el reporte de asistencia con los datos enviados en la solicitud. Si alguno de estos campos está presente en los datos de la solicitud, se actualiza el valor correspondiente en el objeto override. Esto permite que se puedan modificar estos campos de manera flexible según las necesidades del usuario.
    for field in ['estado', 'descripcion', 'row_color']:
        if field in request.data:
            val = request.data.get(field) or None
            setattr(override, field, val)

    # se resuelve el reemplazo a partir de los datos de la solicitud utilizando la función _resolver_reemplazo_desde_request. Si se encuentra un error en este proceso, se devuelve la respuesta de error correspondiente. Si el resultado del reemplazo no es 'no-enviado', se actualiza el campo de reemplazo en el objeto override. Esto permite que se pueda asignar o modificar el reemplazo asociado al reporte de asistencia de manera eficiente y con manejo adecuado de errores.
    reemplazo_result, err = _resolver_reemplazo_desde_request(request)
    if err:
        return err
    if reemplazo_result != 'no-enviado':
        override.reemplazo = reemplazo_result

    fecha_param = request.data.get('fecha')
    fecha_reporte = None
    if fecha_param:
        try:
            fecha_reporte = datetime.date.fromisoformat(str(fecha_param))
        except ValueError:
            fecha_reporte = None

    if request.user and request.user.is_authenticated:
        override.modificado_por = request.user
    override.fecha_reporte = fecha_reporte
    override.modificado_en = timezone.now()
    override.save()

    try:
        # se crea un registro en el historial de reportes de asistencia para mantener un seguimiento de los cambios realizados en el reporte de asistencia. Esto permite tener un historial completo de las modificaciones realizadas, incluyendo quién hizo el cambio, cuándo se hizo y qué cambios se realizaron, lo que es útil para auditorías y para entender la evolución de la asistencia a lo largo del tiempo.
        ReporteAsistenciaHistorial.objects.create(
            reporte=override,
            asignacion=asignacion,
            fecha_reporte=override.fecha_reporte,
            usuario=request.user if request.user and request.user.is_authenticated else None,
            codigo=override.codigo,
            estado=override.estado,
            reemplazo=override.reemplazo,
            descripcion=override.descripcion,
            row_color=override.row_color
        )
    except Exception:
        pass

    # se construye el nombre del ususario que modifico el reporte de aistencia utilizando el nombre y apellido del usuario, o su nombre de usuario si el nombre completo no está disponible. Esto permite mostrar información clara sobre quién realizó la última modificación en el reporte de asistencia, lo que es útil para seguimiento y auditoría.
    modificado_por_nombre = ''
    if override.modificado_por:
        full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
        modificado_por_nombre = full_name or override.modificado_por.get_username()

    reemplazo_nombre = ''
    if override.reemplazo:
        reemplazo_nombre = f"{override.reemplazo.nombres} {override.reemplazo.apellidos}".strip()

    # se retorna una respuesta json con la informacion de reporte de asistencia
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
def historial_reporte_asistencia(request, asignacion_id):
    # si el usuario no tiene permiso para ver el reporte de asistencia, se devuelve una respuesta JSON con un mensaje de error y un código de estado 403 (Forbidden). Esto asegura que solo los usuarios autorizados puedan acceder a la información del historial del reporte de asistencia, protegiendo así los datos sensibles y manteniendo la seguridad de la aplicación.
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    # se obtiene el parámetro de fecha para filtrar el historial del reporte de asistencia. Luego se consulta la base de datos para obtener los registros del historial relacionados con la asignación especificada, aplicando el filtro de fecha si se proporciona. Se construye una lista de datos con la información relevante de cada registro del historial, incluyendo la fecha del reporte, el usuario que realizó el cambio, el código, el estado, el reemplazo, la descripción, el color de fila y la fecha de creación. Finalmente, se devuelve esta información en formato JSON con un código de estado 200 (OK). Esto permite que los usuarios autorizados puedan consultar el historial de cambios realizados en el reporte de asistencia para una asignación específica.
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
    # se construye una lista de datos con la informacion relevante de cada registro del historial, incluyendo la fecha del reporte, el usuario que realizó el cambio, el código, el estado, el reemplazo, la descripción, el color de fila y la fecha de creación. Finalmente, se devuelve esta información en formato JSON con un código de estado 200 (OK). Esto permite que los usuarios autorizados puedan consultar el historial de cambios realizados en el reporte de asistencia para una asignación específica.
    data = []
    for h in qs:
        usuario_nombre = ''
        if h.usuario:
            full_name = f"{h.usuario.first_name} {h.usuario.last_name}".strip()
            usuario_nombre = full_name or h.usuario.get_username()
        reemplazo_nombre = ''
        if h.reemplazo:
            reemplazo_nombre = f"{h.reemplazo.nombres} {h.reemplazo.apellidos}".strip()
        # se agrega un diccionario con la información relevante de cada registro del historial a la lista de datos, incluyendo la fecha del reporte, el usuario que realizó el cambio, el código, el estado, el reemplazo, la descripción, el color de fila y la fecha de creación. Esto permite estructurar la información del historial de manera clara y accesible para su presentación en el reporte de asistencia.
        data.append({
            'fecha_reporte': h.fecha_reporte.isoformat() if h.fecha_reporte else None,
            'usuario': usuario_nombre,
            'codigo': h.codigo or '',
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
    # si el usuario no tiene permiso para ver el reporte de asistencia, se devuelve una respuesta JSON con un mensaje de error y un código de estado 403 (Forbidden). Esto asegura que solo los usuarios autorizados puedan acceder a la funcionalidad de exportar el reporte de asistencia en formato Excel, protegiendo así los datos sensibles y manteniendo la seguridad de la aplicación.
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    # se obtienen los parametros de filtro para la consulta del reporte de asistencia, incluyendo la fecha y el ID del cliente. Luego se definen los encabezados para el archivo Excel y se crean estilos de borde para las celdas. Se define una función interna render_sheet que se encarga de construir el contenido del archivo Excel, incluyendo la consulta de datos, la construcción del resumen de asistencia, la agrupación por zona y provincia, y el formato de las celdas. Finalmente, se llama a esta función para generar el archivo Excel con el reporte de asistencia filtrado según los parámetros proporcionados. Esto permite que los usuarios autorizados puedan exportar el reporte de asistencia en un formato Excel para su análisis o presentación.
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    headers = [
        'NOMINATIVO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO', 'DESCRIPCIÓN',
    ]
    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # funcion para construir el contenido del archivo Excel, incluyendo la consulta de datos, la construcción del resumen de asistencia, la agrupación por zona y provincia, y el formato de las celdas. Esta función se encarga de organizar los datos del reporte de asistencia de manera estructurada y visualmente clara en el archivo Excel, facilitando su análisis y presentación.
    def render_sheet(ws, turno_val):
        data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno_val)
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
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=8)
            zona_cell = ws.cell(row=current_row, column=1)
            zona_cell.value = _normalize_zona_label(zona_group['zona'])
            zona_cell.font = Font(bold=True, size=11)
            zona_cell.alignment = Alignment(horizontal='left', vertical='center')
            for col_idx in range(1, 9):
                ws.cell(row=current_row, column=col_idx).border = border
            ws.row_dimensions[current_row].height = 24
            current_row += 1

            zona_items = []
            for prov_group in zona_group['provincias']:
                # Fila de provincia
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=8)
                prov_cell = ws.cell(row=current_row, column=1)
                prov_cell.value = str(prov_group['provincia']).upper()
                prov_cell.font = Font(bold=True, size=10)
                prov_cell.alignment = Alignment(horizontal='left', vertical='center')
                for col_idx in range(1, 9):
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
                        item.get('estado', ''),
                        item.get('reemplazo', ''),
                        item.get('descripcion', ''),
                    ]
                    for col_idx, value in enumerate(row_vals, start=1):
                        cell = ws.cell(row=current_row, column=col_idx)
                        cell.value = value
                        cell.border = border
                        if row_fill:
                            cell.fill = row_fill
                        if col_idx == 8:
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
            6: 12,  # Estado
            7: 40,  # Reemplazo
            8: 28,  # Descripcion
        }
        for col_idx, width in column_widths.items():
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        # Resumen global removido; se deja solo el resumen por zona.
        current_row += 1
        for zona_label, zona_asistencias, zona_faltos in zona_resumen:
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=2)
            ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=5)
            ws.merge_cells(start_row=current_row, start_column=6, end_row=current_row, end_column=8)

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

            for col_idx in range(1, 9):
                ws.cell(row=current_row, column=col_idx).border = border
            current_row += 1

    # openpyxl se utiliza para crear un nuevo libro de trabajo de Excel y agregar hojas para los turnos diurno y nocturno, llamando a la función render_sheet para generar el contenido de cada hoja. Luego se configura la respuesta HTTP para descargar el archivo Excel generado, estableciendo el tipo de contenido y el encabezado de disposición de contenido para indicar que es un archivo adjunto con un nombre específico. Finalmente, se guarda el libro de trabajo en la respuesta, lo que permite que el usuario descargue el archivo Excel con el reporte de asistencia filtrado según los parámetros proporcionados.
    wb = openpyxl.Workbook()
    # wb.active se refiere a la hoja activa del libro de trabajo, que por defecto es la primera hoja creada. Se asigna esta hoja a la variable ws para poder trabajar con ella, y luego se establece el título de la hoja como 'DIURNO'. Esto permite organizar el contenido del reporte de asistencia en diferentes hojas según el turno, facilitando su análisis y presentación.
    ws = wb.active
    # ws.title se establece el título de la hoja activa como 'DIURNO', lo que indica que esta hoja contendrá el reporte de asistencia para el turno diurno. Esto ayuda a organizar el contenido del archivo Excel de manera clara y facilita la navegación para los usuarios que descarguen el reporte.
    ws.title = 'DIURNO'
    # se utiliza la función render_sheet para generar el contenido del reporte de asistencia en la hoja 'DIURNO', pasando la hoja de trabajo y el valor del turno como argumentos. Esto permite que se construya el reporte de asistencia específico para el turno diurno en la hoja correspondiente del archivo Excel.
    render_sheet(ws, 'Diurno')

    #ws_nocturno se crea una nueva hoja en el libro de trabajo para el turno nocturno, y se utiliza la función render_sheet para generar el contenido del reporte de asistencia en esta hoja, pasando la hoja de trabajo y el valor del turno como argumentos. Esto permite que se construya el reporte de asistencia específico para el turno nocturno en la hoja correspondiente del archivo Excel, organizando así la información de manera clara y accesible para los usuarios que descarguen el reporte.
    ws_nocturno = wb.create_sheet('NOCTURNO')
    render_sheet(ws_nocturno, 'Nocturno')

    # se configura la repuesta HTTP para descargar el archivo Excel generado, estableciendo el tipo de contenido como 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' y el encabezado de disposición de contenido para indicar que es un archivo adjunto con el nombre 'reporte_asistencia.xlsx'. Luego se guarda el libro de trabajo en la respuesta, lo que permite que el usuario descargue el archivo Excel con el reporte de asistencia filtrado según los parámetros proporcionados. Esto facilita a los usuarios autorizados la obtención del reporte de asistencia en un formato Excel para su análisis o presentación.
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # se establece el encabezado de disposicion de contenido para indicar que el archivo generado es un adjunto con el nombre 'reporte_asistencia.xlsx'. Esto asegura que cuando el usuario descargue el archivo, se le sugerirá este nombre para guardarlo en su dispositivo, facilitando la identificación del archivo como el reporte de asistencia.
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.xlsx"'
    # se guarda el libro de trabajo en la respuesta HTTP, lo que permite que el usuario descargue el archivo Excel con el reporte de asistencia filtrado según los parámetros proporcionados. Esto facilita a los usuarios autorizados la obtención del reporte de asistencia en un formato Excel para su análisis o presentación.
    wb.save(response)
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reporte_asistencia_pdf(request):
    # si el usuario no tiene permiso para el reporte de asistencia, se devuelve una respuesta JSON con un mensaje de error y un código de estado 403 (Forbidden). Esto asegura que solo los usuarios autorizados puedan acceder a la funcionalidad de exportar el reporte de asistencia en formato PDF, protegiendo así los datos sensibles y manteniendo la seguridad de la aplicación.
    if not request.user.has_perm('CoreFisica.view_reporteasistencia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    # se obtienen los parámetros de filtro para la consulta del reporte de asistencia, incluyendo la fecha, el ID del cliente y el turno. Luego se construyen los datos del reporte de asistencia utilizando la función _build_reporte_asistencia_data con estos parámetros. Se construye el contexto para el encabezado del PDF utilizando la función _build_header_context, y se obtiene el resumen de asistencias y faltas utilizando la función _build_resumen_asistencia. Los datos del reporte se agrupan por zona y provincia utilizando la función _group_reporte_por_zona_y_provincia. Finalmente, se genera un archivo PDF con el reporte de asistencia utilizando ReportLab, organizando la información de manera clara y estructurada para su presentación. Esto permite que los usuarios autorizados puedan exportar el reporte de asistencia en un formato PDF para su análisis o presentación.
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')
    turno = request.GET.get('turno')
    data = _build_reporte_asistencia_data(fecha=fecha, cliente_id=cliente_id, turno=turno)
    header_ctx = _build_header_context(request, fecha, turno)
    asistencias, faltos = _build_resumen_asistencia(data)
    grouped = _group_reporte_por_zona_y_provincia(data)
    # se inicializa una lista vacía llamada zona_resumen, que se utilizará para almacenar el resumen de asistencias y faltas por zona. Esta lista se llenará a medida que se procesen los datos agrupados por zona y provincia, permitiendo que se genere un resumen claro y organizado de la asistencia para cada zona en el reporte PDF.
    zona_resumen = []

    # se configura la respuesta HTTP para descargar el archivo PDF generado, estableciendo el tipo de contenido como 'application/pdf' y el encabezado de disposición de contenido para indicar que es un archivo adjunto con el nombre 'reporte_asistencia.pdf'. Luego se utiliza ReportLab para crear un lienzo PDF en la respuesta, organizando la información del reporte de asistencia de manera clara y estructurada para su presentación. Esto permite que los usuarios autorizados puedan exportar el reporte de asistencia en un formato PDF para su análisis o presentación.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.pdf"'
    # se utiliza ReportLab para crear un lienzo PDF en la respuesta, organizando la información del reporte de asistencia de manera clara y estructurada para su presentación. Esto permite que los usuarios autorizados puedan exportar el reporte de asistencia en un formato PDF para su análisis o presentación.
    p = canvas.Canvas(response, pagesize=landscape(letter))
    # se obtiene el ancho y alto de la página en orientación horizontal utilizando la función landscape de ReportLab, lo que permite configurar el diseño del contenido del PDF de manera adecuada para su presentación. Esto es importante para asegurar que la información del reporte de asistencia se muestre de manera clara y legible en el formato PDF generado.
    width, height = landscape(letter)
    # se define un margen horizontal y vertical de 0.5 pulgadas utilizando la unidad de medida inch de ReportLab, lo que permite establecer un espacio adecuado alrededor del contenido del PDF para mejorar su presentación y legibilidad. Esto ayuda a evitar que el contenido se vea demasiado apretado o desordenado en el formato PDF generado.    
    x_margin = 0.5 * inch
    y_margin = 0.5 * inch

    # se definen los encabezados(headers) para la tabla que se mostrará en el PDF, incluyendo 'NOMINATIVO', 'CLIENTE', 'PUESTO', 'HORARIO', 'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO' y 'DESCRIPCIÓN'. Estos encabezados representan las columnas de información que se incluirán en el reporte de asistencia, proporcionando una estructura clara para la presentación de los datos en el formato PDF generado. Esto facilita la comprensión y análisis de la información del reporte por parte de los usuarios que descarguen el archivo PDF.
    headers = [
        'NOMINATIVO', 'CLIENTE', 'PUESTO', 'HORARIO',
        'NOMBRE Y APELLIDOS', 'ESTADO', 'REEMPLAZO', 'DESCRIPCIÓN',
    ]
    # se definen los anchos de las columnas en pulgadas, lo que permite ajustar el diseño de la tabla en el PDF de manera precisa y consistente.
    col_widths = [0.8, 1.25, 1.2, 0.65, 1.95, 0.9, 1.9, 1.05]
    col_widths = [w * inch for w in col_widths]

    #Funcion para asegurar que haya suficiente espacio en la página para dibujar el contenido, y si no es así, se crea una nueva página y se redibuja el encabezado y los encabezados de la tabla. Esto garantiza que el contenido del reporte de asistencia se muestre de manera clara y legible en el formato PDF generado, evitando que se corte o se vea desordenado debido a la falta de espacio en la página.
    def ensure_space(y_cursor, needed_height):
        if y_cursor < y_margin + needed_height:
            p.showPage()
            page_width, page_height = landscape(letter)
            new_y = _draw_pdf_header(p, page_width, page_height, x_margin, y_margin, header_ctx)
            new_y = _draw_pdf_table_headers(p, x_margin, new_y, headers, col_widths)
            p.setFont('Helvetica', 6)
            return new_y
        return y_cursor

    #Funcion para dibujar una fila de grupo (zona o provincia) en el PDF, utilizando un tamaño de fuente específico y asegurando que haya suficiente espacio en la página antes de dibujar la fila. Esto permite organizar el contenido del reporte de asistencia en grupos claros y visualmente distintos, mejorando la legibilidad y presentación del PDF generado.
    def draw_group_row(y_cursor, text, font_size=7):
        y_cursor = ensure_space(y_cursor, 0.3 * inch)
        p.setFont('Helvetica-Bold', font_size)
        p.setFillColor(colors.black)
        p.drawString(x_margin + 6, y_cursor, text)
        p.setFont('Helvetica', 6)
        return y_cursor - 0.2 * inch

    # Funcion para dibujar el resumen de asistencias y faltas para una zona específica en el PDF, utilizando un diseño de cajas con colores y asegurando que haya suficiente espacio en la página antes de dibujar el resumen. Esto permite presentar de manera clara y visualmente atractiva el resumen de asistencia para cada zona en el reporte PDF generado, facilitando su análisis y comprensión por parte de los usuarios que descarguen el archivo.
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
                # se construye una lista de valores para la fila actual, obteniendo los datos del item y asegurándose de manejar valores nulos o vacíos de manera adecuada. Esto permite que se muestre información clara y consistente en cada fila del reporte PDF generado, mejorando su legibilidad y presentación. 
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

        zona_asistencias, zona_faltos = _build_resumen_asistencia(zona_items)
        zona_resumen.append((zona_group['zona'], zona_asistencias, zona_faltos))
        y = draw_resumen(y, zona_asistencias, zona_faltos)
    #si hay un resumen por zona, se dibuja al final del reporte PDF utilizando la función draw_resumen, asegurando que haya suficiente espacio en la página antes de dibujar el resumen. Esto permite que se presente de manera clara y visualmente atractiva el resumen de asistencia para cada zona al final del reporte PDF generado, facilitando su análisis y comprensión por parte de los usuarios que descarguen el archivo.
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
    # se llama a la funcion showPage para finalizar la página actual del PDF y preparar el lienzo para una nueva página si es necesario. Esto es importante para asegurar que el contenido del reporte de asistencia se organice correctamente en el formato PDF generado, permitiendo que se muestre de manera clara y legible incluso si el contenido excede el espacio disponible en una sola página.
    p.showPage()
    p.save()
    return response