from ..models import AsignacionSemanal, SacafrancoFilaSemanal, CoberturaSacafranco
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from ..serializers import AsignacionSemanalSerializer, SacafrancoFilaSemanalSerializer
from django.db import transaction
from datetime import datetime, date, timedelta


def _puesto_detalle_dict(puesto):
    return {
        'id': puesto.id,
        'nombre': puesto.nombre,
        'cantidad_puestos': puesto.cantidad_puestos,
        'zona_id': getattr(puesto, 'zona_id', None),
        'zona_titulo': getattr(getattr(puesto, 'zona', None), 'titulo', ''),
        'turno': puesto.get_turno(),
        'turno_display': puesto.get_turno_display(),
        'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in puesto.horarios.all()],
        'resumen': puesto.resumen,
    }


def _overlay_coberturas_sacafranco(rows, week_start_date):
    coberturas = list(
        CoberturaSacafranco.objects.filter(week_start=week_start_date)
        .select_related('puesto', 'puesto__zona')
        .prefetch_related('puesto__horarios')
        .order_by('puesto_id', 'day')
    )
    if not coberturas:
        return rows

    rows_by_puesto = {}
    for row in rows:
        puesto_id = row.get('puesto')
        if puesto_id is not None and puesto_id not in rows_by_puesto:
            rows_by_puesto[puesto_id] = row

    for cobertura in coberturas:
        row = rows_by_puesto.get(cobertura.puesto_id)
        if row is None:
            # No crear filas nuevas solo por cobertura sacafranco.
            continue

        current_value = str(row.get(cobertura.day) or '').strip()
        if current_value == '':
            row[cobertura.day] = 'F'

    return rows


def _auto_create_asignacion_semanal_for_week(week_start_date, provincia_id=None):
    try:
        from ..models import Asignacion, Puesto
        asigns = Asignacion.objects.filter(estado='ACTIVO').exclude(persona__tipo='SACAFRANCO').filter(
            Q(mes=week_start_date.month, anio=week_start_date.year) |
            (Q(recurring=True) & Q(start_date__lte=week_start_date) & (Q(end_date__isnull=True) | Q(end_date__gte=week_start_date)))
        ).select_related('puesto', 'patronAsignacion')
        if provincia_id is not None:
            asigns = asigns.filter(instalacion__canton__provincia_id=provincia_id)

        weekday_names = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']

        def normalize_day_token(tok: str) -> str:
            t = str(tok).strip().lower()
            if not t:
                return ''
            map_short = {
                'l': 'lunes', 'lu': 'lunes', 'lun': 'lunes', 'lunes': 'lunes',
                'm': 'martes', 'ma': 'martes', 'mar': 'martes', 'martes': 'martes',
                'mi': 'miercoles', 'mie': 'miercoles', 'miercoles': 'miercoles', 'miércoles': 'miercoles',
                'j': 'jueves', 'ju': 'jueves', 'jue': 'jueves', 'jueves': 'jueves',
                'v': 'viernes', 'vi': 'viernes', 'vie': 'viernes', 'viernes': 'viernes',
                's': 'sabado', 'sa': 'sabado', 'sab': 'sabado', 'sabado': 'sabado', 'sábado': 'sabado',
                'd': 'domingo', 'do': 'domingo', 'dom': 'domingo', 'domingo': 'domingo'
            }
            return map_short.get(t, t)

        for asign in asigns:
            puesto_obj = getattr(asign, 'puesto', None)
            if not puesto_obj:
                try:
                    puesto_obj = Puesto.objects.get(id=asign.puesto_id)
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

            dias_norm = [normalize_day_token(d) for d in dias_puesto if d]
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

            turno_val = (getattr(puesto_obj, 'turno', '') or '').strip().lower() if puesto_obj else ''
            default_code = 'N' if turno_val.startswith('n') else 'D'

            patron = getattr(asign, 'patronAsignacion', None)
            seq = None
            if patron and getattr(patron, 'secuencia', None):
                try:
                    seq = [str(x).strip().upper() for x in patron.secuencia if x]
                except Exception:
                    seq = None

            defaults = {}
            for idx in range(7):
                day_date = week_start_date + timedelta(days=idx)
                name = weekday_names[day_date.weekday()]
                weekday_keys = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                key = weekday_keys[day_date.weekday()]

                if seq:
                    applies_by_puesto = True
                elif dias_nums:
                    applies_by_puesto = (day_date.isoweekday() in dias_nums)
                else:
                    applies_by_puesto = any(name == d or d in name or name in d for d in dias_norm)

                value = ''
                if seq:
                    ref_date = None
                    if asign.start_date:
                        ref_date = asign.start_date
                    elif getattr(asign, 'fecha', None):
                        ref_date = asign.fecha
                    else:
                        try:
                            ref_date = date(asign.anio, asign.mes, 1)
                        except Exception:
                            ref_date = week_start_date

                    active = True
                    if asign.recurring:
                        if asign.start_date and day_date < asign.start_date:
                            active = False
                        if asign.end_date and day_date > asign.end_date:
                            active = False
                    else:
                        if getattr(asign, 'fecha', None):
                            active = (day_date == asign.fecha)
                        else:
                            active = (day_date.month == asign.mes and day_date.year == asign.anio)

                    if active and applies_by_puesto:
                        try:
                            days_diff = (day_date - ref_date).days
                            offset = 0
                            try:
                                is_24h = False
                                try:
                                    if getattr(asign, 'horario', None):
                                        hi = asign.horario.hora_ingreso
                                        ho = asign.horario.hora_salida
                                        dt1 = datetime.combine(date(1, 1, 1), hi)
                                        dt2 = datetime.combine(date(1, 1, 1), ho)
                                        if dt2 <= dt1:
                                            dt2 += timedelta(days=1)
                                        dur = (dt2 - dt1).total_seconds() / 3600.0
                                        is_24h = dur >= 23.5
                                except Exception:
                                    is_24h = False
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

            if puesto_obj:
                pid = puesto_obj.id if hasattr(puesto_obj, 'id') else puesto_obj
                try:
                    obj, created = AsignacionSemanal.objects.get_or_create(
                        asignacion_id=asign.id,
                        week_start=week_start_date,
                        defaults={**defaults, 'asignacion': asign, 'puesto_id': pid}
                    )
                    if not created:
                        changed = False
                        if getattr(obj, 'asignacion_id', None) is None:
                            obj.asignacion = asign
                            changed = True
                        for k, v in defaults.items():
                            try:
                                cur = getattr(obj, k, '')
                            except Exception:
                                cur = ''
                            cur_str = str(cur or '').strip()
                            if (cur_str == '' or cur is None) and v:
                                setattr(obj, k, v)
                                changed = True
                        if changed:
                            obj.save()
                except Exception as e:
                    print(f"⚠️ Error creando/actualizando AsignacionSemanal (puesto {pid}, week_start {week_start_date}): {e}")
    except Exception as e:
        print(f"⚠️ Error asegurando AsignacionSemanal para week_start {week_start_date}: {e}")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_asignacion_semanal(request):
    """Listar asignaciones semanales. Filtrar por week_start (YYYY-MM-DD) y opcionalmente por cliente."""
    if not request.user.has_perm('CoreFisica.view_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)


    week_start = request.GET.get('week_start')
    cliente_id = request.GET.get('cliente')
    provincia_id = request.GET.get('provincia_id')
    turno = request.GET.get('turno')
    q = (request.GET.get('q') or '').strip()
    lite = str(request.GET.get('lite', 'false')).lower() in ['true', '1', 'yes']
    auto_create = str(request.GET.get('auto_create', 'true')).lower() in ['true', '1', 'yes']

    qs = AsignacionSemanal.objects.select_related(
        'puesto',
        'puesto__zona',
        'asignacion__persona'
    ).prefetch_related('puesto__horarios')
    if week_start:
        try:
            ws = datetime.fromisoformat(week_start).date()
            # Antes de listar, opcionalmente crear filas semanales para los puestos
            # que tengan asignaciones activas o recurrentes que apliquen a esta semana.
            active_asign_ids = set()
            if auto_create:
                try:
                    from ..models import Asignacion, Puesto
                    # encontrar asignaciones activas que aplican a esta semana
                    asigns = Asignacion.objects.filter(estado='ACTIVO').exclude(persona__tipo='SACAFRANCO').filter(
                        Q(mes=ws.month, anio=ws.year) |
                        (Q(recurring=True) & Q(start_date__lte=ws) & (Q(end_date__isnull=True) | Q(end_date__gte=ws)))
                    ).select_related('puesto', 'patronAsignacion')
                    active_asign_ids = set(asigns.values_list('id', flat=True))
                    # weekday_names para normalizar tokens de días y compararlos con días del puesto o patrón sin depender de idioma o formato exacto.
                    weekday_names = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
                    # funcion para normalizar tokens de dias a formato estándar (ej: 'lun', 'Lunes' -> 'lunes') 
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
                    # itera las asignaciones activas y asegura que exista una fila semanal para el
                    for asign in asigns:
                    
                        puesto_obj = getattr(asign, 'puesto', None)
                        # si no se obtiene puesto relacionado, intentar por puesto_id (caso de asignaciones sin relación correcta pero con puesto_id presente)
                        if not puesto_obj:
                            try:
                                puesto_obj = Puesto.objects.get(id=asign.puesto_id)
                            except Exception:
                                puesto_obj = None
                        #
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
                        dias_norm = [normalize_day_token(d) for d in dias_puesto if d]
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

                        # Si la asignación tiene un patrón definido, construir la secuencia continua
                        patron = getattr(asign, 'patronAsignacion', None)
                        seq = None
                        if patron and getattr(patron, 'secuencia', None):
                            try:
                                seq = [str(x).strip().upper() for x in patron.secuencia if x]
                            except Exception:
                                seq = None

                        defaults = {}
                        for idx in range(7):
                            day_date = ws + timedelta(days=idx)
                            name = weekday_names[day_date.weekday()]
                            weekday_keys = ['mon','tue','wed','thu','fri','sat','sun']
                            key = weekday_keys[day_date.weekday()]

                            # Si hay patrón, el ciclo se aplica de forma continua por día.
                            if seq:
                                applies_by_puesto = True
                            # Sin patrón: respetar días/horarios del puesto.
                            elif dias_nums:
                                applies_by_puesto = (day_date.isoweekday() in dias_nums)
                            else:
                                applies_by_puesto = any(name == d or d in name or name in d for d in dias_norm)

                            value = ''
                            # si hay patrón y la asignación está activa ese día, calcular token según ciclo continuo
                            if seq:
                                # determinar fecha de inicio para indexación: start_date > fecha > week_start
                                ref_date = None
                                if asign.start_date:
                                    ref_date = asign.start_date
                                elif getattr(asign, 'fecha', None):
                                    ref_date = asign.fecha
                                else:
                                    # fallback: use the first day of the month-year where asign applies or week_start
                                    try:
                                        ref_date = date(asign.anio, asign.mes, 1)
                                    except Exception:
                                        ref_date = ws

                                # si the day_date is within asign's active window
                                active = True
                                if asign.recurring:
                                    if asign.start_date and day_date < asign.start_date:
                                        active = False
                                    if asign.end_date and asign.end_date and day_date > asign.end_date:
                                        active = False
                                else:
                                    # non-recurring: match by mes/anio or fecha
                                    if getattr(asign, 'fecha', None):
                                        active = (day_date == asign.fecha)
                                    else:
                                        active = (day_date.month == asign.mes and day_date.year == asign.anio)

                                if active and applies_by_puesto:
                                    try:
                                        days_diff = (day_date - ref_date).days
                                        # detectar 24h: preferir horario de la asignación
                                        offset = 0
                                        try:
                                            is_24h = False
                                            try:
                                                if getattr(asign, 'horario', None):
                                                    hi = asign.horario.hora_ingreso
                                                    ho = asign.horario.hora_salida
                                                    dt1 = datetime.combine(date(1,1,1), hi)
                                                    dt2 = datetime.combine(date(1,1,1), ho)
                                                    if dt2 <= dt1:
                                                        dt2 += timedelta(days=1)
                                                    dur = (dt2 - dt1).total_seconds() / 3600.0
                                                    is_24h = dur >= 23.5
                                            except Exception:
                                                is_24h = False
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
                                # sin patrón, usar comportamiento previo (turno por puesto)
                                if applies_by_puesto:
                                    value = default_code

                            defaults[key] = value

                        if puesto_obj:
                            pid = puesto_obj.id if hasattr(puesto_obj, 'id') else puesto_obj
                            # Intentar obtener/crear por puesto+week_start (único). Si ya existe pero no tiene
                            # asignacion vinculada, ligar la asignación; si existe y ya tiene asignacion, no crear duplicado.
                            try:
                                obj, created = AsignacionSemanal.objects.get_or_create(
                                    asignacion_id=asign.id,
                                    week_start=ws,
                                    defaults={**defaults, 'asignacion': asign, 'puesto_id': pid}
                                )
                                if not created:
                                    changed = False
                                    # solo enlazar asignación si no hay una ya ligada (no pisar sacafranco u otras)
                                    if getattr(obj, 'asignacion_id', None) is None:
                                        obj.asignacion = asign
                                        changed = True
                                    # rellenar solo celdas vacías para no sobreescribir 'F' u otros códigos existentes
                                    for k, v in defaults.items():
                                        try:
                                            cur = getattr(obj, k, '')
                                        except Exception:
                                            cur = ''
                                        cur_str = str(cur or '').strip()
                                        if (cur_str == '' or cur is None) and v:
                                            setattr(obj, k, v)
                                            changed = True
                                    if changed:
                                        obj.save()
                            except Exception as e:
                                # imprimir el error y continuar
                                print(f"⚠️ Error creando/actualizando AsignacionSemanal (puesto {pid}, week_start {ws}): {e}")

                except Exception as e:
                    print(f"⚠️ Error asegurando AsignacionSemanal para week_start {week_start}: {e}")

            if not auto_create:
                try:
                    from ..models import Asignacion
                    active_asigns = Asignacion.objects.filter(estado='ACTIVO').exclude(persona__tipo='SACAFRANCO').filter(
                        Q(mes=ws.month, anio=ws.year) |
                        (Q(recurring=True) & Q(start_date__lte=ws) & (Q(end_date__isnull=True) | Q(end_date__gte=ws)))
                    )
                    active_asign_ids = set(active_asigns.values_list('id', flat=True))
                except Exception:
                    active_asign_ids = set()

            qs = qs.filter(week_start=ws)
            if active_asign_ids:
                qs = qs.filter(asignacion_id__in=active_asign_ids)
            else:
                qs = qs.none()
        except Exception:
            return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    #si el cliente_id se proporciona como filtro, aplicarlo al queryset después de filtrar por semana para optimizar la consulta y evitar crear filas semanales innecesarias para clientes no relacionados.
    if cliente_id:
        qs = qs.filter(puesto__instalacion__cliente_id=cliente_id)
    # si se proporciona un término de búsqueda, aplicarlo a campos relevantes de asignación, persona y puesto. Esto se hace después de filtrar por semana para optimizar la consulta.
    if q:
        filtros = (
            Q(asignacion__cliente__nombre_comercial__icontains=q) |
            Q(asignacion__cliente__razon_social__icontains=q) |
            Q(asignacion__persona__cedula__icontains=q) |
            Q(asignacion__persona__nombres__icontains=q) |
            Q(asignacion__persona__apellidos__icontains=q) |
            Q(puesto__nombre__icontains=q)
        )
        # Si el término de búsqueda es un número, también buscar por ID de asignación o ID de fila semanal para facilitar acceso directo.
        if q.isdigit():
            filtros = filtros | Q(id=int(q)) | Q(asignacion_id=int(q))
        qs = qs.filter(filtros).distinct()
    # ordena por asignacion_id para matener un orden consistente, especialmente al aplicar filtros
    qs = qs.order_by('asignacion_id')
    # si se proporciona filtro de turno, aplicarlo al queryset para mostrar solo filas semanales cuyos puestos tengan ese turno. Esto se hace al final para no afectar la creación automática de filas semanales basada en asignaciones activas.
    if turno in ['Diurno', 'Nocturno']:
        qs = qs.filter(puesto__horarios__turno=turno).distinct()
    #serializa y devuelve los resultados, si se proporciono week_start, aplicar overlay de coberturas sacafranco para marcar días con cobertura aunque no tengan asignación activa.
    if lite:
        rows = list(qs.values(
            'id',
            'asignacion_id',
            'puesto_id',
            'week_start',
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
        ))
    else:
        serializer = AsignacionSemanalSerializer(qs, many=True)
        rows = list(serializer.data)
    if week_start:
        rows = _overlay_coberturas_sacafranco(rows, ws)
    return Response(rows)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_asignacion_semanal_mes(request):
    """Listar asignaciones semanales para todo un mes en una sola respuesta."""
    if not request.user.has_perm('CoreFisica.view_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    mes = request.GET.get('mes')
    anio = request.GET.get('anio')
    cliente_id = request.GET.get('cliente')
    provincia_id = request.GET.get('provincia_id')
    turno = request.GET.get('turno')
    q = (request.GET.get('q') or '').strip()
    lite = str(request.GET.get('lite', 'false')).lower() in ['true', '1', 'yes']
    include_sacafranco = str(request.GET.get('include_sacafranco', 'true')).lower() in ['true', '1', 'yes']
    auto_create = str(request.GET.get('auto_create', 'true')).lower() in ['true', '1', 'yes']

    if not mes or not anio:
        return Response({'error': 'mes y año invalidos son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        mes = int(mes)
        anio = int(anio)
        if not (1 <= mes <= 12):
            raise ValueError
    except ValueError:
        return Response({'error': 'mes o anio inválidos'}, status=status.HTTP_400_BAD_REQUEST)

    first_day = date(anio, mes, 1)
    last_day = date(anio, mes + 1, 1) - timedelta(days=1) if mes < 12 else date(anio, 12, 31)

    weeks = []
    current = first_day
    while current.month == mes:
        weeks.append(current)
        current += timedelta(days=7)

    prov_id = None
    if provincia_id:
        try:
            prov_id = int(provincia_id)
        except (TypeError, ValueError):
            return Response({'error': 'Provincia invalida'}, status=status.HTTP_400_BAD_REQUEST)

    if auto_create:
        for ws in weeks:
            base_qs = AsignacionSemanal.objects.filter(week_start=ws)
            if prov_id is not None:
                base_qs = base_qs.filter(puesto__instalacion__canton__provincia_id=prov_id)
            if base_qs.exists():
                continue
            _auto_create_asignacion_semanal_for_week(ws, provincia_id=prov_id)

    qs = AsignacionSemanal.objects.select_related(
        'puesto',
        'puesto__zona',
        'asignacion__persona'
    ).prefetch_related('puesto__horarios')
    qs = qs.filter(week_start__in=weeks)
    if cliente_id:
        qs = qs.filter(puesto__instalacion__cliente_id=cliente_id)
    if prov_id is not None:
        qs = qs.filter(puesto__instalacion__canton__provincia_id=prov_id)
    if q:
        filtros = (
            Q(asignacion__cliente__nombre_comercial__icontains=q) |
            Q(asignacion__cliente__razon_social__icontains=q) |
            Q(asignacion__persona__cedula__icontains=q) |
            Q(asignacion__persona__nombres__icontains=q) |
            Q(asignacion__persona__apellidos__icontains=q) |
            Q(puesto__nombre__icontains=q)
        )
        if q.isdigit():
            filtros = filtros | Q(id=int(q)) | Q(asignacion_id=int(q))
        qs = qs.filter(filtros).distinct()
    if turno in ['Diurno', 'Nocturno']:
        qs = qs.filter(puesto__horarios__turno=turno).distinct()
    qs = qs.order_by('asignacion_id', 'week_start')

    if lite:
        rows = list(qs.values(
            'id',
            'asignacion',
            'puesto',
            'week_start',
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
        ))
    else:
        serializer = AsignacionSemanalSerializer(qs, many=True)
        rows = list(serializer.data)

    active_ids_by_week = {}
    try:
        from ..models import Asignacion
        assigns = list(
            Asignacion.objects.filter(estado='ACTIVO')
            .exclude(persona__tipo='SACAFRANCO')
            .filter(
                Q(mes=mes, anio=anio) |
                (Q(recurring=True) & Q(start_date__lte=last_day) & (Q(end_date__isnull=True) | Q(end_date__gte=first_day)))
            )
        )
        for ws in weeks:
            ids = set()
            for asign in assigns:
                if asign.recurring:
                    if asign.start_date and ws < asign.start_date:
                        continue
                    if asign.end_date and ws > asign.end_date:
                        continue
                    ids.add(asign.id)
                else:
                    if asign.mes == ws.month and asign.anio == ws.year:
                        ids.add(asign.id)
            active_ids_by_week[ws.isoformat()] = ids
    except Exception:
        active_ids_by_week = {}

    weeks_map = {ws.isoformat(): {'asignaciones': [], 'sacafranco': []} for ws in weeks}
    for row in rows:
        ws = row.get('week_start')
        ws_key = ws.isoformat() if isinstance(ws, date) else str(ws)
        if ws_key not in weeks_map:
            continue
        if active_ids_by_week:
            asig_id = row.get('asignacion') or row.get('asignacion_id')
            if asig_id not in active_ids_by_week.get(ws_key, set()):
                continue
        weeks_map[ws_key]['asignaciones'].append(row)

    if include_sacafranco and weeks:
        sac_qs = SacafrancoFilaSemanal.objects.filter(week_start__in=weeks)
        sac_rows = list(SacafrancoFilaSemanalSerializer(sac_qs, many=True).data)
        for row in sac_rows:
            ws_key = str(row.get('week_start'))
            if ws_key in weeks_map:
                weeks_map[ws_key]['sacafranco'].append(row)

    for ws_key, bucket in weeks_map.items():
        try:
            ws_date = datetime.fromisoformat(ws_key).date()
            bucket['asignaciones'] = _overlay_coberturas_sacafranco(bucket['asignaciones'], ws_date)
        except Exception:
            continue

    return Response({'weeks': weeks_map})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def semanas_del_mes(request):
    """
    obtener parametros: mes 1-12, año(yyyy)
    Retorna: { weeks: ['YYYY-MM-DD', ...] }
    """
    # si el usuario no tiene permiso para ver asignaciones semanales, devolver error 403 antes de procesar parámetros
    if not request.user.has_perm('CoreFisica.view_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    mes = request.GET.get('mes')
    anio = request.GET.get('anio')

    if not mes or not anio:
        return Response({'error': 'mes y año invalidos son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        mes = int(mes)
        anio = int(anio)
        if not (1 <= mes <=12):
            raise ValueError
    except ValueError:
        return Response({'error': 'mes o anio inválidos'}, status=status.HTTP_400_BAD_REQUEST)

    first_day = date(anio, mes, 1)
    current = first_day

    weeks = []
    while current.month == mes:
        weeks.append(current.isoformat())
        current += timedelta(days=7)

    return Response({'weeks': weeks})



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_o_actualizar_asignacion_semanal(request):
    """Crea o actualiza una fila semanal (unicidad por puesto+week_start)."""
    if not request.user.has_perm('CoreFisica.change_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    data = request.data
    puesto_id = data.get('puesto')
    week_start = data.get('week_start')
    asignacion_id = data.get('asignacion_id')
    if not puesto_id or not week_start:
        return Response({'error': 'Faltan campos puesto o week_start'}, status=status.HTTP_400_BAD_REQUEST)
    if not asignacion_id:
        return Response({'error': 'asignacion_id es requerido para guardar calendario semanal'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ws = datetime.fromisoformat(week_start).date()
    except Exception:
        return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # preparar defaults solo con los días que vienen en el payload
            defaults = {}
            for d in ['mon','tue','wed','thu','fri','sat','sun']:
                if d in data:
                    defaults[d] = data.get(d) or ''
            defaults['asignacion_id'] = asignacion_id

            obj, created = AsignacionSemanal.objects.get_or_create(asignacion_id=asignacion_id, week_start=ws, defaults={**defaults, 'puesto_id': puesto_id})

            # Si no se creó (existía), actualizar campos proporcionados y ligar asignacion si se indicó
            if not created:
                for d in ['mon','tue','wed','thu','fri','sat','sun']:
                    if d in data:
                        setattr(obj, d, data.get(d) or '')
                if getattr(obj, 'asignacion_id', None) != int(asignacion_id):
                    obj.asignacion_id = asignacion_id
                obj.save()

            serializer = AsignacionSemanalSerializer(obj)
            return Response({'created': created, 'result': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_sacafranco_fila_semanal(request):
    if not request.user.has_perm('CoreFisica.view_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    week_start = request.GET.get('week_start')
    if not week_start:
        return Response({'error': 'week_start es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ws = datetime.fromisoformat(week_start).date()
    except Exception:
        return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    qs = SacafrancoFilaSemanal.objects.select_related('sacafranco_fila').filter(week_start=ws)
    serializer = SacafrancoFilaSemanalSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_o_actualizar_sacafranco_fila_semanal(request):
    if not request.user.has_perm('CoreFisica.change_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    data = request.data
    sacafranco_fila_id = data.get('sacafranco_fila')
    week_start = data.get('week_start')
    if not sacafranco_fila_id or not week_start:
        return Response({'error': 'Faltan campos sacafranco_fila o week_start'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ws = datetime.fromisoformat(week_start).date()
    except Exception:
        return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            defaults = {}
            for d in ['mon','tue','wed','thu','fri','sat','sun']:
                if d in data:
                    defaults[d] = data.get(d) or ''

            obj, created = SacafrancoFilaSemanal.objects.get_or_create(
                sacafranco_fila_id=sacafranco_fila_id,
                week_start=ws,
                defaults={**defaults, 'sacafranco_fila_id': sacafranco_fila_id}
            )

            if not created:
                for d in ['mon','tue','wed','thu','fri','sat','sun']:
                    if d in data:
                        setattr(obj, d, data.get(d) or '')
                obj.save()

            serializer = SacafrancoFilaSemanalSerializer(obj)
            return Response({'created': created, 'result': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def copiar_semana(request):
    """Copiar semana: payload {from_week, to_week, cliente (opcional)}"""
    if not request.user.has_perm('CoreFisica.change_asignacionsemanal'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    payload = request.data
    from_week = payload.get('from_week')
    to_week = payload.get('to_week')
    cliente_id = payload.get('cliente')
    if not from_week or not to_week:
        return Response({'error': 'from_week y to_week son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        fw = datetime.fromisoformat(from_week).date()
        tw = datetime.fromisoformat(to_week).date()
    except Exception:
        return Response({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    qs = AsignacionSemanal.objects.filter(week_start=fw)
    if cliente_id:
        qs = qs.filter(puesto__instalacion__cliente_id=cliente_id)

    created = 0
    updated = 0
    with transaction.atomic():
        for row in qs:
            if not getattr(row, 'asignacion_id', None):
                continue
            obj, was_created = AsignacionSemanal.objects.update_or_create(
                asignacion_id=row.asignacion_id,
                week_start=tw,
                defaults={
                    'mon': row.mon,
                    'tue': row.tue,
                    'wed': row.wed,
                    'thu': row.thu,
                    'fri': row.fri,
                    'sat': row.sat,
                    'sun': row.sun,
                    'puesto_id': getattr(row, 'puesto_id', None),
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

    return Response({'created': created, 'updated': updated, 'copied_from': str(fw), 'copied_to': str(tw)})
