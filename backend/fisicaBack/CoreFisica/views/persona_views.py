from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError, transaction
from django.db.models import Q
from ..models import Persona, AsignacionSemanal, Puesto, Asignacion, Horario
from openpyxl import load_workbook
import csv
import io
import re
import logging
import datetime

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
        q = (request.GET.get('q') or '').strip()
        tipo = (request.GET.get('tipo') or '').strip()

        personas = Persona.objects.all()
        if q:
            personas = personas.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(cedula__icontains=q)
            )

        if tipo:
            personas = personas.filter(tipo=tipo)

        personas = personas.order_by('apellidos')
        
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
    fullname_headers = ['APELLIDOS Y NOMBRES', 'APELLIDOS Y NOMBRE', 'NOMBRES Y APELLIDOS']
    allowed_tipos = {choice[0] for choice in Persona.TIPO_CHOICES}

    def normalize_header(value):
        if value is None:
            return ''
        import unicodedata
        text = str(value).strip().upper()
        # quitar acentos/diacríticos
        text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        return text

    def parse_bool(value):
        if value is None or value == '':
            return True
        return str(value).strip().lower() not in ['0', 'false', 'no', 'n']

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
                filas_raw.append((idx, raw_row))
        except Exception:
            logger.exception('Error procesando CSV de personas')
            return JsonResponse({'error': 'No se pudo leer el CSV'}, status=400)

    elif ext in ['xlsx']:
        try:
            wb = load_workbook(upload, read_only=True, data_only=True)
            ws = wb.active
            header_row = None
            header_norm = []
            header_idx = None
            for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20)), start=1):
                norm = [normalize_header(cell.value) for cell in row]
                has_cedula = 'CEDULA' in norm
                has_fullname_header = any(h in fullname_headers for h in norm)
                has_apellidos = 'APELLIDOS' in norm
                has_nombres = 'NOMBRES' in norm
                if has_cedula and ((has_apellidos and has_nombres) or has_fullname_header):
                    header_row = norm
                    header_idx = r_idx
                    break
            if header_row is None:
                return JsonResponse({'error': 'Faltan columnas: CEDULA y APELLIDOS/NOMBRES'}, status=400)
            header_map_idx = {h: idx for idx, h in enumerate(header_row)}
            for row_idx, row in enumerate(ws.iter_rows(min_row=header_idx+1, max_row=ws.max_row), start=header_idx+1):
                raw_row = {}
                for key in header_map_idx:
                    pos = header_map_idx[key]
                    raw_row[key] = row[pos].value if pos < len(row) else None
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
        tipo = str(raw.get('TIPO') or 'FIJOS').strip().upper()
        is_active = parse_bool(raw.get('IS_ACTIVE'))

        # obtener apellidos/nombres, permitiendo columna combinada
        apellidos = str(raw.get('APELLIDOS') or '').strip()
        nombres = str(raw.get('NOMBRES') or '').strip()
        if not (apellidos and nombres) and has_fullname_header:
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

class SacafrancoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        week_start = request.query_params.get('week_start')
        day = request.query_params.get('day')
        puesto_id = request.query_params.get('puesto_id')

        def normalize_day(tok):
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
            if t in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
                return t
            return mapping.get(t, '')

        if day:
            day_norm = normalize_day(day)
            if not day_norm:
                return Response({'error': 'Día inválido'}, status=400)
            day = day_norm

        qs = Persona.objects.filter(tipo='SACAFRANCO', is_active=True).order_by('nombres', 'apellidos')
        results = []
        for p in qs:
            occupied = False
            if week_start and day:
                if AsignacionSemanal.objects.filter(asignacion__persona=p, week_start=week_start, **{f"{day}__istartswith": 'F'}).exists():
                    occupied = True
            assigned_for_puesto = None
            if puesto_id and week_start and day:
                assigned = AsignacionSemanal.objects.filter(puesto_id=puesto_id, week_start=week_start, asignacion__persona=p, **{f"{day}__istartswith": 'F'}).first()
                if assigned:
                    assigned_for_puesto = p.id

            results.append({
                'id': p.id,
                'nombres': p.nombres,
                'apellidos': p.apellidos,
                'cedula': p.cedula,
                'status': 'asignado' if occupied else 'available',
                'assigned_for_puesto': assigned_for_puesto,
            })

        return Response(results)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_sacafranco(request):
    data = request.data
    persona_id = data.get('persona_id')
    puesto_id = data.get('puesto_id')
    week_start = data.get('week_start')
    day = data.get('day')
   

    if not all([persona_id, puesto_id, week_start, day]):
        return JsonResponse({'error': 'Faltan parámetros requeridos'}, status=400)

    # Normalizar día a las claves del modelo (mon..sun)
    def normalize_day(tok):
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
        if t in ['mon','tue','wed','thu','fri','sat','sun']:
            return t
        return mapping.get(t, '')

    day_norm = normalize_day(day)
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

    # No modificar semanas anteriores al inicio de la semana actual (semana corre de domingo a sábado)
    try:
        today = datetime.date.today()
        start_current_week = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
        if isinstance(week_start_date, datetime.date) and week_start_date < start_current_week:
            return JsonResponse({'status': 'preserved_past', 'detail': 'Semana pasada, no se modifica'}, status=200)
    except Exception:
        pass

    mes_ref = week_start_date.month
    anio_ref = week_start_date.year

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
            # Reusar la asignación del mes/año y actualizar si cambió puesto/cliente/instalación/horario
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

            today = datetime.date.today()
            start_current_week = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
            # Si la semana está antes de la semana actual, no tocamos
            if isinstance(week_start_date, datetime.date) and week_start_date < start_current_week:
                return JsonResponse({'status': 'preserved_past', 'detail': 'Semana pasada, no se modifica'}, status=200)

            # empezamos a propagar desde la semana seleccionada si es >= inicio semana actual,
            # en caso contrario desde el inicio de la semana actual
            prop_start = week_start_date if (isinstance(week_start_date, datetime.date) and week_start_date >= start_current_week) else start_current_week
            # propagamos sólo hasta el fin del año correspondiente (31-dic)
            try:
                year_for_end = week_start_date.year if isinstance(week_start_date, datetime.date) else today.year
                prop_end = datetime.date(year_for_end, 12, 31)
            except Exception:
                prop_end = datetime.date(today.year, 12, 31)

            # asegurar filas semanales alineadas con el front (semanas por mes: día 1 y saltos de 7)
            weeks = []
            year_end = prop_end.year
            month_cursor = prop_start.month
            while month_cursor <= 12:
                base = datetime.date(prop_start.year, month_cursor, 1)
                cursor = base
                while cursor.month == month_cursor:
                    if cursor >= prop_start:
                        weeks.append(cursor)
                    cursor += datetime.timedelta(days=7)
                month_cursor += 1

            for ws in weeks:
                semanal_obj, _ = AsignacionSemanal.objects.get_or_create(puesto=puesto, week_start=ws)
                try:
                    cur_val = getattr(semanal_obj, day, '') or ''
                except Exception:
                    cur_val = ''
                cur_str = str(cur_val).strip()
                # si está vacío, marcamos F y enlazamos asignación; si ya tiene F, solo enlazamos asignación
                if cur_str == '':
                    setattr(semanal_obj, day, 'F')
                    semanal_obj.asignacion_id = asignacion.id
                    semanal_obj.save()
                elif cur_str.upper().startswith('F'):
                    if semanal_obj.asignacion_id != asignacion.id:
                        semanal_obj.asignacion_id = asignacion.id
                        semanal_obj.save()
                # si tiene otro valor, no tocar
        except Exception:
            logger.exception('Error propagando sacafranco a semanas futuras')

        semanal, created = AsignacionSemanal.objects.get_or_create(puesto=puesto, week_start=week_start_date if isinstance(week_start_date, datetime.date) else week_start, defaults={'asignacion': asignacion})
        # obtener valor actual del día para decidir si lo sobrescribimos
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
    data = request.data
    persona_id = data.get('persona_id')
    puesto_id = data.get('puesto_id')
    week_start = data.get('week_start')
    day = data.get('day')

    if not all([persona_id, puesto_id, week_start, day]):
        return JsonResponse({'error': 'Faltan parámetros requeridos'}, status=400)

    try:
        persona = Persona.objects.get(id=persona_id)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

    try:
        puesto = Puesto.objects.get(id=puesto_id)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)

    try:
        asignacion = Asignacion.objects.filter(persona=persona, puesto=puesto).first()
        if not asignacion:
            return JsonResponse({'error': 'No existe asignación para esa persona en el puesto'}, status=404)

        # parse week_start
        try:
            if isinstance(week_start, str):
                week_start_date = datetime.date.fromisoformat(week_start)
            else:
                week_start_date = week_start
        except Exception:
            week_start_date = week_start

        today = datetime.date.today()
        # comenzamos a afectar desde la semana seleccionada solo si es futura; si no, desde hoy
        prop_start = week_start_date if (isinstance(week_start_date, datetime.date) and week_start_date > today) else today
        try:
            year_for_end = week_start_date.year if isinstance(week_start_date, datetime.date) else today.year
            prop_end = datetime.date(year_for_end, 12, 31)
        except Exception:
            prop_end = datetime.date(today.year, 12, 31)

        semanal = AsignacionSemanal.objects.filter(puesto=puesto, week_start=week_start_date if isinstance(week_start_date, datetime.date) else week_start, asignacion=asignacion).first()
        if not semanal:
            return JsonResponse({'error': 'No hay programación semanal para ese puesto/semana'}, status=404)

        # Si la semana seleccionada es pasada (antes de prop_start), no la tocamos
        try:
            if isinstance(semanal.week_start, datetime.date) and semanal.week_start < prop_start:
                return JsonResponse({'status': 'preserved_past', 'semanal_id': semanal.id, 'value': getattr(semanal, day, '')})
        except Exception:
            pass

        if not hasattr(semanal, day):
            return JsonResponse({'error': 'Día inválido'}, status=400)

        # Limpiar la semana seleccionada (si está en o después de prop_start)
        setattr(semanal, day, '')
        # desvincular asignacion de esta fila si corresponde
        if semanal.asignacion_id == asignacion.id:
            semanal.asignacion = None
        semanal.save()

        # Propagar la eliminación a semanas futuras hasta fin de año (solo filas ligadas a la misma asignacion)
        try:
            from django.db.models import Q as _Q
            future_qs = AsignacionSemanal.objects.filter(puesto=puesto, week_start__gte=prop_start, week_start__lte=prop_end, asignacion_id=asignacion.id)
            # Solo limpiar celdas que contienen 'F' (o comienzan con 'F')
            target_qs = future_qs.filter(_Q(**{f"{day}__istartswith": 'F'}))
            if target_qs.exists():
                target_qs.update(**{day: ''}, asignacion_id=None)
        except Exception:
            logger.exception('Error propagando desasignación a semanas futuras')

        return JsonResponse({'status': 'unassigned', 'semanal_id': semanal.id})
    except Exception:
        logger.exception('Error desasignando sacafranco')
        return JsonResponse({'error': 'No se pudo desasignar sacafranco'}, status=500)


