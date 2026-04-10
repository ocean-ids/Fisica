from datetime import date, datetime

from django.http import JsonResponse
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from ..models import Cliente, Instalacion, Puesto, Provincia, Canton


HEADER_MAP = {
    'RUC': 'ruc',
    'RAZON SOCIAL': 'razon_social',
    'RAZÓN SOCIAL': 'razon_social',
    'NOMBRE COMERCIAL': 'nombre_comercial',
    'NOMBRE_COMERCIAL': 'nombre_comercial',
    'NOMBRECOMERCIAL': 'nombre_comercial',
    'CLASIFICACION': 'clasificacion',
    'CLASIFICACIÓN': 'clasificacion',
    'INSTALACION': 'instalacion',
    'INSTALACIÓN': 'instalacion',
    'PROVINCIA': 'provincia',
    'CIUDAD': 'ciudad',

    'FECHA DE INGRESO': 'fecha_ingreso',
    'FECHA INGRESO': 'fecha_ingreso',
    'FECHA_INGRESO': 'fecha_ingreso',
    'FECHA DE INICIO': 'fecha_ingreso',
    'FECHA INICIO': 'fecha_ingreso',
    'FECHA_INICIO': 'fecha_ingreso',
    'FECHA DE INCIO': 'fecha_ingreso',
    'FECHA INCIO': 'fecha_ingreso',
    'FECHA_INCIO': 'fecha_ingreso',
    
    'NOMBRE DE PUESTO': 'puesto_nombre',
    'PUESTO NOMBRE': 'puesto_nombre',
    'PUESTO_NOMBRE': 'puesto_nombre',
    
    'PUESTO': 'puesto',
    'PUESTOS': 'puesto',
    'TIPO DE PUESTO': 'puesto_tipo',
    'TIPO DE PUESTOS': 'puesto_tipo',
    'TIPO PUESTO': 'puesto_tipo',
    'TIPO_PUESTO': 'puesto_tipo',
    'PUESTO TIPO': 'puesto_tipo',
    'PUESTO_TIPO': 'puesto_tipo',
}

# Normalización de clasificación a los valores del modelo
CLASSIF_MAP = {
    'PEQUENO': 'PEQUENO',
    'PEQUEÑO': 'PEQUENO',
    'PEQUENA': 'PEQUENO',
    'PEQUEÑA': 'PEQUENO',
    'MEDIANO': 'MEDIANO',
    'MEDIANA': 'MEDIANO',
    'GRANDE': 'GRANDE',
    'GRAN': 'GRANDE',
    'OFICINA': 'OFICINA',
}


def get_or_create_provincia_token(token):
    if not token:
        return None
    nombre = norm(token)
    if not nombre:
        return None
    prov = Provincia.objects.filter(nombre__iexact=nombre).first()
    if prov:
        return prov
    return Provincia.objects.create(nombre=nombre)


def get_or_create_canton_token(token, provincia_token=None):
    if not token:
        return None
    nombre = norm(token)
    if not nombre:
        return None
    provincia_obj = get_or_create_provincia_token(provincia_token) if provincia_token else None
    qs = Canton.objects.all()
    if provincia_obj:
        qs = qs.filter(provincia=provincia_obj)
    canton = qs.filter(nombre__iexact=nombre).first()
    if canton:
        return canton
    if provincia_obj:
        return Canton.objects.create(nombre=nombre, provincia=provincia_obj)
    return None


def norm(val):
    if val is None:
        return ''
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        return str(val)
    return str(val).strip()


def norm_class(val):
    return CLASSIF_MAP.get(norm(val).upper(), '')


def norm_header_key(val: str) -> str:
    key = norm(val).upper()
    key = key.replace('_', ' ')
    key = ' '.join(key.split())  
    return key


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def importar_clientes(request):
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No se envió archivo'}, status=400)

    try:
        wb = load_workbook(filename=file, read_only=True)
    except Exception as exc:
        return JsonResponse({'error': f'No se pudo abrir el archivo: {exc}'}, status=400)

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return JsonResponse({'error': 'El archivo está vacío'}, status=400)

    header_idx = None
    header_row_num = None
    headers_raw = []
    for ridx, row in enumerate(rows):
        candidate_headers = [norm_header_key(h) for h in row]
        tmp_idx = {HEADER_MAP[h]: i for i, h in enumerate(candidate_headers) if h in HEADER_MAP}
        headers_raw = candidate_headers
        if 'nombre_comercial' in tmp_idx:
            header_idx = tmp_idx
            header_row_num = ridx
            break

    if header_idx is None:
        return JsonResponse({
            'error': 'Falta la columna obligatoria: NOMBRE COMERCIAL',
            'headers_detectados': headers_raw
        }, status=400)

    created_clientes = updated_clientes = 0
    created_inst = updated_inst = 0
    created_puestos = updated_puestos = 0
    errors = []

    start_row = (header_row_num or 0) + 1

    with transaction.atomic():
        for i, row in enumerate(rows[start_row:], start=start_row + 1):
            def col(key):
                idx = header_idx.get(key)
                return norm(row[idx]) if idx is not None and idx < len(row) else ''

            def col_raw(key):
                idx = header_idx.get(key)
                return row[idx] if idx is not None and idx < len(row) else None

            ruc = col('ruc')
            razon_social = col('razon_social')
            nombre_comercial = col('nombre_comercial') or razon_social
            clasif = norm_class(col('clasificacion'))
            inst_nombre = col('instalacion') or 'SIN NOMBRE'
            provincia = col('provincia')
            ciudad = col('ciudad')
            fecha_ingreso = parse_excel_date(col_raw('fecha_ingreso'))
            
            puesto_nombre = col('puesto_nombre') or col('puesto')
            puesto_tipo = col('puesto_tipo') or None

            if not nombre_comercial:
                errors.append(f"Fila {i}: sin nombre_comercial")
                continue

            
            if ruc:
                cliente, created = Cliente.objects.get_or_create(
                    ruc=ruc,
                    defaults={
                        'razon_social': razon_social or nombre_comercial,
                        'nombre_comercial': nombre_comercial,
                        'size': clasif or 'MEDIANO',
                        'fecha_ingreso': fecha_ingreso,
                    },
                )
            else:
                cliente, created = Cliente.objects.get_or_create(
                    nombre_comercial=nombre_comercial,
                    defaults={
                        'razon_social': razon_social or nombre_comercial,
                        'ruc': None,
                        'size': clasif or 'MEDIANO',
                        'fecha_ingreso': fecha_ingreso,
                    },
                )
            if created:
                created_clientes += 1
            else:
                updated = False
                if fecha_ingreso and cliente.fecha_ingreso != fecha_ingreso:
                    cliente.fecha_ingreso = fecha_ingreso
                    updated = True
                if updated:
                    cliente.save(update_fields=['fecha_ingreso'])
                    updated_clientes += 1

            # Instalación por cliente + nombre, resolviendo provincia/cantón
            canton_obj = get_or_create_canton_token(ciudad, provincia)
            instalacion, inst_created = Instalacion.objects.get_or_create(
                cliente=cliente,
                nombre=inst_nombre,
                defaults={'canton': canton_obj} if canton_obj else {},
            )
            if inst_created:
                created_inst += 1

            # Puesto por instalación + nombre
            if puesto_nombre:
                puesto_defaults = {'cantidad_guardias': 1}
                if puesto_tipo:
                    puesto_defaults['tipo'] = puesto_tipo
                puesto, puesto_created = Puesto.objects.get_or_create(
                    instalacion=instalacion,
                    nombre=puesto_nombre,
                    defaults=puesto_defaults,
                )
                if puesto_created:
                    created_puestos += 1

    summary = {
        'clientes_creados': created_clientes,
        'clientes_actualizados': updated_clientes,
        'instalaciones_creadas': created_inst,
        'instalaciones_actualizadas': updated_inst,
        'puestos_creados': created_puestos,
        'puestos_actualizados': updated_puestos,
        'errores': errors,
        'errores_total': len(errors),
    }
    return JsonResponse(summary, status=200)
