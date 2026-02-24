import os
import traceback
import datetime

print('Running inspect_patron.py')

try:
    from CoreFisica.models import Asignacion, PatronAsignacion, Puesto
except Exception as e:
    print('Error importing models:', e)
    raise


def detect_24h(asignacion, puesto_obj=None):
    try:
        is_24h = False
        if getattr(asignacion, 'horario', None):
            hi = asignacion.horario.hora_ingreso
            ho = asignacion.horario.hora_salida
            dt1 = datetime.datetime.combine(datetime.date(1,1,1), hi)
            dt2 = datetime.datetime.combine(datetime.date(1,1,1), ho)
            if dt2 <= dt1:
                dt2 += datetime.timedelta(days=1)
            dur = (dt2 - dt1).total_seconds() / 3600.0
            is_24h = dur >= 23.5
        if not is_24h and puesto_obj is not None:
            horarios_qs = getattr(puesto_obj, 'horarios', None)
            if horarios_qs is not None:
                horas_list = list(horarios_qs.values_list('horas', flat=True))
                is_24h = any((int(h) if h is not None else 0) == 24 for h in horas_list)
        return bool(is_24h)
    except Exception:
        traceback.print_exc()
        return False


def load_patron(pat):
    try:
        if not pat:
            return None, None
        patron = pat
        if patron and not hasattr(patron, 'secuencia'):
            try:
                patron = PatronAsignacion.objects.get(id=int(patron))
            except Exception:
                patron = None
        seq = None
        if patron and getattr(patron, 'secuencia', None):
            seq = [str(x).strip().upper() for x in patron.secuencia if x]
        return patron, seq
    except Exception:
        traceback.print_exc()
        return None, None


def main():
    try:
        asign_id = os.environ.get('ASIGN_ID')
        asign = None
        if asign_id:
            asign = Asignacion.objects.filter(id=int(asign_id)).first()
        if not asign:
            asign = Asignacion.objects.filter(estado='ACTIVO').first()
        if not asign:
            print('No Asignacion found (active). Provide ASIGN_ID env var to inspect a specific one.')
            return

        print(f'Inspecting Asignacion id={asign.id} persona={getattr(asign, "persona", None)} puesto={getattr(asign, "puesto", None)}')
        puesto_obj = None
        try:
            puesto_obj = getattr(asign, 'puesto')
            if isinstance(puesto_obj, (int, str)):
                puesto_obj = Puesto.objects.filter(id=int(puesto_obj)).first()
        except Exception:
            puesto_obj = None

        print('Asignacion fields: mes,anio,recurring,start_date,fecha,end_date')
        print(asign.mes, asign.anio, asign.recurring, getattr(asign, 'start_date', None), getattr(asign, 'fecha', None), getattr(asign, 'end_date', None))

        # print puesto horarios detail
        try:
            if puesto_obj is not None:
                horarios_qs = getattr(puesto_obj, 'horarios', None)
                if horarios_qs is not None:
                    horarios_list = list(horarios_qs.all())
                    print('\nPuesto.horarios count:', len(horarios_list))
                    for h in horarios_list:
                        print('  horario -> id:', getattr(h, 'id', None), 'dia:', getattr(h, 'dia', None), 'horas:', getattr(h, 'horas', None), 'turno:', getattr(h, 'turno', None))
                else:
                    print('\nPuesto.horarios: None')
            else:
                print('\nNo puesto_obj')
        except Exception:
            traceback.print_exc()

        patron, seq = load_patron(getattr(asign, 'patronAsignacion', None))
        print('Patron:', getattr(patron, 'id', None), 'raw_sequence:', getattr(patron, 'secuencia', None))
        print('Parsed seq:', seq)

        # compute ref_date
        ref_date = None
        if asign.start_date:
            ref_date = asign.start_date
        elif getattr(asign, 'fecha', None):
            ref_date = asign.fecha
        else:
            try:
                ref_date = datetime.date(int(asign.anio), int(asign.mes), 1)
            except Exception:
                ref_date = datetime.date.today()
        print('ref_date:', ref_date)

        is_24h = detect_24h(asign, puesto_obj)
        print('is_24h detected:', is_24h)

        offset = 0
        if is_24h and seq:
            first = seq[0]
            cnt = 0
            for s in seq:
                if s == first:
                    cnt += 1
                else:
                    break
            offset = cnt
        print('offset applied:', offset)

        print('\nDay | date | days_diff | applies_by_puesto | active | idx_seq | value | reason')
        # prepare dias_norm and dias_nums like views
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

        dias_puesto = []
        try:
            if puesto_obj:
                if hasattr(puesto_obj, 'dias') and getattr(puesto_obj, 'dias'):
                    dias_puesto = puesto_obj.dias or []
                else:
                    horarios_qs = getattr(puesto_obj, 'horarios', None)
                    if horarios_qs is not None:
                        dias_nums_local = list(horarios_qs.values_list('dia', flat=True))
                        day_map = {1: 'lunes', 2: 'martes', 3: 'miercoles', 4: 'jueves', 5: 'viernes', 6: 'sabado', 7: 'domingo'}
                        dias_puesto = [day_map.get(n, '') for n in dias_nums_local if n]
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

        print('\ndias_puesto (names):', dias_puesto)
        print('dias_norm:', dias_norm)
        print('dias_nums:', dias_nums)

        for i in range(0, 21):
            day_date = ref_date + datetime.timedelta(days=i)
            days_diff = (day_date - ref_date).days
            name = day_date.strftime('%A').lower()

            # applies_by_puesto calculation
            if dias_nums:
                applies_by_puesto = (day_date.isoweekday() in dias_nums)
                reason = f'dias_nums match ({day_date.isoweekday()} in {dias_nums})'
            else:
                applies_by_puesto = any(name == d or d in name or name in d for d in dias_norm) or (not dias_norm and bool(seq))
                reason = f'dias_norm match: {dias_norm}' if dias_norm else ('fallback to seq exists' if seq else 'no dias_norm and no seq')

            # active check
            active = True
            if asign.recurring:
                if asign.start_date and day_date < asign.start_date:
                    active = False
                if asign.end_date and asign.end_date and day_date > asign.end_date:
                    active = False
            else:
                if getattr(asign, 'fecha', None):
                    active = (day_date == asign.fecha)
                else:
                    active = (day_date.month == asign.mes and day_date.year == asign.anio)

            idx_seq = '-'
            val = None
            if seq and active and applies_by_puesto:
                idx_seq = (days_diff + offset) % len(seq)
                val = seq[idx_seq]

            print(f'{i:2d} | {day_date} | {days_diff:3d} | {applies_by_puesto!s:5} | {active!s:5} | {idx_seq:>3} | {val:5} | {reason}')

    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main()
