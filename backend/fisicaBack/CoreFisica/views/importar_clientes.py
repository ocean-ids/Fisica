from django.http import JsonResponse
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from openpyxl import load_workbook
from ..models import Cliente, Instalacion, Puesto

# Mapear encabezados del Excel a nombres internos
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
    key = ' '.join(key.split())  # colapsar espacios múltiples
    return key


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

            ruc = col('ruc')
            razon_social = col('razon_social')
            nombre_comercial = col('nombre_comercial') or razon_social
            clasif = norm_class(col('clasificacion'))
            inst_nombre = col('instalacion') or 'SIN NOMBRE'
            provincia = col('provincia')
            ciudad = col('ciudad')
            # Preferimos la columna "NOMBRE DE PUESTO" si existe; si no, usamos el respaldo genérico "PUESTO"
            puesto_nombre = col('puesto_nombre') or col('puesto')
            puesto_tipo = col('puesto_tipo') or None

            if not nombre_comercial:
                errors.append(f"Fila {i}: sin nombre_comercial")
                continue

            # Cliente por RUC si hay, si no por nombre_comercial
            if ruc:
                cliente, created = Cliente.objects.get_or_create(
                    ruc=ruc,
                    defaults={
                        'razon_social': razon_social or nombre_comercial,
                        'nombre_comercial': nombre_comercial,
                        'size': clasif or 'MEDIANO',
                    },
                )
            else:
                cliente, created = Cliente.objects.get_or_create(
                    nombre_comercial=nombre_comercial,
                    defaults={
                        'razon_social': razon_social or nombre_comercial,
                        'ruc': None,
                        'size': clasif or 'MEDIANO',
                    },
                )
            if created:
                created_clientes += 1
            else:
                if clasif and cliente.size != clasif:
                    cliente.size = clasif
                    cliente.save(update_fields=['size'])
                    updated_clientes += 1

            # Instalación por cliente + nombre
            inst_defaults = {}
            if provincia:
                inst_defaults['provincia'] = provincia
            if ciudad:
                inst_defaults['ciudad'] = ciudad
            instalacion, inst_created = Instalacion.objects.get_or_create(
                cliente=cliente,
                nombre=inst_nombre,
                defaults=inst_defaults,
            )
            if not inst_created and inst_defaults:
                changed = False
                if provincia and not instalacion.provincia:
                    instalacion.provincia = provincia
                    changed = True
                if ciudad and not instalacion.ciudad:
                    instalacion.ciudad = ciudad
                    changed = True
                if changed:
                    instalacion.save(update_fields=['provincia', 'ciudad'])
                    updated_inst += 1
            elif inst_created:
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
                else:
                    changed = False
                    if puesto_tipo and puesto.tipo != puesto_tipo:
                        puesto.tipo = puesto_tipo
                        changed = True
                    if changed:
                        puesto.save(update_fields=['tipo'])
                        updated_puestos += 1

    summary = {
        'clientes_creados': created_clientes,
        'clientes_actualizados': updated_clientes,
        'instalaciones_creadas': created_inst,
        'instalaciones_actualizadas': updated_inst,
        'puestos_creados': created_puestos,
        'puestos_actualizados': updated_puestos,
        'errores': errors[:10],
        'errores_total': len(errors),
    }
    return JsonResponse(summary, status=200)
