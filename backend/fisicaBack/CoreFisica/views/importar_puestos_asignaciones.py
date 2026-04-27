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

from ..models import Cliente, Instalacion, Puesto, PuestoHorario, Persona, Horario, Asignacion

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
}


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
    return str(val).strip()


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


def parse_dias(value):
    if not value:
        return []
    text = str(value).strip().upper()
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
        tok = tok.strip('.').upper()
        if tok.isdigit():
            num = int(tok)
            if 1 <= num <= 7:
                result.add(num)
            continue
        if tok in mapping:
            result.add(mapping[tok])
    return sorted(result)


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
    if not request.user.has_perm('CoreFisica.add_asignacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': 'Falta el archivo (campo file)'}, status=400)

    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        try:
            cliente_id = int(cliente_id)
        except (TypeError, ValueError):
            cliente_id = None

    try:
        wb = load_workbook(upload, read_only=True, data_only=True)
    except Exception as exc:
        return JsonResponse({'error': f'No se pudo abrir el archivo: {exc}'}, status=400)

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return JsonResponse({'error': 'El archivo esta vacio'}, status=400)

    header_idx = None
    header_row_num = None
    headers_raw = []
    for ridx, row in enumerate(rows[:15]):
        candidate_headers = [normalize_header(h) for h in row]
        tmp_idx = {HEADER_MAP[h]: i for i, h in enumerate(candidate_headers) if h in HEADER_MAP}
        headers_raw = candidate_headers
        required = {'instalacion', 'puesto', 'cedula', 'hora_ingreso', 'hora_salida', 'dias'}
        if required.issubset(set(tmp_idx.keys())):
            header_idx = tmp_idx
            header_row_num = ridx
            break

    if header_idx is None:
        return JsonResponse({
            'error': 'Faltan columnas obligatorias: INSTALACION, PUESTO, CEDULA, HORA INGRESO, HORA SALIDA, DIAS',
            'headers_detectados': headers_raw
        }, status=400)

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

    start_row = (header_row_num or 0) + 1

    try:
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

                cedula = normalize_cedula(col('cedula'))
                apellidos = col('apellidos')
                nombres = col('nombres')
                persona_tipo = col('tipo')

                hora_ingreso = parse_excel_time(col_raw('hora_ingreso'))
                hora_salida = parse_excel_time(col_raw('hora_salida'))
                turno = parse_turno(col('turno'))
                dias = parse_dias(col('dias'))
                fecha = parse_excel_date(col_raw('fecha'))

                if not puesto_nombre:
                    resumen['errores'].append(f'Fila {i}: puesto vacio')
                    continue
                if not cedula:
                    resumen['errores'].append(f'Fila {i}: cedula vacia o invalida')
                    continue
                if not hora_ingreso or not hora_salida:
                    resumen['errores'].append(f'Fila {i}: hora ingreso/salida invalida')
                    continue
                if not dias:
                    resumen['errores'].append(f'Fila {i}: dias vacio')
                    continue

                instalacion = None
                if instalacion_id:
                    try:
                        instalacion = Instalacion.objects.get(id=int(instalacion_id))
                    except (ValueError, Instalacion.DoesNotExist):
                        resumen['errores'].append(f'Fila {i}: instalacion_id no encontrada')
                        continue
                else:
                    if not instalacion_nombre:
                        resumen['errores'].append(f'Fila {i}: instalacion vacia')
                        continue
                    inst_qs = Instalacion.objects.filter(nombre__iexact=instalacion_nombre)
                    if cliente_id:
                        inst_qs = inst_qs.filter(cliente_id=cliente_id)
                    elif cliente_ruc:
                        cliente = Cliente.objects.filter(ruc=cliente_ruc).first()
                        if cliente:
                            inst_qs = inst_qs.filter(cliente=cliente)
                    elif cliente_nombre:
                        cliente = Cliente.objects.filter(nombre_comercial__iexact=cliente_nombre).first()
                        if cliente:
                            inst_qs = inst_qs.filter(cliente=cliente)
                    if inst_qs.count() > 1:
                        resumen['errores'].append(f'Fila {i}: instalacion duplicada, use instalacion_id o cliente')
                        continue
                    instalacion = inst_qs.first()
                    if not instalacion:
                        resumen['errores'].append(f'Fila {i}: instalacion no encontrada')
                        continue

                persona = Persona.objects.filter(cedula=cedula).first()
                if not persona:
                    if not apellidos or not nombres:
                        resumen['errores'].append(f'Fila {i}: apellidos/nombres requeridos para nueva persona')
                        continue
                    persona = Persona.objects.create(
                        nombres=str(nombres).strip().upper(),
                        apellidos=str(apellidos).strip().upper(),
                        cedula=cedula,
                        tipo=persona_tipo or None,
                    )
                    resumen['personas_creadas'] += 1

                horario, created_horario = Horario.objects.get_or_create(
                    hora_ingreso=hora_ingreso,
                    hora_salida=hora_salida,
                )
                if created_horario:
                    resumen['horarios_creados'] += 1

                try:
                    cantidad_int = int(cantidad_puestos) if cantidad_puestos else 1
                except (TypeError, ValueError):
                    cantidad_int = 1
                if cantidad_int < 1:
                    cantidad_int = 1

                puesto, puesto_created = Puesto.objects.get_or_create(
                    instalacion=instalacion,
                    nombre=puesto_nombre,
                    defaults={
                        'cantidad_puestos': cantidad_int,
                        'tipo': puesto_tipo or None,
                    }
                )
                if puesto_created:
                    resumen['puestos_creados'] += 1
                else:
                    if cantidad_int and puesto.cantidad_puestos != cantidad_int:
                        puesto.cantidad_puestos = cantidad_int
                        puesto.save(update_fields=['cantidad_puestos'])
                    if puesto_tipo and puesto.tipo != puesto_tipo:
                        puesto.tipo = puesto_tipo
                        puesto.save(update_fields=['tipo'])

                horas = compute_horas(hora_ingreso, hora_salida)
                for dia in dias:
                    PuestoHorario.objects.update_or_create(
                        puesto=puesto,
                        dia=dia,
                        defaults={'horas': horas, 'turno': turno}
                    )

                try:
                    puesto.sync_from_horarios()
                    puesto.save()
                except Exception:
                    pass

                ref_date = fecha or date.today()
                mes = ref_date.month
                anio = ref_date.year

                asig, created_asig = Asignacion.objects.update_or_create(
                    persona=persona,
                    mes=mes,
                    anio=anio,
                    defaults={
                        'cliente': instalacion.cliente,
                        'instalacion': instalacion,
                        'puesto': puesto,
                        'horario': horario,
                        'fecha': fecha,
                        'estado': 'ACTIVO'
                    }
                )

                if created_asig:
                    resumen['asignaciones_creadas'] += 1
                else:
                    resumen['asignaciones_actualizadas'] += 1

                try:
                    from .asignacion_views import _rebuild_asignacion_semanal
                    _rebuild_asignacion_semanal(asig, force_all=created_asig)
                except Exception:
                    logger.exception('Error reconstruyendo asignacion semanal')

                resumen['filas_validas'] += 1

        return JsonResponse(resumen, status=200)
    except Exception:
        logger.exception('Error importando puestos/asignaciones')
        return JsonResponse({'error': 'No se pudo importar puestos/asignaciones'}, status=500)
