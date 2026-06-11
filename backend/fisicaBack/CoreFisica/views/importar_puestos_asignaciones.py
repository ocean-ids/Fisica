from datetime import date, datetime, time, timedelta
import logging
import re

from django.db import transaction
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from ..models import Cliente, Instalacion, Puesto, PuestoHorario, Persona, Horario, Asignacion, PatronAsignacion, AsignacionSemanal, ReporteAsistencia

logger = logging.getLogger(__name__)

HEADER_MAP = {
    'INSTALACION': 'instalacion',
    'INSTALACION ID': 'instalacion_id',
    'PUESTO': 'puesto',
    'PUESTO NOMBRE': 'puesto',
    'NOMBRE PUESTO': 'puesto',
    'TIPO PUESTO': 'puesto_tipo',
    'PUESTO TIPO': 'puesto_tipo',
    'CEDULA': 'cedula',
    'APELLIDOS': 'apellidos',
    'NOMBRES': 'nombres',
    'TIPO': 'tipo',
    'HORARIO INGRESO': 'hora_ingreso',
    'HORA INGRESO': 'hora_ingreso',
    'INGRESO': 'hora_ingreso',
    'HORARIO SALIDA': 'hora_salida',
    'HORA SALIDA': 'hora_salida',
    'SALIDA': 'hora_salida',
    'HORAS': 'horas',
    'TURNO': 'turno',
    'DIAS': 'dias',
    'DIAS TURNO': 'dias',
    'DIA': 'dias',
    'FECHA': 'fecha',
    'CLIENTE': 'cliente',
    'CLIENTE NOMBRE': 'cliente',
    'NOMBRE COMERCIAL': 'cliente',
    'CLIENTE RUC': 'cliente_ruc',
    'RUC': 'cliente_ruc',
    'CANTIDAD PUESTOS': 'cantidad_puestos',
    'CANTIDAD': 'cantidad_puestos',
    'PUESTO CANTIDAD': 'cantidad_puestos',
    'PATRON': 'patron',
    'PATRON CODIGO': 'patron',
    'CODIGO PATRON': 'patron',
    'PATRON ID': 'patron_id',
}

for day_num in range(1, 32):
    HEADER_MAP[str(day_num)] = f'day_{day_num}'


def normalize_header(value):
    if value is None:
        return ''
    import unicodedata
    text = str(value).strip().upper()
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    text = text.replace('_', ' ')
    text = ' '.join(text.split())
    return text


def norm(val):
    if val is None:
        return ''
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        return str(val)
    return re.sub(r'\s+', ' ', str(val)).strip()


def parse_excel_date(val):
    if not val:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, (int, float)):
        try:
            return from_excel(val).date()
        except Exception:
            return None
    if isinstance(val, str):
        raw = val.strip()
        if not raw:
            return None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def parse_excel_time(val):
    if not val:
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, datetime):
        return val.time()
    if isinstance(val, (int, float)):
        try:
            return from_excel(val).time()
        except Exception:
            return None
    if isinstance(val, str):
        raw = val.strip()
        if not raw:
            return None
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                return datetime.strptime(raw, fmt).time()
            except ValueError:
                continue
    return None


def normalize_cedula(value):
    if value is None:
        return ''
    raw = str(value).strip()
    compact = re.sub(r'[\s\-]', '', raw)
    if not compact:
        return ''
    if not re.match(r'^\d+$', compact):
        return None
    if len(compact) == 9:
        return f"0{compact}"
    return compact


def parse_turno(value):
    if not value:
        return 'Diurno'
    token = str(value).strip().upper()
    if token in ('D', 'DIURNO', 'DIURNA'):
        return 'Diurno'
    if token in ('N', 'NOCTURNO', 'NOCTURNA'):
        return 'Nocturno'
    if token in ('A', 'AMBOS', '24H', '24'):
        return 'Ambos'
    return 'Diurno'


def parse_turno_groups(value):
    if not value:
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [p.strip() for p in text.split('/') if p.strip()]
    return [parse_turno(p) for p in parts]


def parse_hours_groups(value):
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [p.strip() for p in text.split('/') if p.strip()]
    hours = []
    for part in parts:
        try:
            hours.append(int(float(part)))
        except (TypeError, ValueError):
            continue
    return hours


def parse_dias(value):
    if not value:
        return []
    text = str(value).strip().upper()
    text = text.replace('"', '').replace("'", '')
    if not text:
        return []
    tokens = re.split(r'[\s,;/|]+', text)
    mapping = {
        'L': 1, 'LU': 1, 'LUN': 1, 'LUNES': 1,
        'M': 2, 'MA': 2, 'MAR': 2, 'MARTES': 2,
        'X': 3, 'MI': 3, 'MIE': 3, 'MIERCOLES': 3,
        'J': 4, 'JU': 4, 'JUE': 4, 'JUEVES': 4,
        'V': 5, 'VI': 5, 'VIE': 5, 'VIERNES': 5,
        'S': 6, 'SA': 6, 'SAB': 6, 'SABADO': 6,
        'D': 7, 'DO': 7, 'DOM': 7, 'DOMINGO': 7,
    }
    result = set()
    for tok in tokens:
        if not tok:
            continue
        tok = re.sub(r'[^A-Z0-9]', '', tok.strip('.').upper())
        if tok.isdigit():
            num = int(tok)
            if 1 <= num <= 7:
                result.add(num)
            continue
        if tok in mapping:
            result.add(mapping[tok])
    return sorted(result)


def parse_dias_groups(value):
    if not value:
        return []
    text = str(value).strip().upper()
    text = text.replace('"', '').replace("'", '')
    if not text:
        return []
    # Support "LUNES-JUEVES / VIERNES-SABADO" or "L,M,X,J / V,S"
    group_tokens = [g.strip() for g in text.split('/') if g.strip()]
    mapping = {
        'L': 1, 'LU': 1, 'LUN': 1, 'LUNES': 1,
        'M': 2, 'MA': 2, 'MAR': 2, 'MARTES': 2,
        'X': 3, 'MI': 3, 'MIE': 3, 'MIERCOLES': 3,
        'J': 4, 'JU': 4, 'JUE': 4, 'JUEVES': 4,
        'V': 5, 'VI': 5, 'VIE': 5, 'VIERNES': 5,
        'S': 6, 'SA': 6, 'SAB': 6, 'SABADO': 6,
        'D': 7, 'DO': 7, 'DOM': 7, 'DOMINGO': 7,
    }
    def normalize_tok(tok: str):
        tok = re.sub(r'[^A-Z0-9]', '', tok.strip().upper())
        return tok

    groups = []
    for group in group_tokens:
        group = group.replace(' A ', '-').replace(' A\t', '-').replace('\tA ', '-')
        days = []
        if '-' in group:
            parts = [p for p in re.split(r'-+', group) if p.strip()]
            if len(parts) >= 2:
                start = mapping.get(normalize_tok(parts[0]))
                end = mapping.get(normalize_tok(parts[1]))
                if start and end:
                    if start <= end:
                        days = list(range(start, end + 1))
                    else:
                        days = list(range(start, 8)) + list(range(1, end + 1))
        if not days:
            tokens = re.split(r'[\s,;|]+', group)
            for tok in tokens:
                if not tok:
                    continue
                key = normalize_tok(tok.strip('.'))
                if key.isdigit():
                    num = int(key)
                    if 1 <= num <= 7:
                        days.append(num)
                    continue
                if key in mapping:
                    days.append(mapping[key])
        if days:
            groups.append(sorted(set(days)))
    return groups


def _expand_compact_dias(token: str):
    if not token:
        return []
    token = re.sub(r'[^A-Z]', '', token.upper())
    mapping = {'L': 1, 'M': 2, 'X': 3, 'J': 4, 'V': 5, 'S': 6, 'D': 7}
    if len(token) == 2 and token[0] in mapping and token[1] in mapping and token[0] != token[1]:
        start = mapping[token[0]]
        end = mapping[token[1]]
        if start <= end:
            return list(range(start, end + 1))
        return list(range(start, 8)) + list(range(1, end + 1))
    days = []
    for ch in token:
        if ch in mapping:
            days.append(mapping[ch])
    return sorted(set(days))


def parse_compact_horas_turno_dias(value):
    """Parsea el resumen compacto de un puesto. Acepta ambos formatos:
      - Con H: '24HLD', '12HDJM', '9HDLV', '5HDLU' (numero + H + turno? + dias)
      - Con turno y espacio: '24D LD', '12D LV', '12N LD' (numero + turno + dias)
      - Decimales y multi-grupo: '5HDLU - 4.5HDV - 5HDSD'
    """
    if value is None:
        return []
    text = str(value).strip().upper()
    if not text:
        return []
    # separar grupos por '/' o ' - '
    raw_parts = re.split(r'\s*/\s*|\s+-\s+', text)
    groups = []
    for part in raw_parts:
        p = re.sub(r'\s+', '', part)
        if not p:
            continue
        # numero(decimal) + H opcional + turno opcional (D/N) + dias (1-2 letras de LMXJVSD)
        m = re.match(r'^(\d+(?:[.,]\d+)?)H?([DN])?([LMXJVSD]{1,2})?$', p)
        if not m:
            continue
        try:
            hours_val = int(round(float(m.group(1).replace(',', '.'))))
        except ValueError:
            hours_val = 12
        turno_token = m.group(2) or ''
        dias_token = m.group(3) or ''
        groups.append({
            'hours': hours_val,
            'turno': parse_turno(turno_token) if turno_token else None,
            'dias': _expand_compact_dias(dias_token),
        })
    return groups


def parse_calendar_value(val):
    if val is None:
        return ''
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val)).strip().upper()
        return str(val).strip().upper()
    return str(val).strip().upper()


def _detect_month_year_from_sheet(rows):
    month_map = {
        'ENERO': 1,
        'FEBRERO': 2,
        'MARZO': 3,
        'ABRIL': 4,
        'MAYO': 5,
        'JUNIO': 6,
        'JULIO': 7,
        'AGOSTO': 8,
        'SEPTIEMBRE': 9,
        'SETIEMBRE': 9,
        'OCTUBRE': 10,
        'NOVIEMBRE': 11,
        'DICIEMBRE': 12,
    }
    for row in rows[:30]:
        for cell in row:
            if not cell:
                continue
            text = str(cell).strip().upper()
            match = re.search(r'(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+(\d{4})', text)
            if match:
                month = month_map.get(match.group(1))
                year = int(match.group(2))
                if month:
                    return year, month
    return None, None


def compute_horas(hora_ingreso, hora_salida):
    if not hora_ingreso or not hora_salida:
        return 12
    base = datetime(2000, 1, 1)
    dt_in = datetime.combine(base.date(), hora_ingreso)
    dt_out = datetime.combine(base.date(), hora_salida)
    if dt_out <= dt_in:
        dt_out += timedelta(days=1)
    hours = (dt_out - dt_in).total_seconds() / 3600.0
    if hours <= 0:
        return 12
    return int(round(hours))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def importar_puestos_asignaciones(request):
    # si el usuario no tiene permiso de importacion, retorna un jsonreponse con error 403
    if not request.user.has_perm('CoreFisica.import_puestos_asignaciones'):
        return JsonResponse({'error': 'No Autorizado'}, status=403)
    # se espera  un respuesta con un archivo excel
    upload = request.FILES.get('file')
    # si no se recibe un archivo, retorna un jsonresponse con error 400
    if not upload:
        return JsonResponse({'error': 'Falta el archivo (campo file)'}, status=400)

    cliente_id = request.GET.get('cliente_id')
    # si se recibe cliente_id, intenta convertirlo a entero, si no es posible, lo ignora y continua sin filtro de cliente
    if cliente_id:
        try:
            cliente_id = int(cliente_id)
        except (TypeError, ValueError):
            cliente_id = None

    try:
        # intenta abrir el archivo excel usando openpyxl, si no es posible, retorna un jsonresponse con error 400
        wb = load_workbook(upload, read_only=False, data_only=True)
    except Exception as exc:
        return JsonResponse({'error': f'No se pudo abrir el archivo: {exc}'}, status=400)

    # Si es el FORMATO REPORTE (el que genera Descargar), usar el importador dedicado
    try:
        if es_formato_reporte(wb):
            resumen = importar_formato_reporte(request, wb, cliente_id)
            return JsonResponse(resumen, status=200)
    except Exception:
        logger.exception('Error importando formato reporte')
        return JsonResponse({'error': 'No se pudo importar el formato reporte'}, status=500)

    # ws es la hoja activa del libro excel
    ws = wb.active
    # rows es una lista de filas de la hoja excel, cada fila es una tupla de valores de celdas, usando values_only=True para obtener solo los valores sin formato
    rows = list(ws.iter_rows(values_only=True))
    # si no se encuentran filas en el archivo, retorna un jsonresponse con error 400
    if not rows:
        return JsonResponse({'error': 'El archivo esta vacio'}, status=400)
    # se buscan las columnas obligatorias en las primeras 15 filas del archivo, normalizando los encabezados y comparandolos con el HEADER_MAP para encontrar los indices de las columnas necesarias, si no se encuentran todas las columnas obligatorias, retorna un jsonresponse con error 400 indicando las columnas faltantes y los encabezados detectados
    header_idx = None
    header_row_num = None
    headers_raw = []
    for ridx, row in enumerate(rows[:15]):
        candidate_headers = [normalize_header(h) for h in row]
        tmp_idx = {HEADER_MAP[h]: i for i, h in enumerate(candidate_headers) if h in HEADER_MAP}
        headers_raw = candidate_headers
        required = {'puesto', 'cedula', 'hora_ingreso', 'hora_salida'}
        alt_required = {'dias', 'horas'}
        if required.issubset(set(tmp_idx.keys())):
            if not alt_required.intersection(set(tmp_idx.keys())):
                continue
            header_idx = tmp_idx
            header_row_num = ridx
            break
    # si no se encuentran todas las columnas obligatorias, retorna un jsonresponse con error 400 indicando las columnas faltantes y los encabezados detectados
    if header_idx is None:
        return JsonResponse({
            'error': 'Faltan columnas obligatorias: PUESTO, CEDULA, HORA INGRESO, HORA SALIDA y (DIAS o HORAS)',
            'headers_detectados': headers_raw
        }, status=400)
    # detectar si la fila siguiente contiene los numeros de dias (1..31) para el calendario
    day_header_row_num = None
    if header_row_num is not None and (header_row_num + 1) < len(rows):
        candidate = rows[header_row_num + 1]
        candidate_headers = [normalize_header(h) for h in candidate]
        day_idx = {HEADER_MAP[h]: i for i, h in enumerate(candidate_headers) if h in HEADER_MAP and h.startswith(tuple(str(d) for d in range(1, 32)))}
        # si hay suficientes columnas de dias, usar esta fila como encabezado de calendario
        if len(day_idx) >= 10:
            day_header_row_num = header_row_num + 1
            for key, idx in day_idx.items():
                if key not in header_idx:
                    header_idx[key] = idx
    sheet_year, sheet_month = _detect_month_year_from_sheet(rows)
    req_month = request.GET.get('mes') or request.POST.get('mes')
    req_year = request.GET.get('anio') or request.POST.get('anio')
    try:
        req_month = int(req_month) if req_month is not None else None
    except (TypeError, ValueError):
        req_month = None
    try:
        req_year = int(req_year) if req_year is not None else None
    except (TypeError, ValueError):
        req_year = None
    if req_month is not None and not (1 <= req_month <= 12):
        req_month = None
    if req_year is not None and req_year < 1:
        req_year = None
    # se inicializa un diccionario de resumen para llevar conteo de filas procesadas, personas/puestos/horarios/asignaciones creadas o actualizadas, y errores encontrados durante el proceso de importacion
    resumen = {
        'total_filas': 0,
        'filas_validas': 0,
        'personas_creadas': 0,
        'puestos_creados': 0,
        'horarios_creados': 0,
        'asignaciones_creadas': 0,
        'asignaciones_actualizadas': 0,
        'errores': [],
    }
    # start_row se establece como la fila siguiente a la fila de encabezado encontrada, para comenzar a procesar los datos desde esa fila en adelante
    start_row = (header_row_num or 0) + 1
    if day_header_row_num is not None and day_header_row_num >= start_row:
        start_row = day_header_row_num + 1

    try:
        touched_asig_ids = set()
        touched_dates = set()
        regenerated_future_signatures = {}
        # Personas importadas por (puesto, mes, anio) -> para reemplazar sin duplicar
        from collections import defaultdict as _dd
        puesto_personas = _dd(set)
        with transaction.atomic():
            for i, row in enumerate(rows[start_row:], start=start_row + 1):
                if not row or all(v is None or str(v).strip() == '' for v in row):
                    continue
                resumen['total_filas'] += 1

                def col(key):
                    idx = header_idx.get(key)
                    return norm(row[idx]) if idx is not None and idx < len(row) else ''

                def col_raw(key):
                    idx = header_idx.get(key)
                    return row[idx] if idx is not None and idx < len(row) else None

                instalacion_id = col('instalacion_id')
                instalacion_nombre = col('instalacion')
                cliente_ruc = col('cliente_ruc')
                cliente_nombre = col('cliente')
                puesto_nombre = col('puesto')
                puesto_tipo = col('puesto_tipo')
                cantidad_puestos = col('cantidad_puestos')
                patron_codigo = col('patron')
                patron_id = col('patron_id')

                cedula = normalize_cedula(col('cedula'))
                apellidos = col('apellidos')
                nombres = col('nombres')
                if not apellidos and not nombres:
                    full_name = col('apellidos_nombres')
                    if full_name:
                        tokens = [t for t in re.split(r'\s+', full_name.strip()) if t]
                        if len(tokens) >= 3:
                            apellidos = ' '.join(tokens[:2])
                            nombres = ' '.join(tokens[2:])
                        elif len(tokens) == 2:
                            apellidos = tokens[0]
                            nombres = tokens[1]
                        elif len(tokens) == 1:
                            apellidos = tokens[0]
                            nombres = tokens[0]
                persona_tipo = col('tipo')

                hora_ingreso = parse_excel_time(col_raw('hora_ingreso'))
                hora_salida = parse_excel_time(col_raw('hora_salida'))
                horas_raw = col('horas')
                turno = parse_turno(col('turno'))
                dias_groups = parse_dias_groups(col('dias'))
                compact_groups = []
                if horas_raw and re.search(r'[A-Z]', str(horas_raw).upper()):
                    compact_groups = parse_compact_horas_turno_dias(horas_raw)
                    if compact_groups and not dias_groups:
                        dias_groups = [g['dias'] for g in compact_groups if g.get('dias')]
                fecha = parse_excel_date(col_raw('fecha')) if header_idx.get('fecha') is not None else None
                # si el puesto_nombre se agrega un mensaje de error al resumen indicando que el puesto esta vacio y se continua con la siguiente fila sin procesar la fila actual, ya que el puesto es un campo obligatorio para crear o actualizar una asignacion
                if not puesto_nombre:
                    resumen['errores'].append(f'Fila {i}: puesto vacio')
                    continue
                # si la cedula se agrega un mensaje de error al resumen indicando que la cedula esta vacia o invalida y se continua con la siguiente fila sin procesar la fila actual, ya que la cedula es un campo obligatorio para crear o actualizar una persona y asignacion
                if not cedula:
                    resumen['errores'].append(f'Fila {i}: cedula vacia o invalida')
                    continue
                # si la hora_ingreso o hora_salida es invalida se agrega un mensaje de error al resumen indicando que la hora de ingreso o salida es invalida y se continua con la siguiente fila sin procesar la fila actual, ya que ambos campos son obligatorios para crear o actualizar un horario y asignacion
                if (not hora_ingreso or not hora_salida) and not horas_raw:
                    resumen['errores'].append(f'Fila {i}: hora ingreso/salida invalida')
                    continue
                # si la lista de dias esta vacia se agrega un mensaje de error al resumen indicando que los dias estan vacios y se continua con la siguiente fila sin procesar la fila actual, ya que los dias son un campo obligatorio para crear o actualizar un puesto horario y asignacion
                if not dias_groups:
                    resumen['errores'].append(f'Fila {i}: dias vacio')
                    continue
                # se intenta obtener la instalacion usando el instalacion_id si se proporciona, si no se encuentra la instalacion con ese id, se agrega un mensaje de error al resumen indicando que la instalacion no fue encontrada y se continua con la siguiente fila sin procesar la fila actual, ya que la instalacion es un campo obligatorio para crear o actualizar un puesto y asignacion. Si no se proporciona el instalacion_id, se intenta buscar la instalacion usando el nombre de la instalacion y opcionalmente filtrando por cliente usando el cliente_id, cliente_ruc o cliente_nombre si se proporcionan, si se encuentran varias instalaciones que coinciden con el nombre, se agrega un mensaje de error al resumen indicando que hay instalaciones duplicadas y se continua con la siguiente fila sin procesar la fila actual, ya que no se puede determinar a cual instalacion asociar el puesto y asignacion. Si no se encuentra ninguna instalacion que coincida con el nombre (y filtro de cliente), se agrega un mensaje de error al resumen indicando que la instalacion no fue encontrada y se continua con la siguiente fila sin procesar la fila actual, ya que la instalacion es un campo obligatorio para crear o actualizar un puesto y asignacion
                instalacion = None
                # si la instalacion_id se proporciona
                if instalacion_id:
                    try:
                        # se intenta obtener la instalacion usando el instalacion_id
                        instalacion = Instalacion.objects.get(id=int(instalacion_id))
                    except (ValueError, Instalacion.DoesNotExist):
                        resumen['errores'].append(f'Fila {i}: instalacion_id no encontrada')
                        continue
                # si la instalacion_id no se proporciona, se intenta buscar la instalacion usando el nombre de la instalacion y opcionalmente filtrando por cliente usando el cliente_id, cliente_ruc o cliente_nombre si se proporcionan
                else:
                    # si el nombre de la instalcion est avacio se agrega un mensaje de error el resumen indicando que la instalacion esta vacia y se continua con la siguiente fila sin procesar la fila actual, ya que la instalacion es un campo obligatorio para crear o actualizar un puesto y asignacion
                    if not instalacion_nombre:
                        # intentar inferir instalacion desde un puesto existente
                        existing_puestos = Puesto.objects.filter(nombre__iexact=puesto_nombre)
                        if existing_puestos.count() == 1:
                            instalacion = existing_puestos.first().instalacion
                        else:
                            resumen['errores'].append(f'Fila {i}: instalacion vacia, use INSTALACION o instale puesto existente')
                            continue
                    # se busca la instalacion usando el nombre de la instalacion
                    inst_qs = Instalacion.objects.filter(nombre__iexact=instalacion_nombre)
                    # si el cliente_id se proporciona, se filtra la instalacion por cliente_id
                    if cliente_id:
                        inst_qs = inst_qs.filter(cliente_id=cliente_id)
                    # si el cliente_ruc se proporciona, se busca el cliente por ruc
                    elif cliente_ruc:
                        cliente = Cliente.objects.filter(ruc=cliente_ruc).first()
                        # si se encuentra el cliente, se filtra la instalacion por cliente
                        if cliente:
                            inst_qs = inst_qs.filter(cliente=cliente)
                    # si el cliente_nombre se proporciona, se busca el cliente por nombre comercial
                    elif cliente_nombre:
                        cliente = Cliente.objects.filter(nombre_comercial__iexact=cliente_nombre).first()
                        if cliente:
                            inst_qs = inst_qs.filter(cliente=cliente)
                    # si la cantidad de instalaciones que coinciden con el nombre (y filtro de cliente) es mayor a 1, se agrega un mensaje de error al resumen indicando que hay instalaciones duplicadas y se continua con la siguiente fila sin procesar la fila actual, ya que no se puede determinar a cual instalacion asociar el puesto y asignacion
                    if inst_qs.count() > 1:
                        resumen['errores'].append(f'Fila {i}: instalacion duplicada, use instalacion_id o cliente')
                        continue
                    instalacion = inst_qs.first()
                    if not instalacion:
                        resumen['errores'].append(f'Fila {i}: instalacion no encontrada')
                        continue
                # persona se busca o crea una persona usando la cedula, si no se encuentra una persona con esa cedula.
                persona = Persona.objects.filter(cedula=cedula).first()
                # si no se encuentra una persona 
                if not persona:
                    if not apellidos or not nombres:
                        resumen['errores'].append(f'Fila {i}: apellidos/nombres requeridos para nueva persona')
                        continue
                    #persona se crea una persona nueva con los datos de nombres, apellidos, cedula, tipo
                    persona = Persona.objects.create(
                        nombres=str(nombres).strip().upper(),
                        apellidos=str(apellidos).strip().upper(),
                        cedula=cedula,
                        tipo=persona_tipo or None,
                    )
                    resumen['personas_creadas'] += 1
                # se obtiene o crea un horario usando la hora_ingreso y hora_salida
                horario, created_horario = Horario.objects.get_or_create(
                    hora_ingreso=hora_ingreso,
                    hora_salida=hora_salida,
                )
                # si se creo un nuevo horario, se incrementa el contador de horarios_creados en el resumen
                if created_horario:
                    resumen['horarios_creados'] += 1

                try:
                    #se intenta convertir la cantidad de puestos a entero, si no es posible, se establece en 1 por defecto, ya que la cantidad de puestos es un campo opcional para crear o actualizar un puesto y asignacion, pero si se proporciona debe ser un numero entero positivo
                    cantidad_int = int(cantidad_puestos) if cantidad_puestos else 1
                except (TypeError, ValueError):
                    cantidad_int = 1
                if cantidad_int < 1:
                    cantidad_int = 1
                # se obtiene o crea un puesto usando el nombre del puesto y la instalacion
                puesto, puesto_created = Puesto.objects.get_or_create(
                    instalacion=instalacion,
                    nombre=puesto_nombre,
                    defaults={
                        'cantidad_puestos': cantidad_int,
                        'tipo': puesto_tipo or None,
                    }
                )
                #si se creo un nuevo puesto, se incrementa el cantador de puestos_ creados en el resumen
                if puesto_created:
                    resumen['puestos_creados'] += 1
                # si no se creo un nuevo puesto
                else:
                    #si se proporciono la cantidad de puestos y es diferente a la cantidad de puestos actual del puesto, se actualiza la cantidad de puestos del puesto con el valor proporcionado, ya que la cantidad de puestos es un campo opcional para crear o actualizar un puesto y asignacion, pero si se proporciona debe ser un numero entero positivo y se asume que el valor proporcionado es el correcto para ese puesto
                    if cantidad_int and puesto.cantidad_puestos != cantidad_int:
                        puesto.cantidad_puestos = cantidad_int
                        puesto.save(update_fields=['cantidad_puestos'])
                    if puesto_tipo and puesto.tipo != puesto_tipo:
                        puesto.tipo = puesto_tipo
                        puesto.save(update_fields=['tipo'])
                # se actualizan o crean los puestos horarios para el puesto usando la lista de dias, hora_ingreso, hora_salida y turno proporcionados, ya que los puestos horarios son necesarios para crear o actualizar una asignacion y se asume que el horario y turno proporcionados aplican para todos los dias indicados
                horas_groups = parse_hours_groups(horas_raw)
                turnos_groups = parse_turno_groups(col('turno'))
                if compact_groups:
                    horas_groups = [g['hours'] for g in compact_groups]
                    turnos_groups = [g['turno'] for g in compact_groups]
                default_horas = compute_horas(hora_ingreso, hora_salida)
                for idx, dias in enumerate(dias_groups):
                    horas = horas_groups[idx] if idx < len(horas_groups) else default_horas
                    turno_val = turnos_groups[idx] if idx < len(turnos_groups) else turno
                    if not turno_val:
                        turno_val = turno
                    for dia in dias:
                        PuestoHorario.objects.update_or_create(
                            puesto=puesto,
                            dia=dia,
                            defaults={'horas': horas, 'turno': turno_val}
                        )

                try:
                    # se sincroniza el puesto con los horarios usando el metodo sync_from_horarios, para asegurar que el puesto tenga el horario correcto basado en los puestos horarios asociados, ya que el horario es un campo necesario para crear o actualizar una asignacion y se asume que el horario del puesto debe reflejar los horarios definidos en los puestos horarios asociados
                    puesto.sync_from_horarios()
                    puesto.save()
                except Exception:
                    pass
                
                # se actualizan o crean las asignaciones para la persona, puesto, instalacion, horario
                if fecha:
                    ref_date = fecha
                elif req_year and req_month:
                    ref_date = date(req_year, req_month, 1)
                elif sheet_year and sheet_month:
                    ref_date = date(sheet_year, sheet_month, 1)
                else:
                    ref_date = date.today()
                mes = ref_date.month
                anio = ref_date.year
                patron_obj = None
                if patron_id:
                    try:
                        patron_obj = PatronAsignacion.objects.filter(id=int(patron_id)).first()
                    except (TypeError, ValueError):
                        patron_obj = None
                if not patron_obj and patron_codigo:
                    token = str(patron_codigo).strip()
                    patron_obj = PatronAsignacion.objects.filter(codigo=token).first()
                    if patron_obj is None and token.isdigit():
                        patron_obj = PatronAsignacion.objects.filter(id=int(token)).first()
                # asig se actualiza o crea una asignacion usando persona + puesto + mes + anio como claves
                defaults = {
                    'cliente': instalacion.cliente,
                    'instalacion': instalacion,
                    'puesto': puesto,
                    'horario': horario,
                    'fecha': None,
                    'patronAsignacion': patron_obj,
                    'estado': 'ACTIVO',
                    'publicada_calendario': True,
                    'recurring': True,
                    'start_date': date(ref_date.year, ref_date.month, 1),
                    'end_date': None,
                }
                if not patron_obj:
                    defaults['patronAsignacion'] = None

                asig, created_asig = Asignacion.objects.update_or_create(
                    persona=persona,
                    mes=mes,
                    anio=anio,
                    defaults=defaults,
                )
                touched_asig_ids.add(asig.id)
                touched_dates.add(ref_date)
                puesto_personas[(puesto.id, mes, anio)].add(persona.id)
                # si se creo una nueva asignacion
                if created_asig:
                    resumen['asignaciones_creadas'] += 1
                else:
                    resumen['asignaciones_actualizadas'] += 1

                # aplicar calendario manual desde columnas 1..31 si existen
                calendar_updates = {}
                raw_month_values = []
                days_in_month = (date(ref_date.year, ref_date.month + 1, 1) - timedelta(days=1)).day if ref_date.month < 12 else 31
                has_calendar_values = False
                for day_num in range(1, 32):
                    if day_num > days_in_month:
                        continue
                    key = f'day_{day_num}'
                    idx = header_idx.get(key)
                    raw_val = row[idx] if (idx is not None and idx < len(row)) else None
                    val = parse_calendar_value(raw_val)
                    raw_month_values.append(val)
                    if not val:
                        continue
                    has_calendar_values = True

                if has_calendar_values:
                    # Tomar solo valores no vacios como ciclo base y completar todo el primer mes.
                    seq_values_future = [v for v in raw_month_values if str(v or '').strip()]
                    cycle_len = len(seq_values_future)
                    if cycle_len <= 0:
                        raise ValueError('Secuencia vacia')

                    filled_month_values = []
                    sequence_index = 0
                    for day_num in range(1, days_in_month + 1):
                        explicit = raw_month_values[day_num - 1] if (day_num - 1) < len(raw_month_values) else ''
                        if str(explicit or '').strip():
                            val = explicit
                        else:
                            val = seq_values_future[sequence_index % cycle_len]
                        filled_month_values.append(val)
                        sequence_index += 1

                    for day_num, val in enumerate(filled_month_values, start=1):
                        day_date = date(ref_date.year, ref_date.month, day_num)
                        week_index = (day_num - 1) // 7
                        week_start = date(ref_date.year, ref_date.month, 1) + timedelta(days=week_index * 7)
                        day_field = ['mon','tue','wed','thu','fri','sat','sun'][day_date.weekday()]
                        calendar_updates.setdefault(week_start, {})[day_field] = val

                    week_count = ((days_in_month - 1) // 7) + 1
                    month_start = date(ref_date.year, ref_date.month, 1)
                    target_week_starts = [month_start + timedelta(days=7 * i) for i in range(week_count)]
                    if target_week_starts:
                        AsignacionSemanal.objects.filter(
                            asignacion_id=asig.id,
                            week_start__in=target_week_starts,
                        ).delete()
                    for ws, day_map in calendar_updates.items():
                        defaults = {**day_map, 'puesto_id': puesto.id}
                        obj, created = AsignacionSemanal.objects.get_or_create(
                            asignacion_id=asig.id,
                            week_start=ws,
                            defaults=defaults,
                        )
                        if not created:
                            changed = False
                            for d_key, d_val in day_map.items():
                                setattr(obj, d_key, d_val)
                                changed = True
                            if getattr(obj, 'puesto_id', None) is None:
                                obj.puesto_id = puesto.id
                                changed = True
                            if changed:
                                obj.save()
                    # Regenerar los proximos 24 meses para continuar la secuencia.
                    regen_key = (persona.id, puesto.id, ref_date.year, ref_date.month)
                    seq_signature = tuple(filled_month_values)
                    if regenerated_future_signatures.get(regen_key) == seq_signature:
                        resumen['filas_validas'] += 1
                        continue
                    regenerated_future_signatures[regen_key] = seq_signature
                    try:
                        def add_months(d, months):
                            year = d.year + (d.month - 1 + months) // 12
                            month = (d.month - 1 + months) % 12 + 1
                            return date(year, month, 1)

                        # Continuar en el mes siguiente justo donde terminó el primer mes completado.
                        base_month_start = date(ref_date.year, ref_date.month, 1)
                        for offset in range(1, 25):
                            target_start = add_months(base_month_start, offset)
                            target_year = target_start.year
                            target_month = target_start.month
                            if target_month == 12:
                                target_end = date(target_year + 1, 1, 1) - timedelta(days=1)
                            else:
                                target_end = date(target_year, target_month + 1, 1) - timedelta(days=1)
                            target_asig, _ = Asignacion.objects.update_or_create(
                                persona=persona,
                                mes=target_month,
                                anio=target_year,
                                defaults={
                                    'cliente': instalacion.cliente,
                                    'instalacion': instalacion,
                                    'puesto': puesto,
                                    'horario': horario,
                                    'fecha': None,
                                    'patronAsignacion': patron_obj,
                                    'estado': 'ACTIVO',
                                    'publicada_calendario': True,
                                    'recurring': True,
                                    'start_date': date(target_year, target_month, 1),
                                    'end_date': None,
                                }
                            )
                            days_in_target = target_end.day
                            weekly_payload = {}
                            for day_num in range(1, days_in_target + 1):
                                day_date = date(target_year, target_month, day_num)
                                week_index = (day_num - 1) // 7
                                week_start = date(target_year, target_month, 1) + timedelta(days=week_index * 7)
                                day_field = ['mon','tue','wed','thu','fri','sat','sun'][day_date.weekday()]
                                val = seq_values_future[sequence_index % cycle_len]
                                sequence_index += 1
                                if week_start not in weekly_payload:
                                    weekly_payload[week_start] = {}
                                weekly_payload[week_start][day_field] = val

                            if weekly_payload:
                                target_week_starts = list(weekly_payload.keys())
                                AsignacionSemanal.objects.filter(
                                    asignacion_id=target_asig.id,
                                    week_start__in=target_week_starts
                                ).delete()
                                bulk_rows = []
                                for ws_key, day_map in weekly_payload.items():
                                    row_data = {
                                        'asignacion_id': target_asig.id,
                                        'week_start': ws_key,
                                        'puesto_id': puesto.id,
                                        'mon': day_map.get('mon', ''),
                                        'tue': day_map.get('tue', ''),
                                        'wed': day_map.get('wed', ''),
                                        'thu': day_map.get('thu', ''),
                                        'fri': day_map.get('fri', ''),
                                        'sat': day_map.get('sat', ''),
                                        'sun': day_map.get('sun', ''),
                                    }
                                    bulk_rows.append(AsignacionSemanal(**row_data))
                                AsignacionSemanal.objects.bulk_create(bulk_rows)
                    except Exception:
                        logger.exception('Error regenerando secuencia de los proximos meses')
                else:
                    try:
                        from .asignacion_views import _rebuild_asignacion_semanal
                        _rebuild_asignacion_semanal(asig, force_all=created_asig)
                    except Exception:
                        logger.exception('Error reconstruyendo asignacion semanal')

                resumen['filas_validas'] += 1

            # Reemplazo sin duplicar: en cada puesto/mes/año importado, desactivar las
            # personas que YA NO aparecen en el archivo (fueron reemplazadas).
            for (pid, pmes, panio), persona_ids in puesto_personas.items():
                sobrantes = Asignacion.objects.filter(
                    puesto_id=pid, mes=pmes, anio=panio, estado='ACTIVO'
                ).exclude(persona_id__in=persona_ids)
                for o in sobrantes:
                    o.estado = 'INACTIVO'
                    o.save(update_fields=['estado'])
                    ReporteAsistencia.objects.filter(asignacion=o).update(
                        estado='TURNO', estado_asistencia='', reemplazo=None,
                        descripcion=None, row_color=None
                    )

            if touched_asig_ids:
                # Asegurar ReporteAsistencia base para las asignaciones importadas
                asig_qs = Asignacion.objects.select_related(
                    'persona', 'cliente', 'instalacion', 'puesto', 'horario'
                ).filter(id__in=touched_asig_ids)
                for asig in asig_qs:
                    try:
                        reporte, _ = ReporteAsistencia.objects.get_or_create(asignacion=asig)
                        reporte.persona = asig.persona
                        reporte.cliente = asig.cliente
                        reporte.instalacion = asig.instalacion
                        reporte.puesto = asig.puesto
                        reporte.horario = asig.horario
                        reporte.puesto_tipo = getattr(asig.puesto, 'tipo', None) if asig.puesto else None
                        reporte.save()
                    except Exception:
                        pass

                # Actualizar resumen de consolidado para fechas importadas (turnos diurno/nocturno)
                try:
                    from .reporte_asistencia_views import _build_reporte_asistencia_data
                    from .consolidado_views import _build_resumen_manual
                    for ref_date in touched_dates:
                        for turno_val in ('Diurno', 'Nocturno'):
                            rows_data = _build_reporte_asistencia_data(
                                fecha=ref_date.isoformat(),
                                turno=turno_val
                            )
                            _build_resumen_manual(ref_date, turno_val, rows_data)
                except Exception:
                    pass

        return JsonResponse(resumen, status=200)
    except Exception:
        logger.exception('Error importando puestos/asignaciones')
        return JsonResponse({'error': 'No se pudo importar puestos/asignaciones'}, status=500)


# ============================================================================
# Importación del FORMATO REPORTE (el que genera el botón Descargar de Asignaciones)
# ============================================================================
def _rep_norm(v):
    import unicodedata
    if v is None:
        return ''
    t = str(v).strip().upper().replace('.', ' ').replace('_', ' ')
    t = ''.join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c))
    return ' '.join(t.split())


def _periodo_minimo(seq):
    """Detecta el período mínimo EXACTO de una secuencia (ej. DDDNNNF -> 7).
    Si no hay período exacto más corto, devuelve la secuencia completa."""
    n = len(seq)
    if n == 0:
        return seq
    for p in range(1, n):
        if all(seq[i] == seq[i % p] for i in range(n)):
            return seq[:p]
    return list(seq)


def _ciclo_para_continuar(seq):
    """Devuelve el ciclo a usar para continuar el patrón en meses futuros.
    1) Período exacto si existe. 2) Si la fila es irregular, prueba longitudes
    típicas (7,6,5,8,14,10,...) y usa la que mejor encaje (>=85%). 3) Si nada
    encaja, repite el mes completo."""
    n = len(seq)
    if n == 0:
        return list(seq)
    # 1) período exacto
    exacto = _periodo_minimo(seq)
    if len(exacto) < n:
        return exacto
    # 2) mejor aproximado entre longitudes típicas de rotación
    candidatos = [7, 6, 5, 8, 14, 10, 12, 4, 3, 2, 21, 28]
    mejor_p, mejor_ratio = None, 0.0
    for p in candidatos:
        if p >= n:
            continue
        aciertos = sum(1 for i in range(n) if seq[i] == seq[i % p])
        ratio = aciertos / n
        if ratio > mejor_ratio:
            mejor_ratio, mejor_p = ratio, p
    if mejor_p and mejor_ratio >= 0.85:
        return seq[:mejor_p]
    # 3) sin patrón claro -> repetir el mes completo
    return list(seq)


def _rep_detectar_columnas(rows):
    for ri, row in enumerate(rows[:20]):
        H = {_rep_norm(c): j for j, c in enumerate(row) if c is not None and str(c).strip()}
        if 'CLIENTE' in H and 'PUESTO' in H and 'CEDULA' in H and ('H INGRESO' in H or 'H SALIDA' in H):
            dias = []
            for j, c in enumerate(row):
                s = str(c).strip() if c is not None else ''
                if s.isdigit() and 1 <= int(s) <= 31:
                    dias.append(j)
            col = {
                'ing': H.get('H INGRESO'), 'sal': H.get('H SALIDA'),
                'cli': H['CLIENTE'], 'pue': H['PUESTO'], 'resumen': H.get('TIPO'),
                'ced': H['CEDULA'], 'nombre': H.get('APELLIDOS Y NOMBRES'),
                'nominativo': H['CLIENTE'] - 1, 'dias': dias,
            }
            return ri, col
    return None, None


def es_formato_reporte(wb):
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        ri, _ = _rep_detectar_columnas(rows)
        if ri is not None:
            return True
    return False


def importar_formato_reporte(request, wb, cliente_id_filter=None):
    from .asignacion_semanal_views import _sync_sacafranco_to_reporte_y_consolidado, _validate_sacafranco_tokens
    from ..models import SacafrancoFila, SacafrancoFilaSemanal

    resumen = {
        'total_filas': 0, 'filas_validas': 0, 'personas_creadas': 0,
        'puestos_creados': 0, 'horarios_creados': 0, 'asignaciones_creadas': 0,
        'asignaciones_actualizadas': 0, 'sacafranco_creados': 0, 'errores': [],
    }

    req_month = request.GET.get('mes') or request.POST.get('mes')
    req_year = request.GET.get('anio') or request.POST.get('anio')
    try:
        req_month = int(req_month) if req_month else None
    except (TypeError, ValueError):
        req_month = None
    try:
        req_year = int(req_year) if req_year else None
    except (TypeError, ValueError):
        req_year = None

    touched_asig_ids = set()
    touched_dates = set()
    puesto_personas = {}
    orden_counter = 0  # orden de presentación según el orden del Excel (igual en todos los meses)
    WEEK_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

    with transaction.atomic():
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            ri, col = _rep_detectar_columnas(rows)
            if ri is None:
                continue
            sheet_year, sheet_month = _detect_month_year_from_sheet(rows)
            mes = req_month or sheet_month
            anio = req_year or sheet_year
            # Fallback: detectar nombre de mes suelto (sin año) y usar año actual
            if not mes:
                meses_map = {'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5,
                             'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'SETIEMBRE': 9,
                             'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12}
                for r in rows[:ri + 2]:
                    for c in r:
                        key = _rep_norm(c)
                        if key in meses_map:
                            mes = meses_map[key]
                            break
                    if mes:
                        break
            if not anio:
                anio = date.today().year
            if not mes:
                resumen['errores'].append(f'Hoja {ws.title}: no se detecto el mes')
                continue
            month_start = date(anio, mes, 1)
            days_in_month = (date(anio, mes + 1, 1) - timedelta(days=1)).day if mes < 12 else 31
            carry = {'nominativo': '', 'cli': '', 'pue': '', 'resumen': ''}
            carry_time = {'ing': None, 'sal': None}

            for i, row in enumerate(rows[ri + 1:], start=ri + 2):
                if not row or all(v is None or str(v).strip() == '' for v in row):
                    continue
                resumen['total_filas'] += 1

                def g(key):
                    j = col.get(key)
                    return row[j] if (j is not None and j < len(row)) else None

                for k in ('nominativo', 'cli', 'pue', 'resumen'):
                    v = g(k)
                    if v is not None and str(v).strip():
                        carry[k] = str(v).strip()

                cedula = normalize_cedula(norm(g('ced')))
                puesto_nombre = carry['pue']
                es_saca = _rep_norm(puesto_nombre) == 'SACAFRANCO'

                cal = []
                for d_i, dj in enumerate(col['dias']):
                    if d_i >= days_in_month:
                        break
                    cal.append(parse_calendar_value(row[dj]) if dj < len(row) else '')

                if es_saca:
                    if not cedula:
                        continue
                    persona = Persona.objects.filter(cedula=cedula).first()
                    if not persona:
                        toks = [t for t in re.split(r'\s+', norm(g('nombre'))) if t]
                        ap = ' '.join(toks[:2]) if len(toks) >= 2 else (toks[0] if toks else 'SF')
                        no = ' '.join(toks[2:]) if len(toks) > 2 else (toks[1] if len(toks) > 1 else ap)
                        persona = Persona.objects.create(nombres=no.upper(), apellidos=ap.upper(), cedula=cedula, tipo='SACAFRANCO')
                        resumen['personas_creadas'] += 1
                    orden_counter += 1
                    row_orden = orden_counter
                    fila, _ = SacafrancoFila.objects.get_or_create(persona=persona, mes=mes, anio=anio, defaults={'orden': row_orden})
                    if fila.orden != row_orden:
                        fila.orden = row_orden
                        fila.save(update_fields=['orden'])
                    for d_i, val in enumerate(cal):
                        day_num = d_i + 1
                        ws_start = month_start + timedelta(days=((day_num - 1) // 7) * 7)
                        day_field = WEEK_KEYS[date(anio, mes, day_num).weekday()]
                        sem, _ = SacafrancoFilaSemanal.objects.get_or_create(sacafranco_fila=fila, week_start=ws_start)
                        setattr(sem, day_field, (val or '').upper())
                        sem.save()
                    for wk in range(((days_in_month - 1) // 7) + 1):
                        ws_start = month_start + timedelta(days=wk * 7)
                        sem = SacafrancoFilaSemanal.objects.filter(sacafranco_fila=fila, week_start=ws_start).first()
                        if not sem:
                            continue
                        payload = {k: getattr(sem, k, '') for k in WEEK_KEYS}
                        try:
                            err, resolved = _validate_sacafranco_tokens(payload, ws_start)
                            if not err:
                                _sync_sacafranco_to_reporte_y_consolidado(fila.id, ws_start, payload, resolved)
                        except Exception:
                            pass

                    # Continuar el patrón del sacafranco en los próximos 36 meses
                    sf_vals = [(v or '').upper() for v in cal]
                    sf_ciclo = _ciclo_para_continuar(sf_vals)
                    if sf_ciclo and any(str(x).strip() for x in sf_ciclo):
                        sf_len = len(sf_ciclo)
                        sf_idx = len(sf_vals)

                        def _add_m(y, mo, off):
                            return (y + (mo - 1 + off) // 12), ((mo - 1 + off) % 12 + 1)

                        for off in range(1, 37):
                            ty, tm = _add_m(anio, mes, off)
                            t_start = date(ty, tm, 1)
                            t_days = (date(ty, tm + 1, 1) - timedelta(days=1)).day if tm < 12 else 31
                            t_fila, _ = SacafrancoFila.objects.get_or_create(persona=persona, mes=tm, anio=ty, defaults={'orden': row_orden})
                            if t_fila.orden != row_orden:
                                t_fila.orden = row_orden
                                t_fila.save(update_fields=['orden'])
                            wp = {}
                            for dn in range(1, t_days + 1):
                                wss = t_start + timedelta(days=((dn - 1) // 7) * 7)
                                df = WEEK_KEYS[date(ty, tm, dn).weekday()]
                                wp.setdefault(wss, {})[df] = sf_ciclo[sf_idx % sf_len]
                                sf_idx += 1
                            for wss, dm in wp.items():
                                sem2, _ = SacafrancoFilaSemanal.objects.get_or_create(sacafranco_fila=t_fila, week_start=wss)
                                for k, v in dm.items():
                                    setattr(sem2, k, v)
                                sem2.save()
                                payload2 = {k: getattr(sem2, k, '') for k in WEEK_KEYS}
                                try:
                                    err2, resolved2 = _validate_sacafranco_tokens(payload2, wss)
                                    if not err2:
                                        _sync_sacafranco_to_reporte_y_consolidado(t_fila.id, wss, payload2, resolved2)
                                except Exception:
                                    pass

                    resumen['sacafranco_creados'] += 1
                    resumen['filas_validas'] += 1
                    touched_dates.add(month_start)
                    continue

                if not cedula:
                    continue
                if not carry['nominativo']:
                    resumen['errores'].append(f'Fila {i}: sin nominativo (codigo de instalacion)')
                    continue
                instalacion = Instalacion.objects.filter(codigo__iexact=carry['nominativo']).first()
                if not instalacion:
                    resumen['errores'].append(f"Fila {i}: instalacion con codigo '{carry['nominativo']}' no existe")
                    continue
                if cliente_id_filter and instalacion.cliente_id != cliente_id_filter:
                    continue

                # arrastrar hora ingreso/salida de celdas combinadas (mismo puesto)
                raw_ing = g('ing')
                raw_sal = g('sal')
                if raw_ing is not None and str(raw_ing).strip():
                    carry_time['ing'] = raw_ing
                if raw_sal is not None and str(raw_sal).strip():
                    carry_time['sal'] = raw_sal
                hora_ingreso = parse_excel_time(raw_ing if (raw_ing is not None and str(raw_ing).strip()) else carry_time['ing'])
                hora_salida = parse_excel_time(raw_sal if (raw_sal is not None and str(raw_sal).strip()) else carry_time['sal'])
                if not hora_ingreso or not hora_salida:
                    resumen['errores'].append(f'Fila {i}: hora ingreso/salida invalida')
                    continue

                resumen_txt = carry['resumen'] or ''
                m = re.match(r'\s*(\d+)\s+(.*)', resumen_txt)
                cantidad = int(m.group(1)) if m else 1
                resto = m.group(2) if m else resumen_txt
                grupos = parse_compact_horas_turno_dias(resto) or []

                persona = Persona.objects.filter(cedula=cedula).first()
                if not persona:
                    toks = [t for t in re.split(r'\s+', norm(g('nombre'))) if t]
                    if len(toks) < 2:
                        resumen['errores'].append(f'Fila {i}: nombre incompleto')
                        continue
                    ap = ' '.join(toks[:2])
                    no = ' '.join(toks[2:]) or toks[1]
                    persona = Persona.objects.create(nombres=no.upper(), apellidos=ap.upper(), cedula=cedula, tipo='FIJOS')
                    resumen['personas_creadas'] += 1

                horario, h_created = Horario.objects.get_or_create(hora_ingreso=hora_ingreso, hora_salida=hora_salida)
                if h_created:
                    resumen['horarios_creados'] += 1

                puesto, p_created = Puesto.objects.get_or_create(
                    instalacion=instalacion, nombre=puesto_nombre,
                    defaults={'cantidad_puestos': cantidad}
                )
                if p_created:
                    resumen['puestos_creados'] += 1
                if not puesto.horario_id:
                    puesto.horario = horario
                    puesto.save(update_fields=['horario'])
                for grp in grupos:
                    for dia in grp.get('dias', []):
                        PuestoHorario.objects.update_or_create(
                            puesto=puesto, dia=dia,
                            defaults={'horas': grp.get('hours', 12), 'turno': grp.get('turno') or 'Diurno'}
                        )
                try:
                    puesto.sync_from_horarios()
                    puesto.save()
                except Exception:
                    pass

                orden_counter += 1
                row_orden = orden_counter
                asig, created = Asignacion.objects.update_or_create(
                    persona=persona, mes=mes, anio=anio,
                    defaults={
                        'cliente': instalacion.cliente, 'instalacion': instalacion,
                        'puesto': puesto, 'horario': horario, 'fecha': None,
                        'patronAsignacion': None, 'estado': 'ACTIVO',
                        'publicada_calendario': True, 'recurring': True,
                        'start_date': month_start, 'end_date': None,
                        'orden': row_orden,
                    }
                )
                touched_asig_ids.add(asig.id)
                touched_dates.add(month_start)
                puesto_personas.setdefault((puesto.id, mes, anio), set()).add(persona.id)
                resumen['asignaciones_creadas' if created else 'asignaciones_actualizadas'] += 1

                cal_by_week = {}
                for d_i, val in enumerate(cal):
                    day_num = d_i + 1
                    ws_start = month_start + timedelta(days=((day_num - 1) // 7) * 7)
                    day_field = WEEK_KEYS[date(anio, mes, day_num).weekday()]
                    cal_by_week.setdefault(ws_start, {})[day_field] = (val or '').upper()
                for ws_start, day_map in cal_by_week.items():
                    obj, _ = AsignacionSemanal.objects.get_or_create(
                        asignacion_id=asig.id, week_start=ws_start, defaults={'puesto_id': puesto.id}
                    )
                    for k, v in day_map.items():
                        setattr(obj, k, v)
                    obj.puesto_id = puesto.id
                    obj.save()

                # Continuar el patrón D/N/F en los próximos 36 meses (ciclo continuo)
                # Detectar el período REAL (ej. DDDNNNF=7) para no repetir el mes entero.
                cal_vals = [(v or '').upper() for v in cal]
                ciclo = _ciclo_para_continuar(cal_vals)
                if ciclo and any(str(x).strip() for x in ciclo):
                    cycle_len = len(ciclo)
                    seq_idx = len(cal_vals)  # desfase global: continúa donde terminó el mes

                    def _add_months(y, mo, off):
                        ny = y + (mo - 1 + off) // 12
                        nm = (mo - 1 + off) % 12 + 1
                        return ny, nm

                    for off in range(1, 37):
                        ty, tm = _add_months(anio, mes, off)
                        t_start = date(ty, tm, 1)
                        t_days = (date(ty, tm + 1, 1) - timedelta(days=1)).day if tm < 12 else 31
                        t_asig, _ = Asignacion.objects.update_or_create(
                            persona=persona, mes=tm, anio=ty,
                            defaults={
                                'cliente': instalacion.cliente, 'instalacion': instalacion,
                                'puesto': puesto, 'horario': horario, 'fecha': None,
                                'patronAsignacion': None, 'estado': 'ACTIVO',
                                'publicada_calendario': True, 'recurring': True,
                                'start_date': t_start, 'end_date': None,
                                'orden': row_orden,
                            }
                        )
                        puesto_personas.setdefault((puesto.id, tm, ty), set()).add(persona.id)
                        wp = {}
                        for dn in range(1, t_days + 1):
                            wss = t_start + timedelta(days=((dn - 1) // 7) * 7)
                            df = WEEK_KEYS[date(ty, tm, dn).weekday()]
                            wp.setdefault(wss, {})[df] = ciclo[seq_idx % cycle_len]
                            seq_idx += 1
                        for wss, dm in wp.items():
                            o, _ = AsignacionSemanal.objects.get_or_create(
                                asignacion_id=t_asig.id, week_start=wss, defaults={'puesto_id': puesto.id}
                            )
                            for k, v in dm.items():
                                setattr(o, k, v)
                            o.puesto_id = puesto.id
                            o.save()

                resumen['filas_validas'] += 1

        for (pid, pmes, panio), pers_ids in puesto_personas.items():
            for o in Asignacion.objects.filter(puesto_id=pid, mes=pmes, anio=panio, estado='ACTIVO').exclude(persona_id__in=pers_ids):
                o.estado = 'INACTIVO'
                o.save(update_fields=['estado'])
                ReporteAsistencia.objects.filter(asignacion=o).update(
                    estado='TURNO', estado_asistencia='', reemplazo=None, descripcion=None, row_color=None
                )

        for asig in Asignacion.objects.select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario').filter(id__in=touched_asig_ids):
            rep, _ = ReporteAsistencia.objects.get_or_create(asignacion=asig)
            rep.persona = asig.persona
            rep.cliente = asig.cliente
            rep.instalacion = asig.instalacion
            rep.puesto = asig.puesto
            rep.horario = asig.horario
            rep.puesto_tipo = getattr(asig.puesto, 'tipo', None) if asig.puesto else None
            rep.save()

        try:
            from .reporte_asistencia_views import _build_reporte_asistencia_data
            from .consolidado_views import _build_resumen_manual
            for ref_date in touched_dates:
                for turno_val in ('Diurno', 'Nocturno'):
                    rows_data = _build_reporte_asistencia_data(fecha=ref_date.isoformat(), turno=turno_val)
                    _build_resumen_manual(ref_date, turno_val, rows_data)
        except Exception:
            pass

    return resumen
