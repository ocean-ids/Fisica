from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from ..models import Asignacion, AsignacionSemanal, Puesto
from django.db.models import Q, Max
from django.db import transaction
from ..serializers import AsignacionSerializer
import openpyxl
import datetime


@api_view(['GET'])
def obtener_asignaciones(request, mes=None, anio=None):
    instalacion_id = request.GET.get('instalacion_id')
    cliente_id = request.GET.get('cliente_id')

    if mes and anio:
        month_start = datetime.date(int(anio), int(mes), 1)
        if int(mes) == 12:
            month_end = datetime.date(int(anio) + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            month_end = datetime.date(int(anio), int(mes) + 1, 1) - datetime.timedelta(days=1)

        asignaciones = Asignacion.objects.filter(
            estado='ACTIVO'
        ).exclude(persona__tipo='SACAFRANCO').filter(
            Q(mes=mes, anio=anio) |
            (Q(recurring=True) & Q(start_date__lte=month_end) & (Q(end_date__isnull=True) | Q(end_date__gte=month_start)))
        ).select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario')
    else:
        asignaciones = Asignacion.objects.filter(
            estado='ACTIVO'
        ).exclude(persona__tipo='SACAFRANCO').select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario')

    if cliente_id:
        asignaciones = asignaciones.filter(cliente_id=cliente_id)
    if instalacion_id:
        asignaciones = asignaciones.filter(instalacion_id=instalacion_id)
    
    serializer = AsignacionSerializer(asignaciones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def asignar_servicio(request):
    print(f"📥 Datos recibidos: {request.data}")
    serializer = AsignacionSerializer(data=request.data)
    if serializer.is_valid():
        asignacion = serializer.save()
        # Si la asignación es recurrente y no tiene start_date, fijar start_date al primer día del mes de la asignación
        try:
            if getattr(asignacion, 'recurring', False) and not getattr(asignacion, 'start_date', None):
                import datetime
                asignacion.start_date = datetime.date(int(asignacion.anio), int(asignacion.mes), 1)
                asignacion.save()
        except Exception:
            pass
        # Crear filas de AsignacionSemanal para el puesto en las semanas del mes/año de la asignación
        # Forzamos creación de calendario siempre (evita depender del flag del front y cubre el mes actual)
        create_calendar = True

        if create_calendar:
            try:
                mes = int(asignacion.mes)
                anio = int(asignacion.anio)
                first_day = datetime.date(anio, mes, 1)
                if mes == 12:
                    next_month_first = datetime.date(anio + 1, 1, 1)
                else:
                    next_month_first = datetime.date(anio, mes + 1, 1)
                last_day = next_month_first - datetime.timedelta(days=1)

                # semanas del mes iniciando el día 1 y sumando bloques de 7 días (1,8,15,22,29)
                current = first_day

                weekday_names = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']

                # Obtener instancia de Puesto (por si asignacion.puesto es id)
                puesto_obj = None
                try:
                    puesto_obj = getattr(asignacion, 'puesto')
                    if isinstance(puesto_obj, int) or isinstance(puesto_obj, str):
                        puesto_obj = Puesto.objects.get(id=int(puesto_obj))
                except Exception:
                    try:
                        puesto_obj = Puesto.objects.get(id=asignacion.puesto_id)
                    except Exception:
                        puesto_obj = None

                dias_puesto = []
                if puesto_obj:
                    try:
                        if hasattr(puesto_obj, 'dias') and getattr(puesto_obj, 'dias'):
                            dias_puesto = puesto_obj.dias or []
                        else:
                            horarios_qs = getattr(puesto_obj, 'horarios', None)
                            if horarios_qs is not None:
                                dias_nums = list(horarios_qs.values_list('dia', flat=True))
                                day_map = {1: 'lunes', 2: 'martes', 3: 'miercoles', 4: 'jueves', 5: 'viernes', 6: 'sabado', 7: 'domingo'}
                                dias_puesto = [day_map.get(n, '') for n in dias_nums if n]
                    except Exception:
                        dias_puesto = []

                def normalize_day_token(tok: str) -> str:
                    t = str(tok).strip().lower()
                    if not t:
                        return ''
                    map_short = {
                        'l': 'lunes', 'lu': 'lunes', 'lun': 'lunes', 'lunes': 'lunes',
                        'm': 'martes', 'ma': 'martes', 'mar': 'martes', 'martes': 'martes',
                        'mi': 'miercoles', 'mie': 'miercoles', 'miercoles': 'miercoles', 'miércoles':'miercoles',
                        'j': 'jueves', 'ju': 'jueves', 'jue': 'jueves', 'jueves': 'jueves',
                        'v': 'viernes', 'vi': 'viernes', 'vie': 'viernes', 'viernes': 'viernes',
                        's': 'sabado', 'sa': 'sabado', 'sab': 'sabado', 'sabado': 'sabado', 'sábado': 'sabado',
                        'd': 'domingo', 'do': 'domingo', 'dom': 'domingo', 'domingo': 'domingo'
                    }
                    return map_short.get(t, t)

                dias_norm = [normalize_day_token(d) for d in dias_puesto if d]
                # también obtener números de día (1..7) desde los horarios si existen (normalizados a int)
                dias_nums = []
                try:
                    if puesto_obj is not None:
                        horarios_qs = getattr(puesto_obj, 'horarios', None)
                        if horarios_qs is not None:
                            try:
                                dias_nums = [int(n) for n in horarios_qs.values_list('dia', flat=True) if n is not None]
                            except Exception:
                                dias_nums = list(horarios_qs.values_list('dia', flat=True))
                except Exception:
                    dias_nums = []
                turno = (getattr(puesto_obj, 'turno', '') or '').strip().lower() if puesto_obj else ''
                default_code = 'N' if turno.startswith('n') else 'D'

                while current <= last_day:
                    defaults = {}
                    for idx in range(7):
                        day_date = current + datetime.timedelta(days=idx)
                        name = weekday_names[day_date.weekday()]
                        weekday_keys = ['mon','tue','wed','thu','fri','sat','sun']
                        key = weekday_keys[day_date.weekday()]

                        # Obtener secuencia del patron antes de evaluar applies_by_puesto
                        seq = None
                        patron = None
                        try:
                            patron = getattr(asignacion, 'patronAsignacion', None)
                            # si es id, buscar objeto
                            if patron and not hasattr(patron, 'secuencia'):
                                from ..models import PatronAsignacion as _PA
                                try:
                                    patron = _PA.objects.get(id=int(patron))
                                except Exception:
                                    patron = None
                            if patron and getattr(patron, 'secuencia', None):
                                seq = [str(x).strip().upper() for x in patron.secuencia if x]
                        except Exception:
                            seq = None

                        # Preferir coincidencia por número de día si existen horarios registrados
                        if dias_nums:
                            applies_by_puesto = (day_date.isoweekday() in dias_nums)
                        else:
                            applies_by_puesto = any(name == d or d in name or name in d for d in dias_norm) or (not dias_norm and bool(seq))

                        value = ''
                        if seq:
                            # definir fecha referencia
                            ref_date = None
                            if asignacion.start_date:
                                ref_date = asignacion.start_date
                            elif getattr(asignacion, 'fecha', None):
                                ref_date = asignacion.fecha
                            else:
                                try:
                                    ref_date = datetime.date(int(asignacion.anio), int(asignacion.mes), 1)
                                except Exception:
                                    ref_date = current

                            # determinar si la asignación aplica ese día
                            active = True
                            if asignacion.recurring:
                                if asignacion.start_date and day_date < asignacion.start_date:
                                    active = False
                                if asignacion.end_date and asignacion.end_date and day_date > asignacion.end_date:
                                    active = False
                            else:
                                # non-recurring: match by fecha or month/year
                                if getattr(asignacion, 'fecha', None):
                                    active = (day_date == asignacion.fecha)
                                else:
                                    active = (day_date.month == asignacion.mes and day_date.year == asignacion.anio)

                            if active and applies_by_puesto:
                                try:
                                    days_diff = (day_date - ref_date).days
                                    # detectar si corresponde aplicar offset por 24h
                                    offset = 0
                                    try:
                                        is_24h = False
                                        # preferir la duración del horario de la asignación
                                        if getattr(asignacion, 'horario', None):
                                            hi = asignacion.horario.hora_ingreso
                                            ho = asignacion.horario.hora_salida
                                            dt1 = datetime.datetime.combine(datetime.date(1,1,1), hi)
                                            dt2 = datetime.datetime.combine(datetime.date(1,1,1), ho)
                                            if dt2 <= dt1:
                                                dt2 += datetime.timedelta(days=1)
                                            dur = (dt2 - dt1).total_seconds() / 3600.0
                                            is_24h = dur >= 23.5
                                        # si no se detectó por asignacion, caer en puesto horarios
                                        if not is_24h and puesto_obj is not None:
                                            horarios_qs = getattr(puesto_obj, 'horarios', None)
                                            if horarios_qs is not None:
                                                try:
                                                    dia_num = day_date.isoweekday()
                                                    horas_por_dia = list(horarios_qs.filter(dia=dia_num).values_list('horas', flat=True))
                                                    if horas_por_dia:
                                                        is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_por_dia)
                                                    else:
                                                        horas_list = list(horarios_qs.values_list('horas', flat=True))
                                                        is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_list)
                                                except Exception:
                                                    horas_list = list(horarios_qs.values_list('horas', flat=True))
                                                    is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_list)
                                        if is_24h and seq:
                                            # offset = longitud del primer bloque consecutivo igual al primer símbolo
                                            first = seq[0]
                                            cnt = 0
                                            for s in seq:
                                                if s == first:
                                                    cnt += 1
                                                else:
                                                    break
                                            offset = cnt
                                    except Exception:
                                        offset = 0

                                    idx_seq = (days_diff + offset) % len(seq)
                                    value = seq[idx_seq]
                                except Exception:
                                    value = ''
                        else:
                            if applies_by_puesto:
                                value = default_code

                        defaults[key] = value

                    try:
                        pid = puesto_obj.id if puesto_obj and hasattr(puesto_obj, 'id') else getattr(asignacion, 'puesto_id', None)
                        # update_or_create garantiza que la fila del puesto/semana siempre quede ligada a la asignación actual
                        obj, created = AsignacionSemanal.objects.update_or_create(
                            puesto_id=pid,
                            week_start=current,
                            defaults={**defaults, 'asignacion': asignacion, 'puesto_id': pid}
                        )
                        if not created:
                            # Asegurar asignacion vinculada y días actualizados
                            if getattr(obj, 'asignacion_id', None) != getattr(asignacion, 'id', None):
                                obj.asignacion = asignacion
                            for k, v in defaults.items():
                                setattr(obj, k, v)
                            obj.save()
                    except Exception as e:
                        raise Exception(f"Error creando/asegurando AsignacionSemanal en asignar_servicio (puesto {getattr(puesto_obj,'id',None)} week_start {current}): {e}")
                    current += datetime.timedelta(days=7)
            except Exception as e:
                try:
                    asignacion.delete()
                except Exception:
                    pass
                return Response({'error': f'No se pudo crear el calendario semanal: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    # Si hay error de unicidad (persona, mes, anio) intentamos actualizar la asignación existente
    print(f"❌ Errores de validación: {serializer.errors}")
    try:
        errs = serializer.errors or {}
        nonf = errs.get('non_field_errors') if isinstance(errs, dict) else None
        is_unique = False
        if nonf:
            for e in nonf:
                if 'unique' in str(e).lower() or 'únic' in str(e).lower():
                    is_unique = True
                    break
        if is_unique:
            persona = request.data.get('persona')
            mes = request.data.get('mes')
            anio = request.data.get('anio')
            if persona and mes and anio:
                existing = Asignacion.objects.filter(persona_id=persona, mes=mes, anio=anio).first()
                if existing:
                    # actualizar la asignación existente con los nuevos datos
                    serializer2 = AsignacionSerializer(existing, data=request.data, partial=True)
                    if serializer2.is_valid():
                        asignacion = serializer2.save()
                        # crear/actualizar filas semanales siempre
                        create_calendar = True
                        if create_calendar:
                            try:
                                mes = int(asignacion.mes)
                                anio = int(asignacion.anio)
                                first_day = datetime.date(anio, mes, 1)
                                if mes == 12:
                                    next_month_first = datetime.date(anio + 1, 1, 1)
                                else:
                                    next_month_first = datetime.date(anio, mes + 1, 1)
                                last_day = next_month_first - datetime.timedelta(days=1)
                                # semanas del mes iniciando el día 1 y sumando bloques de 7 días (1,8,15,22,29)
                                current = first_day

                                # Obtener puesto_obj
                                puesto_obj = None
                                try:
                                    puesto_obj = getattr(asignacion, 'puesto')
                                    if isinstance(puesto_obj, int) or isinstance(puesto_obj, str):
                                        puesto_obj = Puesto.objects.get(id=int(puesto_obj))
                                except Exception:
                                    try:
                                        puesto_obj = Puesto.objects.get(id=asignacion.puesto_id)
                                    except Exception:
                                        puesto_obj = None

                                dias_puesto = []
                                if puesto_obj:
                                    try:
                                        if hasattr(puesto_obj, 'dias') and getattr(puesto_obj, 'dias'):
                                            dias_puesto = puesto_obj.dias or []
                                        else:
                                            horarios_qs = getattr(puesto_obj, 'horarios', None)
                                            if horarios_qs is not None:
                                                dias_nums = list(horarios_qs.values_list('dia', flat=True))
                                                day_map = {1: 'lunes', 2: 'martes', 3: 'miercoles', 4: 'jueves', 5: 'viernes', 6: 'sabado', 7: 'domingo'}
                                                dias_puesto = [day_map.get(n, '') for n in dias_nums if n]
                                    except Exception:
                                        dias_puesto = []

                                def normalize_day_token(tok: str) -> str:
                                    t = str(tok).strip().lower()
                                    if not t:
                                        return ''
                                    map_short = {
                                        'l': 'lunes', 'lu': 'lunes', 'lun': 'lunes', 'lunes': 'lunes',
                                        'm': 'martes', 'ma': 'martes', 'mar': 'martes', 'martes': 'martes',
                                        'mi': 'miercoles', 'mie': 'miercoles', 'miercoles': 'miercoles', 'miércoles':'miercoles',
                                        'j': 'jueves', 'ju': 'jueves', 'jue': 'jueves', 'jueves': 'jueves',
                                        'v': 'viernes', 'vi': 'viernes', 'vie': 'viernes', 'viernes': 'viernes',
                                        's': 'sabado', 'sa': 'sabado', 'sab': 'sabado', 'sabado': 'sabado', 'sábado': 'sabado',
                                        'd': 'domingo', 'do': 'domingo', 'dom': 'domingo', 'domingo': 'domingo'
                                    }
                                    return map_short.get(t, t)

                                dias_norm = [normalize_day_token(d) for d in dias_puesto if d]
                                turno = (getattr(puesto_obj, 'turno', '') or '').strip().lower() if puesto_obj else ''
                                default_code = 'N' if turno.startswith('n') else 'D'

                                # también obtener números de día (1..7) desde los horarios si existen (normalizados a int)
                                dias_nums = []
                                try:
                                    horarios_qs = getattr(puesto_obj, 'horarios', None)
                                    if horarios_qs is not None:
                                        try:
                                            dias_nums = [int(n) for n in horarios_qs.values_list('dia', flat=True) if n is not None]
                                        except Exception:
                                            dias_nums = list(horarios_qs.values_list('dia', flat=True))
                                except Exception:
                                    dias_nums = []

                                weekday_names = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
                                while current <= last_day:
                                    defaults = {}
                                    for idx in range(7):
                                        day_date = current + datetime.timedelta(days=idx)
                                        name = weekday_names[day_date.weekday()]
                                        weekday_keys = ['mon','tue','wed','thu','fri','sat','sun']
                                        key = weekday_keys[day_date.weekday()]

                                        # Obtener secuencia del patron antes de evaluar applies_by_puesto
                                        seq = None
                                        patron = None
                                        try:
                                            patron = getattr(asignacion, 'patronAsignacion', None)
                                            if patron and not hasattr(patron, 'secuencia'):
                                                from ..models import PatronAsignacion as _PA
                                                try:
                                                    patron = _PA.objects.get(id=int(patron))
                                                except Exception:
                                                    patron = None
                                            if patron and getattr(patron, 'secuencia', None):
                                                seq = [str(x).strip().upper() for x in patron.secuencia if x]
                                        except Exception:
                                            seq = None

                                        # Preferir coincidencia por número de día si existen horarios registrados
                                        if dias_nums:
                                            applies_by_puesto = (day_date.isoweekday() in dias_nums)
                                        else:
                                            applies_by_puesto = any(name == d or d in name or name in d for d in dias_norm) or (not dias_norm and bool(seq))

                                        value = ''
                                        if seq:
                                            ref_date = None
                                            if asignacion.start_date:
                                                ref_date = asignacion.start_date
                                            elif getattr(asignacion, 'fecha', None):
                                                ref_date = asignacion.fecha
                                            else:
                                                try:
                                                    ref_date = datetime.date(int(asignacion.anio), int(asignacion.mes), 1)
                                                except Exception:
                                                    ref_date = current

                                            active = True
                                            if asignacion.recurring:
                                                if asignacion.start_date and day_date < asignacion.start_date:
                                                    active = False
                                                if asignacion.end_date and asignacion.end_date and day_date > asignacion.end_date:
                                                    active = False
                                            else:
                                                if getattr(asignacion, 'fecha', None):
                                                    active = (day_date == asignacion.fecha)
                                                else:
                                                    active = (day_date.month == asignacion.mes and day_date.year == asignacion.anio)

                                            if active and applies_by_puesto:
                                                try:
                                                    days_diff = (day_date - ref_date).days
                                                    # detectar si corresponde aplicar offset por 24h
                                                    offset = 0
                                                    try:
                                                        is_24h = False
                                                        # preferir la duración del horario de la asignación
                                                        if getattr(asignacion, 'horario', None):
                                                            hi = asignacion.horario.hora_ingreso
                                                            ho = asignacion.horario.hora_salida
                                                            dt1 = datetime.datetime.combine(datetime.date(1,1,1), hi)
                                                            dt2 = datetime.datetime.combine(datetime.date(1,1,1), ho)
                                                            if dt2 <= dt1:
                                                                dt2 += datetime.timedelta(days=1)
                                                            dur = (dt2 - dt1).total_seconds() / 3600.0
                                                            is_24h = dur >= 23.5
                                                        # si no se detectó por asignacion, caer en puesto horarios
                                                        if not is_24h and puesto_obj is not None:
                                                            horarios_qs = getattr(puesto_obj, 'horarios', None)
                                                            if horarios_qs is not None:
                                                                # Preferir horario del día específico (dia de la semana)
                                                                try:
                                                                    dia_num = day_date.isoweekday()
                                                                    horas_por_dia = list(horarios_qs.filter(dia=dia_num).values_list('horas', flat=True))
                                                                    if horas_por_dia:
                                                                        is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_por_dia)
                                                                    else:
                                                                        # fallback: si no hay fila para ese día, revisar cualquier horario 24h
                                                                        horas_list = list(horarios_qs.values_list('horas', flat=True))
                                                                        is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_list)
                                                                except Exception:
                                                                    horas_list = list(horarios_qs.values_list('horas', flat=True))
                                                                    is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_list)
                                                        if is_24h and seq:
                                                            # offset = longitud del primer bloque consecutivo igual al primer símbolo
                                                            first = seq[0]
                                                            cnt = 0
                                                            for s in seq:
                                                                if s == first:
                                                                    cnt += 1
                                                                else:
                                                                    break
                                                            offset = cnt
                                                    except Exception:
                                                        offset = 0

                                                    idx_seq = (days_diff + offset) % len(seq)
                                                    value = seq[idx_seq]
                                                except Exception:
                                                    value = ''
                                        else:
                                            if applies_by_puesto:
                                                value = default_code

                                        defaults[key] = value
                                    try:
                                        pid = puesto_obj.id if puesto_obj and hasattr(puesto_obj, 'id') else getattr(asignacion, 'puesto_id', None)
                                        obj, created = AsignacionSemanal.objects.update_or_create(
                                            puesto_id=pid,
                                            week_start=current,
                                            defaults={**defaults, 'asignacion': asignacion, 'puesto_id': pid}
                                        )
                                        if not created:
                                            if getattr(obj, 'asignacion_id', None) != getattr(asignacion, 'id', None):
                                                obj.asignacion = asignacion
                                            for k, v in defaults.items():
                                                setattr(obj, k, v)
                                            obj.save()
                                    except Exception as e:
                                        raise Exception(f"Error creando/asegurando AsignacionSemanal al actualizar: {e}")
                                    current += datetime.timedelta(days=7)
                            except Exception as e:
                                return Response({'error': f'No se pudo actualizar el calendario semanal: {e}'}, status=status.HTTP_400_BAD_REQUEST)
                        return Response(serializer2.data, status=status.HTTP_200_OK)
                    else:
                        return Response(serializer2.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        pass

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def editar_servicio(request, id):
    try:
        asignacion = Asignacion.objects.get(id=id)
    except Asignacion.DoesNotExist:
        return Response({'error': 'Asignación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AsignacionSerializer(asignacion, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def guardar_orden_asignacion(request):
    ordenes = request.data.get('ordenes', [])

    for item in ordenes:
        try:
            asignacion = Asignacion.objects.get(id=item['id'])
            asignacion.orden = item['orden']
            asignacion.save()
        except Asignacion.DoesNotExist:
            continue
    return Response({'mensaje': 'Orden actualizado correctamente'})

@api_view(['DELETE'])
def eliminar_asignacion(request, id):
    try:
        asignar = Asignacion.objects.get(id=id)
        # Guardar datos antes de eliminar para poder limpiar calendario y patron si corresponde
        # No recuperamos/eliminamos el PatronAsignacion aquí: preservamos los
        # patrones creados por los usuarios (se mantienen en el select).

        # Calcular una ventana de fechas para limpiar filas semanales huérfanas del mismo puesto.
        # Preferimos start_date/end_date si existen; si no, usamos mes/año y extendemos
        # hasta la última semana existente para ese puesto.
        puesto_id = getattr(asignar, 'puesto_id', None)
        window_start = None
        window_end = None
        try:
            start_ref = getattr(asignar, 'start_date', None) or getattr(asignar, 'fecha', None)
            if not start_ref and getattr(asignar, 'mes', None) and getattr(asignar, 'anio', None):
                start_ref = datetime.date(int(asignar.anio), int(asignar.mes), 1)

            end_ref = getattr(asignar, 'end_date', None)
            if not end_ref and start_ref:
                # Fin de mes del start_ref
                next_month = (start_ref.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
                end_ref = next_month - datetime.timedelta(days=1)

            if start_ref and end_ref:
                window_start = start_ref - datetime.timedelta(days=6)
                window_end = end_ref
        except Exception:
            window_start = None
            window_end = None

        # Ampliar la ventana usando las filas existentes del mismo puesto (cubrir recurrentes sin end_date).
        try:
            if puesto_id:
                max_week = AsignacionSemanal.objects.filter(puesto_id=puesto_id).aggregate(Max('week_start')).get('week_start__max')
                if max_week:
                    window_end = window_end or max_week
                if start_ref and not window_start:
                    window_start = start_ref - datetime.timedelta(days=6)
        except Exception:
            pass

        # Borrar filas semanales y luego la asignación dentro de una transacción
        try:
            with transaction.atomic():
                # Eliminar filas ligadas explícitamente a la asignación
                AsignacionSemanal.objects.filter(asignacion_id=id).delete()

                # Limpiar filas del mismo puesto sin asignación pero con códigos (evita celdas huérfanas)
                try:
                    if puesto_id:
                        qs_clean = AsignacionSemanal.objects.filter(puesto_id=puesto_id)
                        if window_start:
                            qs_clean = qs_clean.filter(week_start__gte=window_start)
                        if window_end:
                            qs_clean = qs_clean.filter(week_start__lte=window_end)
                        # filas sin asignación, ligadas a esta asignación, o relinkeadas a SACAFRANCO
                        qs_clean = qs_clean.filter(
                            Q(asignacion__isnull=True) |
                            Q(asignacion_id=id) |
                            Q(asignacion__persona__tipo='SACAFRANCO')
                        )
                        for row in qs_clean:
                            dirty = False
                            for d in ['mon','tue','wed','thu','fri','sat','sun']:
                                val = getattr(row, d, '') or ''
                                if val != '':
                                    setattr(row, d, '')
                                    dirty = True
                            if dirty or row.asignacion_id:
                                row.asignacion = None
                                row.save()
                except Exception:
                    pass

                # Limpiar celdas 'F' del mismo puesto dentro de la ventana para evitar sacafranco huérfano
                try:
                    if puesto_id:
                        from django.db.models import Q as _Q
                        qs_f = AsignacionSemanal.objects.filter(puesto_id=puesto_id)
                        if window_start:
                            qs_f = qs_f.filter(week_start__gte=window_start)
                        if window_end:
                            qs_f = qs_f.filter(week_start__lte=window_end)
                        # Celdas 'F' y asignacion nula o la misma que se elimina
                        f_filter = (
                            _Q(mon__istartswith='F') | _Q(tue__istartswith='F') | _Q(wed__istartswith='F') |
                            _Q(thu__istartswith='F') | _Q(fri__istartswith='F') | _Q(sat__istartswith='F') |
                            _Q(sun__istartswith='F')
                        )
                        qs_f = qs_f.filter(f_filter).filter(
                            _Q(asignacion__isnull=True) |
                            _Q(asignacion_id=id) |
                            _Q(asignacion__persona__tipo='SACAFRANCO')
                        )
                        for row in qs_f:
                            try:
                                for d in ['mon','tue','wed','thu','fri','sat','sun']:
                                    val = getattr(row, d, '') or ''
                                    if str(val).upper().startswith('F'):
                                        setattr(row, d, '')
                                row.asignacion = None
                                row.save()
                            except Exception:
                                pass
                except Exception:
                    pass

                # Además, intentar eliminar posibles filas huérfanas creadas
                # para el mismo puesto dentro de la ventana calculada.
                try:
                    if puesto_id:
                        qs = AsignacionSemanal.objects.filter(puesto_id=puesto_id, asignacion__isnull=True)
                        if window_start:
                            qs = qs.filter(week_start__gte=window_start)
                        if window_end:
                            qs = qs.filter(week_start__lte=window_end)
                        orphan_count = qs.count()
                        if orphan_count:
                            print(f"DEBUG eliminar_asignacion: borrando {orphan_count} filas huérfanas para puesto {puesto_id} entre {window_start or '-inf'} y {window_end or '+inf'}")
                            qs.delete()
                except Exception:
                    # no crítico: continuar con la eliminación principal
                    pass

                asignar.delete()
        except Exception as e:
            print(f"⚠️ Error eliminando asignación y sus semanales: {e}")
            return Response({'error': 'No se pudo eliminar la asignación'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'mensaje': 'Asignación eliminada correctamente'}, status=status.HTTP_204_NO_CONTENT)
    except Asignacion.DoesNotExist:
        return Response({'error': 'Asignacion no encontrada'}, status=status.HTTP_404_NOT_FOUND)


def exportar_asignaciones_excel(request):
    import calendar
    from openpyxl.styles import Font, Alignment, Border, Side
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asignaciones y Calendario"

    # Obtener mes/año desde query params si vienen, si no usar mes actual
    qs = request.GET
    try:
        if 'mes' in qs and 'anio' in qs:
            month = int(qs.get('mes'))
            year = int(qs.get('anio'))
        else:
            today = datetime.date.today()
            year = today.year
            month = today.month
    except Exception:
        today = datetime.date.today()
        year = today.year
        month = today.month

    first_day = datetime.date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    dates = [first_day + datetime.timedelta(days=i) for i in range(last_day_num)]

    # Columnas izquierdas (datos de asignación)
    # Se eliminó 'Dirección Instalación' según solicitud
    left_headers = ['HORARIO', 'CÓDIGO', 'CLIENTE', 'NOMBRE PUESTO', 'RESUMEN', 'CÉDULA', 'PERSONA', 'TIPO']
    left_cols = len(left_headers)

    # Columnas de fecha comienzan después de las columnas izquierdas
    date_start_col = left_cols + 1
    num_days = len(dates)

    # Row 1: nombre del mes (merge sobre las columnas de días)
    month_name = first_day.strftime('%B').upper()
    if num_days > 0:
        ws.merge_cells(start_row=1, start_column=date_start_col, end_row=1, end_column=date_start_col + num_days - 1)
        cell = ws.cell(row=1, column=date_start_col)
        cell.value = f"{month_name} {year}"
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Row 2: día de la semana (abreviado)
    dow_names = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
    for i, d in enumerate(dates):
        c = ws.cell(row=2, column=date_start_col + i)
        c.value = dow_names[d.weekday()]
        c.alignment = Alignment(horizontal='center')

    # Row 3: número de día. También aquí colocamos los encabezados izquierdos
    for idx, h in enumerate(left_headers, start=1):
        ch = ws.cell(row=3, column=idx)
        ch.value = h
        ch.font = Font(bold=True)
        ch.alignment = Alignment(horizontal='left')
    for i, d in enumerate(dates):
        c = ws.cell(row=3, column=date_start_col + i)
        c.value = d.day
        c.alignment = Alignment(horizontal='center')

    # Estilos comunes
    thin = Side(border_style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Freeze panes (congelar columnas de datos y filas superiores)
    ws.freeze_panes = ws.cell(row=4, column=date_start_col)

    # Rellenar filas: una fila por Asignacion activa para el mes solicitado
    # Aplicar la misma lógica que en obtener_asignaciones: incluir recurrentes que aplican al mes
    month_start = first_day
    if month == 12:
        month_end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        month_end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    asignaciones = Asignacion.objects.filter(estado='ACTIVO').filter(
        Q(mes=month, anio=year) |
        (Q(recurring=True) & Q(start_date__lte=month_end) & (Q(end_date__isnull=True) | Q(end_date__gte=month_start)))
    ).select_related('horario', 'cliente', 'puesto', 'persona', 'instalacion').prefetch_related('puesto__horarios')
    start_row = 4
    # Precachear AsignacionSemanal por puesto y week_start para eficiencia
    semanal_cache = {}

    def build_resumen(puesto):
        try:
            if not puesto:
                return ''
            horarios_qs = getattr(puesto, 'horarios', None)
            horarios = list(horarios_qs.all()) if horarios_qs is not None else []
            if not horarios:
                return ''

            day_map = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'}
            groups = {}

            for h in horarios:
                horas_val = int(getattr(h, 'horas', 0) or 0)
                turno_val = (getattr(h, 'turno', '') or '').strip()
                key = f"{horas_val}-{turno_val}"
                if key not in groups:
                    groups[key] = {'horas': horas_val, 'turno': turno_val, 'dias': []}
                dia_val = getattr(h, 'dia', None)
                if dia_val and dia_val not in groups[key]['dias']:
                    groups[key]['dias'].append(dia_val)

            def turno_letter(t: str) -> str:
                lower = (t or '').strip().lower()
                if lower.startswith('d'):
                    return 'D'
                if lower.startswith('n'):
                    return 'N'
                if lower.startswith('a'):
                    return 'A'
                return ''

            parts = []
            for g in groups.values():
                dias_str = ''.join([day_map.get(d, '') for d in sorted(g['dias'])]) if g['dias'] else ''
                base = f"{g['horas']}{turno_letter(g['turno'])}".strip()
                parts.append(f"{base} {dias_str}".strip())

            # Ordenar priorizando horas numéricas bajas primero (coincide con la vista)
            def sort_key(p: str):
                try:
                    return int(''.join([ch for ch in p if ch.isdigit()]) or 0)
                except Exception:
                    return 0

            parts = sorted(parts, key=sort_key)
            body = ' / '.join([p for p in parts if p])
            cant = str(getattr(puesto, 'cantidad_guardias', '') or '').strip()
            if cant and body:
                return f"{cant} {body}"
            if cant:
                return cant
            return body
        except Exception:
            return ''

    for asignacion in asignaciones:
        row_idx = start_row
        # datos izquierdos
        horario_txt = ''
        try:
            horario_txt = f"{asignacion.horario.hora_ingreso} - {asignacion.horario.hora_salida}"
        except Exception:
            horario_txt = ''
        inst = getattr(asignacion, 'instalacion', None)
        inst_codigo = getattr(inst, 'codigo', '') if inst else ''
        puesto_obj = getattr(asignacion, 'puesto', None)
        # Forzamos a usar la lógica compacta (coincide con la vista). Si falla, caemos al campo almacenado.
        resumen_val = build_resumen(puesto_obj) or getattr(puesto_obj, 'resumen', '')
        vals = [
            horario_txt,
            inst_codigo,
            getattr(asignacion.cliente, 'nombre_comercial', ''),
            getattr(puesto_obj, 'nombre', ''),
            resumen_val,
            getattr(getattr(asignacion, 'persona', None), 'cedula', ''),
            f"{getattr(asignacion.persona, 'apellidos', '')} {getattr(asignacion.persona, 'nombres', '')}",
            getattr(getattr(asignacion, 'persona', None), 'tipo', '')
        ]
        for ci, v in enumerate(vals, start=1):
            cell = ws.cell(row=row_idx, column=ci)
            cell.value = v
            cell.border = border

        # rellenar las celdas de cada día con datos de AsignacionSemanal (priorizando filas ligadas a la Asignacion)
        for di, d in enumerate(dates):
            col = date_start_col + di
            # calcular week_start usando bloques del mes (1, 8, 15, 22, 29),
            # consistente con la creación de AsignacionSemanal en el sistema.
            week_index = (d.day - 1) // 7
            week_start = first_day + datetime.timedelta(days=week_index * 7)
            legacy_week_start = d - datetime.timedelta(days=d.weekday())
            puesto_id = getattr(asignacion.puesto, 'id', getattr(asignacion, 'puesto_id', None))
            semanal = None
            # Primero intentamos encontrar una fila ligada específicamente a la asignación
            asign_key = ('a', getattr(asignacion, 'id', None), week_start)
            if asign_key in semanal_cache:
                semanal = semanal_cache[asign_key]
            else:
                try:
                    if getattr(asignacion, 'id', None):
                        semanal = AsignacionSemanal.objects.filter(asignacion_id=asignacion.id, week_start=week_start).first()
                        # Compatibilidad con filas antiguas guardadas por semana-lunes.
                        if not semanal:
                            legacy_asign_key = ('a', getattr(asignacion, 'id', None), legacy_week_start)
                            if legacy_asign_key in semanal_cache:
                                semanal = semanal_cache[legacy_asign_key]
                            else:
                                semanal = AsignacionSemanal.objects.filter(
                                    asignacion_id=asignacion.id,
                                    week_start=legacy_week_start
                                ).first()
                                semanal_cache[legacy_asign_key] = semanal
                    else:
                        semanal = None
                except Exception:
                    semanal = None
                semanal_cache[asign_key] = semanal

            # Si no hay fila ligada a la asignación, usamos la fila general por puesto (compatibilidad hacia atrás)
            if not semanal:
                puesto_key = ('p', puesto_id, week_start)
                if puesto_key in semanal_cache:
                    semanal = semanal_cache[puesto_key]
                else:
                    try:
                        semanal = AsignacionSemanal.objects.filter(puesto_id=puesto_id, week_start=week_start).first()
                        # Compatibilidad con filas antiguas guardadas por semana-lunes.
                        if not semanal:
                            legacy_puesto_key = ('p', puesto_id, legacy_week_start)
                            if legacy_puesto_key in semanal_cache:
                                semanal = semanal_cache[legacy_puesto_key]
                            else:
                                semanal = AsignacionSemanal.objects.filter(
                                    puesto_id=puesto_id,
                                    week_start=legacy_week_start
                                ).first()
                                semanal_cache[legacy_puesto_key] = semanal
                    except Exception:
                        semanal = None
                    semanal_cache[puesto_key] = semanal

            val = ''
            if semanal:
                day_field = ['mon','tue','wed','thu','fri','sat','sun'][d.weekday()]
                try:
                    val = getattr(semanal, day_field, '') or ''
                except Exception:
                    val = ''

            cell = ws.cell(row=row_idx, column=col)
            cell.value = val
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        start_row += 1

    # Ajustes de anchos de columna
    for i in range(1, left_cols + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 18
    # Nombre Puesto (columna 4) y Persona (columna 7) con mayor ancho
    ws.column_dimensions[openpyxl.utils.get_column_letter(4)].width = 28
    ws.column_dimensions[openpyxl.utils.get_column_letter(7)].width = 38
    for i in range(date_start_col, date_start_col + num_days):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 5

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=reporte_asignaciones_calendario_{year}_{month}.xlsx'
    wb.save(response)
    return response