from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError, transaction
from ..models import Persona
import csv
import io
import re
import logging
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_persona(request):
    data = request.data

    cedula = (data.get('cedula') or '').strip()
    if not re.match(r'^\d{1,10}$', cedula):
        return JsonResponse({'error': 'Cédula inválida: sólo dígitos, máximo 10'}, status=400)

    try:
        persona = Persona.objects.create(
            nombres=data.get('nombres'),
            apellidos=data.get('apellidos'),
            cedula=cedula,
            tipo=data.get('tipo'),
        )
        return JsonResponse({'message': 'Persona creada correctamente', 'id': persona.id}, status=201)
    except IntegrityError:
        return JsonResponse({'error': 'Cédula ya registrada'}, status=400)
    except Exception:
        logger.exception('Error creando persona')
        return JsonResponse({'error': 'No se pudo crear persona'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_personas(request):
    try:
        personas = Persona.objects.all().order_by('apellidos')
        # Include is_active so frontend can reflect current activation state
        return JsonResponse(list(personas.values('id', 'nombres', 'apellidos', 'cedula', 'tipo', 'is_active')), safe=False)
    except Exception:
        logger.exception('Error obteniendo personas')
        return JsonResponse({'error': 'No se encontraron personas'}, status=404)
        

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_persona(request, id):
    data = request.data

    try:
        persona = Persona.objects.get(id=id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    persona.nombres = data.get('nombres', persona.nombres)
    persona.apellidos = data.get('apellidos', persona.apellidos)

    cedula_in = data.get('cedula')
    if cedula_in is not None:
        cedula_in = cedula_in.strip()
        if not re.match(r'^\d{1,10}$', cedula_in):
            return JsonResponse({'error': 'Cédula inválida: sólo dígitos, máximo 10'}, status=400)
        persona.cedula = cedula_in

    persona.tipo = data.get('tipo', persona.tipo)

    try:
        persona.save()
        return JsonResponse({'message': 'Persona actualizada correctamente', 'id': persona.id})
    except IntegrityError:
        return JsonResponse({'error': 'Cédula ya registrada'}, status=400)
    except Exception:
        logger.exception('Error actualizando persona id=%s', id)
        return JsonResponse({'error': 'No se pudo actualizar persona'}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_persona(request, id):
    try:
        persona = Persona.objects.get(id=id)
        persona.delete()
        return JsonResponse({'message': 'Persona eliminada correctamente'}, status=200)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)
    except Exception:
        logger.exception('Error eliminando persona id=%s', id)
        return JsonResponse({'error': 'No se pudo eliminar persona'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_persona(request, id):
    try:
        persona = Persona.objects.get(id=id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    if not persona.is_active:
        logger.info('Intento de deshabilitar persona ya inactiva id=%s', id)
        # Idempotent: consider already-disabled as success
        return JsonResponse({'status': 'already_disabled'}, status=200)

    try:
        persona.disable(by_user=request.user if request.user.is_authenticated else None)
        logger.info('Persona deshabilitada id=%s by=%s', id, getattr(request.user, 'username', None))
        return JsonResponse({'status': 'disabled'}, status=200)
    except Exception:
        logger.exception('Error deshabilitando persona id=%s', id)
        return JsonResponse({'error': 'No se pudo deshabilitar persona'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_persona(request, id):
    try:
        persona = Persona.objects.get(id=id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    if persona.is_active:
        logger.info('Intento de habilitar persona ya activa id=%s', id)
        return JsonResponse({'status': 'already_enabled'}, status=200)

    try:
        persona.enable(by_user=request.user if request.user.is_authenticated else None)
        logger.info('Persona habilitada id=%s by=%s', id, getattr(request.user, 'username', None))
        return JsonResponse({'status': 'enabled'}, status=200)
    except Exception:
        logger.exception('Error habilitando persona id=%s', id)
        return JsonResponse({'error': 'No se pudo habilitar persona'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def importar_personas(request):
    """
    Importa personas desde CSV o XLSX.
    Requiere columnas: CEDULA, APELLIDOS, NOMBRES. Opcionales: TIPO, IS_ACTIVE.
    """
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': 'Falta el archivo (campo file)'}, status=400)

    dry_run = str(request.GET.get('dry_run', 'false')).lower() in ['1', 'true', 'yes']
    required_headers = ['CEDULA', 'APELLIDOS', 'NOMBRES']
    allowed_tipos = {choice[0] for choice in Persona.TIPO_CHOICES}

    def normalize_header(value):
        return (str(value).strip().upper()) if value is not None else ''

    def parse_bool(value):
        if value is None or value == '':
            return True
        return str(value).strip().lower() not in ['0', 'false', 'no', 'n']

    filas_raw = []
    ext = upload.name.lower().rsplit('.', 1)[-1] if '.' in upload.name else ''

    if ext in ['csv', 'txt']:
        try:
            raw_data = upload.read().decode('utf-8-sig', errors='ignore')
            if not raw_data.strip():
                return JsonResponse({'error': 'Archivo vacío'}, status=400)
            try:
                dialect = csv.Sniffer().sniff(raw_data[:1024], delimiters=',;\t|')
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(io.StringIO(raw_data), dialect=dialect)
            headers_norm = [normalize_header(h) for h in (reader.fieldnames or [])]
            missing = [h for h in required_headers if h not in headers_norm]
            if missing:
                return JsonResponse({'error': f'Faltan columnas: {", ".join(missing)}'}, status=400)
            header_map = {normalize_header(h): h for h in (reader.fieldnames or [])}
            for idx, row in enumerate(reader, start=2):  # fila 1 = cabecera
                raw_row = {key: row.get(src_key) for key, src_key in header_map.items()}
                if all((val is None or str(val).strip() == '') for val in raw_row.values()):
                    continue
                filas_raw.append((idx, raw_row))
        except Exception:
            logger.exception('Error procesando CSV de personas')
            return JsonResponse({'error': 'No se pudo leer el CSV'}, status=400)

    elif ext in ['xlsx']:
        try:
            wb = load_workbook(upload, read_only=True, data_only=True)
            ws = wb.active
            header_row = [normalize_header(cell.value) for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            missing = [h for h in required_headers if h not in header_row]
            if missing:
                return JsonResponse({'error': f'Faltan columnas: {", ".join(missing)}'}, status=400)
            col_count = len(header_row)
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
                raw_row = {}
                for col_idx in range(col_count):
                    key = header_row[col_idx] if col_idx < len(header_row) else ''
                    if key:
                        raw_row[key] = row[col_idx].value if col_idx < len(row) else None
                if all((val is None or str(val).strip() == '') for val in raw_row.values()):
                    continue
                filas_raw.append((row_idx, raw_row))
        except Exception:
            logger.exception('Error procesando XLSX de personas')
            return JsonResponse({'error': 'No se pudo leer el XLSX'}, status=400)
    else:
        return JsonResponse({'error': 'Formato no soportado. Use CSV o XLSX'}, status=400)

    errores = []
    filas_limpias = []

    for fila_num, raw in filas_raw:
        cedula = str(raw.get('CEDULA') or '').strip()
        apellidos = str(raw.get('APELLIDOS') or '').strip()
        nombres = str(raw.get('NOMBRES') or '').strip()
        tipo = str(raw.get('TIPO') or 'FIJOS').strip().upper()
        is_active = parse_bool(raw.get('IS_ACTIVE'))

        if not cedula:
            errores.append({'fila': fila_num, 'error': 'CEDULA vacía'})
            continue
        if not re.match(r'^\d{1,10}$', cedula):
            errores.append({'fila': fila_num, 'error': 'CEDULA inválida: sólo dígitos, máximo 10'})
            continue
        if not apellidos:
            errores.append({'fila': fila_num, 'error': 'APELLIDOS vacíos'})
            continue
        if not nombres:
            errores.append({'fila': fila_num, 'error': 'NOMBRES vacíos'})
            continue
        if tipo and tipo not in allowed_tipos:
            errores.append({'fila': fila_num, 'error': f'TIPO inválido: {tipo}'})
            continue

        filas_limpias.append({
            'fila': fila_num,
            'cedula': cedula,
            'apellidos': apellidos,
            'nombres': nombres,
            'tipo': tipo or None,
            'is_active': bool(is_active),
        })

    resumen = {
        'total_filas': len(filas_raw),
        'filas_validas': len(filas_limpias),
        'creadas': 0,
        'actualizadas': 0,
        'errores': errores,
    }

    if dry_run:
        resumen['mensaje'] = 'Validación realizada (dry_run)'
        return JsonResponse(resumen, status=200)

    if not filas_limpias:
        return JsonResponse({'error': 'No hay filas válidas para importar', 'detalles': errores}, status=400)

    try:
        with transaction.atomic():
            cedulas = [f['cedula'] for f in filas_limpias]
            existentes = {p.cedula: p for p in Persona.objects.filter(cedula__in=cedulas)}

            for fila in filas_limpias:
                persona = existentes.get(fila['cedula'])
                if persona:
                    persona.nombres = fila['nombres']
                    persona.apellidos = fila['apellidos']
                    persona.tipo = fila['tipo']
                    persona.is_active = fila['is_active']
                    persona.save(update_fields=['nombres', 'apellidos', 'tipo', 'is_active'])
                    resumen['actualizadas'] += 1
                else:
                    Persona.objects.create(
                        nombres=fila['nombres'],
                        apellidos=fila['apellidos'],
                        cedula=fila['cedula'],
                        tipo=fila['tipo'],
                        is_active=fila['is_active'],
                    )
                    resumen['creadas'] += 1
        resumen['mensaje'] = 'Importación completada'
        return JsonResponse(resumen, status=200)
    except IntegrityError as exc:
        logger.exception('Error de integridad importando personas')
        return JsonResponse({'error': 'Conflicto de integridad', 'detalle': str(exc)}, status=400)
    except Exception:
        logger.exception('Error importando personas')
        return JsonResponse({'error': 'No se pudo importar personas'}, status=500)