from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError, transaction
from django.db.models import Q
from ..models import Persona, AsignacionSemanal, Puesto, Asignacion, Horario, Provincia, Canton, CoberturaSacafranco
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Border, Side, Alignment, Font, PatternFill
import csv
import io
import re
import logging
import datetime

logger = logging.getLogger(__name__)

DAY_KEYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


def _normalize_day(tok):
    t = str(tok or '').strip().lower()
    mapping = {
        'l': 'mon', 'lu': 'mon', 'lun': 'mon', 'lunes': 'mon',
        'm': 'tue', 'ma': 'tue', 'mar': 'tue', 'martes': 'tue',
        'mi': 'wed', 'mie': 'wed', 'mié': 'wed', 'mier': 'wed', 'miercoles': 'wed', 'miércoles': 'wed',
        'j': 'thu', 'ju': 'thu', 'jue': 'thu', 'jueves': 'thu',
        'v': 'fri', 'vi': 'fri', 'vie': 'fri', 'viernes': 'fri',
        's': 'sat', 'sa': 'sat', 'sab': 'sat', 'sabado': 'sat', 'sábado': 'sat',
        'd': 'sun', 'do': 'sun', 'dom': 'sun', 'domingo': 'sun'
    }
    if t in DAY_KEYS:
        return t
    return mapping.get(t, '')


def _iter_future_week_starts(start_date, years=5):
    weeks = []
    year_cursor = start_date.year
    month_cursor = start_date.month
    end_year = start_date.year + years
    while (year_cursor < end_year) or (year_cursor == end_year and month_cursor <= 12):
        base = datetime.date(year_cursor, month_cursor, 1)
        cursor = base
        while cursor.month == month_cursor:
            if cursor >= start_date:
                weeks.append(cursor)
            cursor += datetime.timedelta(days=7)
        month_cursor += 1
        if month_cursor > 12:
            month_cursor = 1
            year_cursor += 1
    return weeks


def _get_or_create_sacafranco_marker_row(puesto, week_start):
    semanal = AsignacionSemanal.objects.filter(
        puesto=puesto,
        week_start=week_start,
        asignacion__isnull=True,
    ).order_by('id').first()
    if semanal:
        return semanal
    return AsignacionSemanal.objects.create(puesto=puesto, week_start=week_start)


def _marker_value_allows_sacafranco(semanal, day):
    value = str(getattr(semanal, day, '') or '').strip()
    return value == '' or value.upper().startswith('F'), value


def _assign_sacafranco_without_asignacion(persona, puesto, week_start_date, day):
    prop_start = week_start_date

    existing_slot = CoberturaSacafranco.objects.filter(
        puesto=puesto,
        week_start=week_start_date,
        day=day,
    ).first()
    if existing_slot and existing_slot.persona_id != persona.id:
        return JsonResponse({'error': 'Ese puesto ya tiene un sacafranco asignado para esa fecha'}, status=400)

    existing_person = CoberturaSacafranco.objects.filter(
        persona=persona,
        week_start=week_start_date,
        day=day,
    ).exclude(puesto=puesto).first()
    if existing_person:
        return JsonResponse({'error': 'La persona ya está asignada a otro puesto en esa fecha'}, status=400)

    with transaction.atomic():
        weeks = _iter_future_week_starts(prop_start)
        selected_semanal = AsignacionSemanal.objects.filter(
            puesto=puesto,
            week_start=week_start_date,
        ).order_by('id').first()

        for ws in weeks:
            slot_conflict = CoberturaSacafranco.objects.filter(
                puesto=puesto,
                week_start=ws,
                day=day,
            ).exclude(persona=persona).exists()
            if slot_conflict:
                continue

            person_conflict = CoberturaSacafranco.objects.filter(
                persona=persona,
                week_start=ws,
                day=day,
            ).exclude(puesto=puesto).exists()
            if person_conflict:
                continue

            CoberturaSacafranco.objects.get_or_create(
                persona=persona,
                puesto=puesto,
                week_start=ws,
                day=day,
            )

            if ws == week_start_date:
                selected_semanal = AsignacionSemanal.objects.filter(
                    puesto=puesto,
                    week_start=ws,
                ).order_by('id').first() or selected_semanal

        if selected_semanal is None:
            CoberturaSacafranco.objects.get_or_create(
                persona=persona,
                puesto=puesto,
                week_start=week_start_date,
                day=day,
            )
            selected_semanal = AsignacionSemanal.objects.filter(
                puesto=puesto,
                week_start=week_start_date,
            ).order_by('id').first()

    return JsonResponse({'status': 'assigned', 'semanal_id': selected_semanal.id})


def _clear_sacafranco_marker_if_unused(puesto, week_start, day):
    if CoberturaSacafranco.objects.filter(puesto=puesto, week_start=week_start, day=day).exists():
        return None

    semanal = AsignacionSemanal.objects.filter(
        puesto=puesto,
        week_start=week_start,
        asignacion__isnull=True,
        **{f'{day}__istartswith': 'F'}
    ).order_by('id').first()
    if not semanal:
        return None

    setattr(semanal, day, '')
    semanal.save()
    return semanal


def _desasignar_sacafranco_without_asignacion(persona, puesto, week_start_date, day):
    day_offsets = {
        'mon': 0,
        'tue': 1,
        'wed': 2,
        'thu': 3,
        'fri': 4,
        'sat': 5,
        'sun': 6,
    }
    day_offset = day_offsets.get(day, 0)
    today = datetime.date.today()
    selected_cell_date = week_start_date + datetime.timedelta(days=day_offset)
    cutoff_date = today if today > selected_cell_date else selected_cell_date
    prop_end = datetime.date(week_start_date.year, 12, 31)

    candidates = CoberturaSacafranco.objects.filter(
        persona=persona,
        puesto=puesto,
        day=day,
        week_start__gte=week_start_date,
        week_start__lte=prop_end,
    ).order_by('week_start')

    delete_ids = []
    affected_weeks = []
    for cobertura in candidates:
        row_day_date = cobertura.week_start + datetime.timedelta(days=day_offset)
        if row_day_date < cutoff_date:
            continue
        delete_ids.append(cobertura.id)
        affected_weeks.append(cobertura.week_start)

    if not delete_ids:
        return None

    with transaction.atomic():
        CoberturaSacafranco.objects.filter(id__in=delete_ids).delete()
        semanal = None
        for ws in affected_weeks:
            cleared = _clear_sacafranco_marker_if_unused(puesto, ws, day)
            if ws == week_start_date:
                semanal = cleared

    return JsonResponse({'status': 'unassigned', 'semanal_id': getattr(semanal, 'id', None)})


def _resolve_provincia_id(token):
    if token is None or token == '':
        return None
    try:
        return int(token)
    except (TypeError, ValueError):
        pass
    try:
        prov = Provincia.objects.filter(nombre__iexact=str(token).strip()).first()
        return prov.id if prov else None
    except Exception:
        return None


def _resolve_canton_id(token, provincia_id=None):
    if token is None or token == '':
        return None
    try:
        return int(token)
    except (TypeError, ValueError):
        pass
    try:
        qs = Canton.objects.all()
        if provincia_id:
            qs = qs.filter(provincia_id=provincia_id)
        canton = qs.filter(nombre__iexact=str(token).strip()).first()
        return canton.id if canton else None
    except Exception:
        return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_persona(request):
    if not request.user.has_perm('CoreFisica.add_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    # variable data para recibir los datos de request.data, se asigna a data para evitar modificar request.data directamente
    data = request.data

    #cedula es obligatoria, se valida que exista, no esté vacía, tenga solo dígitos y máximo 10 caracteres
    cedula = (data.get('cedula') or '').strip()
    if not cedula:
        return JsonResponse({'error': 'Cédula es obligatoria'}, status=400)
    if not re.match(r'^\d{1,10}$', cedula):
        return JsonResponse({'error': 'Cédula inválida: sólo dígitos, máximo 10'}, status=400)

    #nombres y apellidos se normalizan a mayuscula y se quitan espacios al inicio y final
    nombres = str(data.get('nombres') or '').strip().upper()
    apellidos = str(data.get('apellidos') or '').strip().upper()

    
    provincia_token = data.get('provincia') or data.get('provincia_id')
    provincia_id = _resolve_provincia_id(provincia_token)
    canton_token = data.get('canton') or data.get('canton_id')
    canton_id = _resolve_canton_id(canton_token, provincia_id)

    try:
        persona = Persona.objects.create(
            nombres=nombres,
            apellidos=apellidos,
            cedula=cedula,
            tipo=data.get('tipo'),
            provincia_id=provincia_id,
            canton_id=canton_id,
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
    # si el ususario tiene permiso de ver personas, se obtiene el parametro de busqueda q y tipo para filtrar por tipo de persona (empleado, cliente, etc)
    if not request.user.has_perm('CoreFisica.view_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        q = (request.GET.get('q') or '').strip()
        tipo = (request.GET.get('tipo') or '').strip()

        # la variable persona se asigna a la consulta de todas las personas, luego se filtra por q si existe, buscando coincidencias en nombres, apellidos o cedula, y por tipo si se especifica. Finalmente se ordena por apellidos
        personas = Persona.objects.all()
        if q:
            personas = personas.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(cedula__icontains=q)
            )

        if tipo:
            personas = personas.filter(tipo=tipo)

        personas = personas.select_related('provincia', 'canton').order_by('apellidos')

        data = []
        for p in personas:
            data.append({
                'id': p.id,
                'nombres': p.nombres,
                'apellidos': p.apellidos,
                'cedula': p.cedula,
                'tipo': p.tipo,
                'is_active': p.is_active,
                'provincia': p.provincia_id,
                'canton': p.canton_id,
                'provincia_nombre': getattr(p.provincia, 'nombre', None),
                'canton_nombre': getattr(p.canton, 'nombre', None),
            })

        return JsonResponse(data, safe=False)
    except Exception:
        logger.exception('Error obteniendo personas')
        return JsonResponse({'error': 'No se encontraron personas'}, status=404)
        

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_persona(request, id):
    if not request.user.has_perm('CoreFisica.change_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    data = request.data

    try:
        persona = Persona.objects.get(id=id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    # si el request.data contiene los campos nombres o apellidos, se actualizan normalizando a mayuscula y quitando espacios al inicio y final. Si contiene cedula, se valida que no esté vacía, tenga solo dígitos y máximo 10 caracteres antes de actualizarla. El campo tipo se actualiza si está presente en el request.data, de lo contrario se mantiene el valor actual
    if 'nombres' in data:
        nombres = data.get('nombres')
        persona.nombres = str(nombres or '').strip().upper()
    if 'apellidos' in data:
        apellidos = data.get('apellidos')
        persona.apellidos = str(apellidos or '').strip().upper()

    # si se proporciona una nueva cedula, se valida que no este vacia, tenga solo dígitos y máximo 10 caracteres antes de actualizarla. Si la cedula es inválida, se retorna un error. Si es válida, se actualiza la cedula de la persona
    cedula_in = data.get('cedula')
    if cedula_in is not None:
        cedula_in = cedula_in.strip()
        if not cedula_in:
            return JsonResponse({'error': 'Cédula es obligatoria'}, status=400)
        if not re.match(r'^\d{1,10}$', cedula_in):
            return JsonResponse({'error': 'Cédula inválida: sólo dígitos, máximo 10'}, status=400)
        persona.cedula = cedula_in

    # persona.tipo se actualiza si el campo tipo está presente en el request.data, de lo contrario se mantiene el valor actual. Esto permite actualizar el tipo de persona (empleado, cliente, etc) si se proporciona en la solicitud, sin requerir que siempre esté presente
    persona.tipo = data.get('tipo', persona.tipo)

    if 'provincia' in data or 'provincia_id' in data:
        provincia_token = data.get('provincia') if 'provincia' in data else data.get('provincia_id')
        persona.provincia_id = _resolve_provincia_id(provincia_token)

    if 'canton' in data or 'canton_id' in data:
        canton_token = data.get('canton') if 'canton' in data else data.get('canton_id')
        persona.canton_id = _resolve_canton_id(canton_token, persona.provincia_id)

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
    # si solo el usuario tiene permiso de eliminar persona, se intenta obtener la persona por id, si no existe se retorna un error 404, si existe se elimina y se retorna un mensaje de éxito. Si ocurre cualquier otro error, se registra en el log y se retorna un error 500
    if not request.user.has_perm('CoreFisica.delete_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    # se intenta obtener la persona por id, si no existe se retorna un error 404, si existe se elimina y se retorna un mensaje de éxito. Si ocurre cualquier otro error, se registra en el log y se retorna un error 500
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
    # si el usuario no tiene permiso de cambiar persona, se retorna un error 403. Si tiene permiso, se intenta obtener la persona por id, si no existe se retorna un error 404. Si la persona ya está inactiva, se registra un intento de deshabilitar una persona ya inactiva en el log y se retorna un estado indicando que ya estaba deshabilitada. Si la persona está activa, se llama al método disable() de la persona, pasando el usuario que realiza la acción para registrar quién hizo el cambio. Si la deshabilitación es exitosa, se registra en el log y se retorna un estado indicando que fue deshabilitada. Si ocurre cualquier error durante el proceso, se registra en el log y se retorna un error 500
    if not request.user.has_perm('CoreFisica.change_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        persona = Persona.objects.get(id=id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    # si la persona no está activa, se registra un intento de deshabilitar una persona ya inactiva en el log y se retorna un estado indicando que ya estaba deshabilitada. Esto evita realizar operaciones innecesarias y proporciona información útil para auditoría
    if not persona.is_active:
        logger.info('Intento de deshabilitar persona ya inactiva id=%s', id)
        
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
    # si el usuario no tiene permiso de cambiar persona, se retorna un error 403. Si tiene permiso, se intenta obtener la persona por id, si no existe se retorna un error 404. Si la persona ya está activa, se registra un intento de habilitar una persona ya activa en el log y se retorna un estado indicando que ya estaba habilitada. Si la persona está inactiva, se llama al método enable() de la persona, pasando el usuario que realiza la acción para registrar quién hizo el cambio. Si la habilitación es exitosa, se registra en el log y se retorna un estado indicando que fue habilitada. Si ocurre cualquier error durante el proceso, se registra en el log y se retorna un error 500
    if not  request.user.has_perm('CoreFisica.change_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    try:
        persona = Persona.objects.get(id=id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    # si la persona ya esta activa, se re|gistra un intento de habilitar una persona ya activa en el log y se retorna un estado indicando que ya estaba habilitada. Esto evita realizar operaciones innecesarias y proporciona información útil para auditoría
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

    #Importa personas desde CSV o XLSX.
    # Requiere columnas: CEDULA, APELLIDOS, NOMBRES. Opcionales: TIPO, IS_ACTIVE.
    if not request.user.has_perm('CoreFisica.change_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': 'Falta el archivo (campo file)'}, status=400)

    # El parámetro dry_run permite validar el archivo sin realizar cambios en la base de datos. Si dry_run es true, se procesará el archivo y se devolverá un resumen de validación sin crear ni actualizar registros. Esto es útil para verificar que el formato y los datos del archivo son correctos antes de hacer la importación real.
    dry_run = str(request.GET.get('dry_run', 'false')).lower() in ['1', 'true', 'yes']
    fullname_headers = ['APELLIDOS Y NOMBRES', 'APELLIDOS Y NOMBRE', 'NOMBRES Y APELLIDOS']
    allowed_tipos = {choice[0] for choice in Persona.TIPO_CHOICES}

    # Función para normalizar encabezados, convirtiendo a mayúsculas, quitando espacios y acentos para facilitar la detección de columnas relevantes sin importar variaciones comunes en los nombres de las columnas.
    def normalize_header(value):
        if value is None:
            return ''
        import unicodedata
        text = str(value).strip().upper()
        # quitar acentos/diacríticos
        text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        return text

    # Función para normalizar cédula, eliminando espacios y guiones, validando que solo contenga dígitos y ajustando a formato de 10 dígitos si es necesario. Retorna la cédula normalizada o None si es inválida.
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

    # funcion para parsear valores booleanos, interpretando varias formas comunes de representar falso (0, false, no, n) y considerando vacío o None como verdadero por defecto. Esto permite flexibilidad en cómo se indican los valores booleanos en el archivo de importación.
    def parse_bool(value):
        if value is None or value == '':
            return True
        return str(value).strip().lower() not in ['0', 'false', 'no', 'n']

    # funcion para dividir un nombre completo en apellidos y nombres, utilizando heurísticas para manejar casos comunes. Si el nombre completo tiene una sola palabra, se asume que son nombres sin apellidos. Si tiene dos palabras, se asigna la primera a apellidos y la segunda a nombres. Si tiene más de dos palabras, se asume que las dos primeras son apellidos y el resto son nombres. Esto permite procesar columnas combinadas de nombre completo sin requerir un formato específico.
    def split_full_name(raw: str):
        parts = [p for p in str(raw or '').strip().split() if p]
        if not parts:
            return '', ''
        if len(parts) == 1:
            return '', parts[0]
        if len(parts) == 2:
            return parts[0], parts[1]
        # Heurística: dos primeras palabras como apellidos, resto como nombres
        return ' '.join(parts[:2]), ' '.join(parts[2:])

    filas_raw = []
    has_fullname_header = False
    ext = upload.name.lower().rsplit('.', 1)[-1] if '.' in upload.name else ''

    # Procesar CSV o XLSX, detectando la fila de encabezado que contenga las columnas requeridas (CEDULA y APELLIDOS/NOMBRES o columna combinada), y extrayendo los datos en un formato intermedio sin validar aún. Esto permite manejar archivos con formatos variados y detectar correctamente las columnas relevantes para la importación.
    if ext in ['csv', 'txt']:
        try:
            raw_data = upload.read().decode('utf-8-sig', errors='ignore')
            if not raw_data.strip():
                return JsonResponse({'error': 'Archivo vacío'}, status=400)
            try:
                dialect = csv.Sniffer().sniff(raw_data[:1024], delimiters=',;\t|')
            except csv.Error:
                dialect = csv.excel
            reader_rows = list(csv.reader(io.StringIO(raw_data), dialect=dialect))
            header_idx = None
            header_norm = []
            for i, row in enumerate(reader_rows[:15]):  # busca cabecera en primeras filas
                norm = [normalize_header(c) for c in row]
                has_cedula = 'CEDULA' in norm
                has_fullname_header = any(h in fullname_headers for h in norm)
                has_apellidos = 'APELLIDOS' in norm
                has_nombres = 'NOMBRES' in norm
                if has_cedula and ((has_apellidos and has_nombres) or has_fullname_header):
                    header_idx = i
                    header_norm = norm
                    break
            if header_idx is None:
                return JsonResponse({'error': 'Faltan columnas: CEDULA y APELLIDOS/NOMBRES'}, status=400)
            header_map_idx = {h: idx for idx, h in enumerate(header_norm)}
            for idx, row in enumerate(reader_rows[header_idx+1:], start=header_idx+2):
                raw_row = {}
                for key in header_map_idx:
                    pos = header_map_idx[key]
                    raw_row[key] = row[pos] if pos < len(row) else None
                if all((val is None or str(val).strip() == '') for val in raw_row.values()):
                    continue
                filas_raw.append({
                    'fila': idx,
                    'raw': raw_row,
                    'has_fullname_header': has_fullname_header,
                    'hoja': None,
                })
        except Exception:
            logger.exception('Error procesando CSV de personas')
            return JsonResponse({'error': 'No se pudo leer el CSV'}, status=400)

    elif ext in ['xlsx']:
        try:
            wb = load_workbook(upload, read_only=True, data_only=True)
            any_sheet = False
            for ws in wb.worksheets:
                header_row = None
                header_idx = None
                sheet_has_fullname_header = False
                for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20)), start=1):
                    norm = [normalize_header(cell.value) for cell in row]
                    has_cedula = 'CEDULA' in norm
                    sheet_has_fullname_header = any(h in fullname_headers for h in norm)
                    has_apellidos = 'APELLIDOS' in norm
                    has_nombres = 'NOMBRES' in norm
                    if has_cedula and ((has_apellidos and has_nombres) or sheet_has_fullname_header):
                        header_row = norm
                        header_idx = r_idx
                        break
                if header_row is None:
                    continue
                any_sheet = True
                header_map_idx = {h: idx for idx, h in enumerate(header_row)}
                for row_idx, row in enumerate(ws.iter_rows(min_row=header_idx + 1, max_row=ws.max_row), start=header_idx + 1):
                    raw_row = {}
                    for key in header_map_idx:
                        pos = header_map_idx[key]
                        raw_row[key] = row[pos].value if pos < len(row) else None
                    if all((val is None or str(val).strip() == '') for val in raw_row.values()):
                        continue
                    filas_raw.append({
                        'fila': row_idx,
                        'raw': raw_row,
                        'has_fullname_header': sheet_has_fullname_header,
                        'hoja': ws.title,
                    })
            if not any_sheet:
                return JsonResponse({'error': 'No se encontraron hojas con columnas: CEDULA y APELLIDOS/NOMBRES'}, status=400)
        except Exception:
            logger.exception('Error procesando XLSX de personas')
            return JsonResponse({'error': 'No se pudo leer el XLSX'}, status=400)
    else:
        return JsonResponse({'error': 'Formato no soportado. Use CSV o XLSX'}, status=400)

    errores = []
    filas_limpias = []

    for item in filas_raw:
        fila_num = item['fila']
        raw = item['raw']
        fila_hoja = item.get('hoja')
        row_has_fullname = item.get('has_fullname_header', False)
        cedula = normalize_cedula(raw.get('CEDULA'))
        tipo = str(raw.get('TIPO') or '').strip().upper()
        if not tipo:
            tipo = None
        is_active = parse_bool(raw.get('IS_ACTIVE'))

        # obtener apellidos/nombres, permitiendo columna combinada
        apellidos = str(raw.get('APELLIDOS') or '').strip()
        nombres = str(raw.get('NOMBRES') or '').strip()
        if not (apellidos and nombres) and row_has_fullname:
            # buscar la primera columna fullname presente
            fullname_val = None
            for key in raw.keys():
                if normalize_header(key) in fullname_headers:
                    fullname_val = raw.get(key)
                    break
            a_split, n_split = split_full_name(fullname_val)
            if not apellidos:
                apellidos = a_split
            if not nombres:
                nombres = n_split

        #Validaciones: cedula no vacia, solo dgitos, maximo 10 caracteres, apellidos y nombres no vacios, tipo valido si se proporciona. Se acumulan errores para cada fila sin detener el proceso, permitiendo reportar múltiples problemas en un solo intento de importación.
        if cedula is None:
            errores.append({'fila': fila_num, 'hoja': fila_hoja, 'error': 'CEDULA invalida: solo digitos'})
            continue
        if not cedula:
            errores.append({'fila': fila_num, 'hoja': fila_hoja, 'error': 'CEDULA vacia'})
            continue
        if not re.match(r'^\d{1,10}$', cedula):
            errores.append({'fila': fila_num, 'hoja': fila_hoja, 'error': 'CEDULA invalida: solo digitos, maximo 10'})
            continue
        if not apellidos:
            errores.append({'fila': fila_num, 'hoja': fila_hoja, 'error': 'APELLIDOS vacios'})
            continue
        if not nombres:
            errores.append({'fila': fila_num, 'hoja': fila_hoja, 'error': 'NOMBRES vacios'})
            continue
        if tipo and tipo not in allowed_tipos:
            errores.append({'fila': fila_num, 'hoja': fila_hoja, 'error': f'TIPO invalido: {tipo}'})
            continue
        
        # Si la fila es válida, se agrega a filas_limpias para su posterior procesamiento. Esto permite separar claramente las filas que tienen problemas de formato o datos inválidos de aquellas que están listas para ser importadas, facilitando la gestión de errores y la importación efectiva.
        filas_limpias.append({
            'fila': fila_num,
            'hoja': fila_hoja,
            'cedula': cedula,
            'apellidos': apellidos,
            'nombres': nombres,
            'tipo': tipo or None,
            'is_active': bool(is_active),
        })
    # Se construye un resumen del proceso de validación, incluyendo el total de filas procesadas, cuántas son válidas, cuántas se crearían o actualizarían (inicialmente 0 en este caso) y los errores encontrados. Este resumen se devuelve al cliente para proporcionar retroalimentación sobre el resultado de la validación, especialmente útil cuando se utiliza el modo dry_run para verificar el archivo sin realizar cambios en la base de datos.
    resumen = {
        'total_filas': len(filas_raw),
        'filas_validas': len(filas_limpias),
        'creadas': 0,
        'actualizadas': 0,
        'errores': errores,
    }

    # Si dry_run es true, se devuelve el resumen de validación sin realizar la importación real. Esto permite al usuario verificar que el archivo tiene el formato correcto y que los datos son válidos antes de proceder con la importación, evitando cambios no deseados en la base de datos.
    if dry_run:
        resumen['mensaje'] = 'Validación realizada (dry_run)'
        return JsonResponse(resumen, status=200)
    
    # si no hay filas válidas para importar, se devuelve un error con el resumen de errores encontrados. Esto evita intentar realizar una importación cuando no hay datos correctos, proporcionando retroalimentación clara sobre los problemas que deben corregirse en el archivo antes de intentar importar nuevamente.
    if not filas_limpias:
        return JsonResponse({'error': 'No hay filas válidas para importar', 'detalles': errores}, status=400)
    # Importar filas válidas, evitando duplicados tanto en el archivo como con registros existentes en la base de datos
    try:
        with transaction.atomic():
            cedulas = [f['cedula'] for f in filas_limpias]
            cedula_candidates = set(cedulas)
            for c in cedulas:
                if len(c) == 10 and c.startswith('0'):
                    cedula_candidates.add(c.lstrip('0') or c)
                elif len(c) == 9:
                    cedula_candidates.add(f"0{c}")
            existentes = {}
            for p in Persona.objects.filter(cedula__in=list(cedula_candidates)):
                norm = normalize_cedula(p.cedula)
                if norm:
                    existentes[norm] = p
            procesadas = set(existentes.keys())

            for fila in filas_limpias:
                cedula = fila['cedula']
                if cedula in procesadas:
                    # Evitar duplicados en el mismo archivo y existentes en BD.
                    continue
                Persona.objects.create(
                    nombres=fila['nombres'],
                    apellidos=fila['apellidos'],
                    cedula=cedula,
                    tipo=fila['tipo'],
                    is_active=fila['is_active'],
                )
                resumen['creadas'] += 1
                procesadas.add(cedula)
        resumen['mensaje'] = 'Importación completada'
        return JsonResponse(resumen, status=200)
    except IntegrityError as exc:
        logger.exception('Error de integridad importando personas')
        return JsonResponse({'error': 'Conflicto de integridad', 'detalle': str(exc)}, status=400)
    except Exception:
        logger.exception('Error importando personas')
        return JsonResponse({'error': 'No se pudo importar personas'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_personas_excel(request):
    # si el usuario no tiene permiso de ver personas, se retorna un error 403. Si tiene permiso, se obtienen los parámetros de búsqueda q y tipo para filtrar las personas. Solo se exportan personas activas para evitar confusión, pero se pueden ajustar filtros según necesidad. Se crea un archivo Excel con los datos de las personas filtradas, aplicando formato a las celdas para mejorar la legibilidad. Finalmente, se devuelve el archivo Excel como una respuesta de descarga al cliente.
    if not request.user.has_perm('CoreFisica.view_persona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    # Obtener parámetros de búsqueda y strip para eliminar espacios al inicio y final. Esto permite filtrar las personas por cédula, nombres o apellidos (q) y por tipo de persona (tipo) antes de generar el archivo Excel, proporcionando una exportación más relevante según los criterios especificados por el usuario.
    q = (request.GET.get('q') or '').strip()
    tipo = (request.GET.get('tipo') or '').strip()

    # Solo exportamos personas activas para evitar confusión, pero se pueden ajustar filtros según necesidad
    personas = Persona.objects.filter(is_active=True)

    # Si se proporciona un parámetro de búsqueda q, se filtran las personas buscando coincidencias en los campos nombres, apellidos o cedula utilizando una consulta Q para combinar las condiciones. Si se especifica un tipo, se filtran las personas por ese tipo. Finalmente, se ordenan las personas por apellidos y nombres para una presentación más organizada en el archivo Excel.
    if q:
        personas = personas.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(cedula__icontains=q)
        )
    
    # si tipo no esta vacio se filtra por tipo
    if tipo:
        personas = personas.filter(tipo=tipo)

    # variable personas se ordena por apellidos y nombres en el excel
    personas = personas.order_by('apellidos', 'nombres')
    
    # wb es un objeto Workbook de openpyxl que representa el archivo Excel que se va a generar
    wb = Workbook()
    # wb.active obtiene la hoja activa del libro de Excel, que es donde se escribirán los datos de las personas. Se asigna a la variable ws para facilitar su manipulación. Luego se establece el título de la hoja como "Personas" para identificar claramente el contenido del archivo.
    ws = wb.active
    # ws.title establece el título de la hoja activa a "Personas", lo que ayuda a identificar el contenido del archivo Excel. Luego, se agregan los encabezados de las columnas (CEDULA, APELLIDOS, NOMBRES, TIPO) como la primera fila de la hoja utilizando ws.append(). Esto proporciona una estructura clara para los datos que se agregarán a continuación.
    ws.title = "Personas"
    #ws.append agrega los encabezados de las columnas al archivo Excel, definiendo claramente qué información se encuentra en cada columna. Esto es importante para la legibilidad del archivo y para que los usuarios puedan entender fácilmente los datos que se presentan. Los encabezados son: CEDULA, APELLIDOS, NOMBRES y TIPO, que corresponden a los campos principales de la entidad Persona.
    ws.append(['CEDULA', 'APELLIDOS', 'NOMBRES', 'TIPO'])

    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 15

    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="F1F3F5", end_color="F1F3F5", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    thin = Side(border_style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for p in personas:
        ws.append([p.cedula, p.apellidos, p.nombres, p.tipo])

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=4):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    resp = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    resp['Content-Disposition'] = 'attachment; filename=personal.xlsx'
    return resp

class SacafrancoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm('CoreFisica.view_persona'):
            return JsonResponse({'error': 'No autorizado'}, status=403)

        week_start = request.query_params.get('week_start')
        day = request.query_params.get('day')
        puesto_id = request.query_params.get('puesto_id')
        week_start_date = None

        if day:
            day_norm = _normalize_day(day)
            if not day_norm:
                return Response({'error': 'Día inválido'}, status=400)
            day = day_norm

        if week_start:
            try:
                week_start_date = datetime.date.fromisoformat(str(week_start))
            except Exception:
                return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=400)

        qs = Persona.objects.filter(tipo='SACAFRANCO', is_active=True).order_by('nombres', 'apellidos')
        results = []
        for p in qs:
            occupied = False
            if week_start_date and day:
                any_f = Q()
                for key in DAY_KEYS:
                    any_f |= Q(**{f"{key}__istartswith": 'F'})

                if CoberturaSacafranco.objects.filter(
                    persona=p,
                    week_start=week_start_date,
                ).exists():
                    occupied = True
                elif CoberturaSacafranco.objects.filter(
                    persona=p,
                    week_start__gte=week_start_date,
                    day=day,
                ).exists():
                    occupied = True
                elif AsignacionSemanal.objects.filter(
                    asignacion__persona=p,
                    week_start=week_start_date,
                ).filter(any_f).exists():
                    occupied = True
                elif AsignacionSemanal.objects.filter(
                    asignacion__persona=p,
                    week_start__gte=week_start_date,
                    **{f"{day}__istartswith": 'F'}
                ).exists():
                    occupied = True
            assigned_for_puesto = None
            if puesto_id and week_start_date and day:
                assigned = CoberturaSacafranco.objects.filter(
                    puesto_id=puesto_id,
                    week_start=week_start_date,
                    day=day,
                    persona=p,
                ).first()
                if assigned or AsignacionSemanal.objects.filter(puesto_id=puesto_id, week_start=week_start_date, asignacion__persona=p, **{f"{day}__istartswith": 'F'}).exists():
                    assigned_for_puesto = p.id

            results.append({
                'id': p.id,
                'nombres': p.nombres,
                'apellidos': p.apellidos,
                'cedula': p.cedula,
                'status': 'asignado' if (assigned_for_puesto or occupied) else 'available',
                'assigned_for_puesto': assigned_for_puesto,
            })

        return Response(results)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_sacafranco(request):
    # si el ususario no tiene permiso de cambiar asignacionsemanal, se retorna un error 403. Si tiene permiso, se obtienen los parámetros necesarios del request.data para realizar la asignación de sacafranco a una persona en un puesto específico para una semana y día determinados. Se valida que todos los parámetros requeridos estén presentes y que el día sea válido. Luego se intenta obtener la persona y el puesto por sus IDs, retornando errores 404 si no se encuentran. Se determina el mes y año de referencia a partir de week_start para mantener la unicidad de asignación por persona/mes/año. Si no existe una asignación para esa persona/mes/año, se crea una nueva asignación con el contexto del puesto actual. Si ya existe una asignación, se sincroniza su contexto con el puesto actual si es necesario. Finalmente, se propaga la asignación a semanas futuras a partir de la semana indicada, sin tocar semanas pasadas ni sobrescribir códigos existentes.
    if not request.user.has_perm('CoreFisica.change_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    data = request.data
    persona_id = data.get('persona_id')
    puesto_id = data.get('puesto_id')
    week_start = data.get('week_start')
    day = data.get('day')
   

    if not all([persona_id, puesto_id, week_start, day]):
        return JsonResponse({'error': 'Faltan parámetros requeridos'}, status=400)

    # Normalizar día a las claves del modelo (mon..sun)
    day_norm = _normalize_day(day)
    if not day_norm:
        return JsonResponse({'error': 'Día inválido'}, status=400)
    day = day_norm

    try:
        persona = Persona.objects.get(id=persona_id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    try:
        puesto = Puesto.objects.get(id=puesto_id)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)

    # Determinar mes/año desde week_start (respeta unicidad persona/mes/anio)
    try:
        if isinstance(week_start, str):
            week_start_date = datetime.date.fromisoformat(week_start)
        else:
            week_start_date = week_start if isinstance(week_start, datetime.date) else datetime.date.today()
    except Exception:
        week_start_date = datetime.date.today()

    mes_ref = week_start_date.month
    anio_ref = week_start_date.year

    if persona.tipo == 'SACAFRANCO':
        try:
            return _assign_sacafranco_without_asignacion(persona, puesto, week_start_date, day)
        except Exception:
            logger.exception('Error asignando sacafranco sin crear asignación')
            return JsonResponse({'error': 'No se pudo asignar sacafranco'}, status=500)

    asignacion = Asignacion.objects.filter(persona=persona, mes=mes_ref, anio=anio_ref).first()
    try:
        if not asignacion:
            cliente = getattr(puesto.instalacion, 'cliente', None)
            instalacion = getattr(puesto, 'instalacion', None)
            horario = Horario.objects.first()
            if horario is None:
                horario = Horario.objects.create(hora_ingreso='08:00', hora_salida='20:00')
            try:
                asignacion = Asignacion.objects.create(
                    persona=persona,
                    cliente=cliente,
                    instalacion=instalacion,
                    puesto=puesto,
                    horario=horario,
                    mes=mes_ref,
                    anio=anio_ref,
                    recurring=False
                )
            except IntegrityError:
                asignacion = Asignacion.objects.filter(persona=persona, mes=mes_ref, anio=anio_ref).first()
                if not asignacion:
                    return JsonResponse({'error': 'Conflicto de asignación existente'}, status=400)
        else:
            # Reusar la asignación del mes/año y sincronizar contexto del puesto actual.
            changed = False
            if asignacion.puesto_id != puesto.id:
                asignacion.puesto = puesto
                changed = True
            try:
                cliente = getattr(puesto.instalacion, 'cliente', None)
                instalacion = getattr(puesto, 'instalacion', None)
                if asignacion.instalacion_id != getattr(instalacion, 'id', None):
                    asignacion.instalacion = instalacion
                    changed = True
                if asignacion.cliente_id != getattr(cliente, 'id', None):
                    asignacion.cliente = cliente
                    changed = True
            except Exception:
                pass
            if not asignacion.horario_id:
                horario = Horario.objects.first()
                if horario is None:
                    horario = Horario.objects.create(hora_ingreso='08:00', hora_salida='20:00')
                asignacion.horario = horario
                changed = True
            if changed:
                asignacion.save()

        # Propagar la asignación a semanas futuras a partir de la semana indicada,
        # pero sin tocar semanas pasadas ni sobrescribir códigos existentes.
        try:
            # parsear week_start a date
            try:
                if isinstance(week_start, str):
                    week_start_date = datetime.date.fromisoformat(week_start)
                else:
                    week_start_date = week_start
            except Exception:
                week_start_date = week_start

            # empezamos a propagar desde hoy (nunca hacia atras)
            today = datetime.date.today()
            prop_start = week_start_date if isinstance(week_start_date, datetime.date) else today
            if prop_start < today:
                prop_start = today
            # asegurar filas semanales alineadas con el front (semanas por mes: día 1 y saltos de 7)
            # y propagar varios años hacia adelante para que quede "de largo".
            weeks = []
            year_cursor = prop_start.year
            month_cursor = prop_start.month
            end_year = prop_start.year + 5
            while (year_cursor < end_year) or (year_cursor == end_year and month_cursor <= 12):
                base = datetime.date(year_cursor, month_cursor, 1)
                cursor = base
                while cursor.month == month_cursor:
                    if cursor >= prop_start:
                        weeks.append(cursor)
                    cursor += datetime.timedelta(days=7)
                month_cursor += 1
                if month_cursor > 12:
                    month_cursor = 1
                    year_cursor += 1

            for ws in weeks:
                semanal_obj, _ = AsignacionSemanal.objects.get_or_create(
                    asignacion_id=asignacion.id,
                    week_start=ws,
                    defaults={'puesto': puesto}
                )
                try:
                    cur_val = getattr(semanal_obj, day, '') or ''
                except Exception:
                    cur_val = ''
                cur_str = str(cur_val).strip()
                
                if cur_str == '':
                    setattr(semanal_obj, day, 'F')
                    semanal_obj.asignacion_id = asignacion.id
                    semanal_obj.save()
                elif cur_str.upper().startswith('F'):
                    if semanal_obj.asignacion_id != asignacion.id:
                        semanal_obj.asignacion_id = asignacion.id
                        semanal_obj.save()
                
        except Exception:
            logger.exception('Error propagando sacafranco a semanas futuras')

        semanal, created = AsignacionSemanal.objects.get_or_create(
            asignacion_id=asignacion.id,
            week_start=week_start_date if isinstance(week_start_date, datetime.date) else week_start,
            defaults={'asignacion': asignacion, 'puesto': puesto}
        )
        
        current_val = None
        try:
            current_val = getattr(semanal, day, None)
        except Exception:
            current_val = None

        # Vinculamos la asignación para la semana seleccionada si la celda está vacía
        # o contiene 'F' (no sobrescribimos el marcador 'F').
        if hasattr(semanal, day):
            cur = (current_val or '')
            cur_str = str(cur).strip() if cur is not None else ''
            # permitimos enlace si la celda está vacía o ya es 'F'
            if cur_str == '' or cur_str.upper().startswith('F'):
                if semanal.asignacion_id != asignacion.id:
                    semanal.asignacion = asignacion
                # si está vacía escribimos 'F', si ya es 'F' no la tocamos
                if cur_str == '':
                    setattr(semanal, day, 'F')
                semanal.save()
                return JsonResponse({'status': 'assigned', 'semanal_id': semanal.id})
            else:
                return JsonResponse({'status': 'preserved', 'semanal_id': semanal.id, 'value': current_val})
        else:
            return JsonResponse({'error': 'Día inválido'}, status=400)
    except Exception:
        logger.exception('Error asignando sacafranco')
        return JsonResponse({'error': 'No se pudo asignar sacafranco'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def desasignar_sacafranco(request):
    if not request.user.has_perm('CoreFisica.change_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    data = request.data
    persona_id = data.get('persona_id')
    puesto_id = data.get('puesto_id')
    week_start = data.get('week_start')
    day = data.get('day')

    if not all([persona_id, puesto_id, week_start, day]):
        return JsonResponse({'error': 'Faltan parámetros requeridos'}, status=400)

    try:
        # Obtener la persona por ID, retornando un error 404 si no se encuentra. Esto es esencial para asegurarse de que la persona a la que se le va a desasignar el sacafranco existe en la base de datos antes de intentar realizar cualquier operación relacionada con ella.
        persona = Persona.objects.get(id=persona_id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    try:
        # Obtener el puesto por ID, retornando un error 404 si no se encuentra. Esto es esencial para asegurarse de que el puesto al que se le va a desasignar el sacafranco existe en la base de datos antes de intentar realizar cualquier operación relacionada con él.
        puesto = Puesto.objects.get(id=puesto_id)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)

    # Normalizar día a las claves del modelo (mon..sun)
    day_norm = _normalize_day(day)
    if not day_norm:
        return JsonResponse({'error': 'Día inválido'}, status=400)
    day = day_norm

    try:
        try:
            if isinstance(week_start, str):
                week_start_date = datetime.date.fromisoformat(week_start)
            else:
                week_start_date = week_start if isinstance(week_start, datetime.date) else datetime.date.today()
        except Exception:
            week_start_date = datetime.date.today()

        if persona.tipo == 'SACAFRANCO':
            unassigned = _desasignar_sacafranco_without_asignacion(persona, puesto, week_start_date, day)
            if unassigned is not None:
                return unassigned

        mes_ref = week_start_date.month
        anio_ref = week_start_date.year
        asignacion = Asignacion.objects.filter(persona=persona, mes=mes_ref, anio=anio_ref).first()

        today = datetime.date.today()
        prop_start = week_start_date if isinstance(week_start_date, datetime.date) else today
        if prop_start < today:
            prop_start = today
        try:
            year_for_end = week_start_date.year if isinstance(week_start_date, datetime.date) else datetime.date.today().year
            prop_end = datetime.date(year_for_end, 12, 31)
        except Exception:
            today = datetime.date.today()
            prop_end = datetime.date(today.year, 12, 31)

        semanal = None
        if asignacion:
            semanal = AsignacionSemanal.objects.filter(
                puesto=puesto,
                week_start=week_start_date if isinstance(week_start_date, datetime.date) else week_start,
                asignacion_id=asignacion.id
            ).first()

        # Fallback: en datos históricos puede existir la marca F sin vínculo consistente
        # con asignación/persona; en ese caso buscamos la fila por puesto/semana/día.
        if not semanal:
            semanal = AsignacionSemanal.objects.filter(
                puesto=puesto,
                week_start=week_start_date if isinstance(week_start_date, datetime.date) else week_start,
                **{f"{day}__istartswith": 'F'}
            ).filter(
                Q(asignacion__persona=persona) | Q(asignacion__isnull=True)
            ).first() or AsignacionSemanal.objects.filter(
                puesto=puesto,
                week_start=week_start_date if isinstance(week_start_date, datetime.date) else week_start,
                **{f"{day}__istartswith": 'F'}
            ).first()

        if not semanal:
            return JsonResponse({'error': 'No hay programación semanal para ese puesto/semana'}, status=404)

        if not asignacion and semanal.asignacion_id:
            asignacion = semanal.asignacion

        if not hasattr(semanal, day):
            return JsonResponse({'error': 'Día inválido'}, status=400)

        day_offsets = {
            'mon': 0,
            'tue': 1,
            'wed': 2,
            'thu': 3,
            'fri': 4,
            'sat': 5,
            'sun': 6,
        }
        day_offset = day_offsets.get(day, 0)
        # Corta la propagación desde hoy hacia adelante (nunca hacia atras)
        selected_cell_date = week_start_date + datetime.timedelta(days=day_offset)
        cutoff_date = today if today > selected_cell_date else selected_cell_date

        # Propagar la desasignacion solo a fechas vigentes/futuras,
        # sin borrar la marca 'F'.
        try:
            if asignacion:
                candidate_qs = AsignacionSemanal.objects.filter(
                    puesto=puesto,
                    week_start__gte=prop_start,
                    week_start__lte=prop_end,
                    asignacion_id=asignacion.id
                )
            else:
                candidate_qs = AsignacionSemanal.objects.filter(
                    puesto=puesto,
                    week_start__gte=prop_start,
                    week_start__lte=prop_end,
                    asignacion_id=semanal.asignacion_id
                ) if semanal.asignacion_id else AsignacionSemanal.objects.filter(
                    puesto=puesto,
                    week_start__gte=prop_start,
                    week_start__lte=prop_end
                )

            for fila in candidate_qs:
                row_day_date = fila.week_start + datetime.timedelta(days=day_offset)
                if row_day_date < cutoff_date:
                    continue

                cell_value = str(getattr(fila, day, '') or '').strip().upper()
                if not cell_value.startswith('F'):
                    continue

                if fila.asignacion_id is not None:
                    fila.asignacion = None
                    fila.save()
        except Exception:
            logger.exception('Error propagando desasignación a semanas futuras')

        return JsonResponse({'status': 'unassigned', 'semanal_id': semanal.id})
    except Exception:
        logger.exception('Error desasignando sacafranco')
        return JsonResponse({'error': 'No se pudo desasignar sacafranco'}, status=500)


