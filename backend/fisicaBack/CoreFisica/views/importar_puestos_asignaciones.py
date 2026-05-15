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
    if value is None:
        return []
    text = str(value).strip().upper()
    if not text:
        return []
    parts = [p.strip() for p in text.split('/') if p.strip()]
    groups = []
    for part in parts:
        part = re.sub(r'\s+', '', part)
        match = re.match(r'^(\d{1,2})H([DN])?([A-Z]+)?$', part)
        if not match:
            continue
        hours_val = int(match.group(1))
        turno_token = match.group(2) or ''
        dias_token = match.group(3) or ''
        groups.append({
            'hours': hours_val,
            'turno': parse_turno(turno_token) if turno_token else None,
            'dias': _expand_compact_dias(dias_token)
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
    for row in rows[:10]:
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
        wb = load_workbook(upload, read_only=True, data_only=True)
    except Exception as exc:
        return JsonResponse({'error': f'No se pudo abrir el archivo: {exc}'}, status=400)
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
    sheet_year, sheet_month = _detect_month_year_from_sheet(rows)
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

    try:
        touched_asig_ids = set()
        touched_dates = set()
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
                fecha = None
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
                ref_date = fecha or (date(sheet_year, sheet_month, 1) if sheet_year and sheet_month else date.today())
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
                    puesto=puesto,
                    mes=mes,
                    anio=anio,
                    defaults=defaults,
                )
                touched_asig_ids.add(asig.id)
                touched_dates.add(ref_date)
                # si se creo una nueva asignacion
                if created_asig:
                    resumen['asignaciones_creadas'] += 1
                else:
                    resumen['asignaciones_actualizadas'] += 1

                # aplicar calendario manual desde columnas 1..31 si existen
                calendar_updates = {}
                days_in_month = (date(ref_date.year, ref_date.month + 1, 1) - timedelta(days=1)).day if ref_date.month < 12 else 31
                has_calendar_values = False
                for day_num in range(1, 32):
                    if day_num > days_in_month:
                        continue
                    key = f'day_{day_num}'
                    idx = header_idx.get(key)
                    if idx is None or idx >= len(row):
                        continue
                    raw_val = row[idx]
                    val = parse_calendar_value(raw_val)
                    if not val:
                        continue
                    has_calendar_values = True
                    day_date = date(ref_date.year, ref_date.month, day_num)
                    week_index = (day_num - 1) // 7
                    week_start = date(ref_date.year, ref_date.month, 1) + timedelta(days=week_index * 7)
                    day_field = ['mon','tue','wed','thu','fri','sat','sun'][day_date.weekday()]
                    calendar_updates.setdefault(week_start, {})[day_field] = val

                if has_calendar_values:
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
                else:
                    try:
                        from .asignacion_views import _rebuild_asignacion_semanal
                        _rebuild_asignacion_semanal(asig, force_all=created_asig)
                    except Exception:
                        logger.exception('Error reconstruyendo asignacion semanal')

                resumen['filas_validas'] += 1

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
