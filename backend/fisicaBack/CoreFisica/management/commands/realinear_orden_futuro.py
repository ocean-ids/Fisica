"""Re-propaga el orden del mes presente (o uno dado) hacia los meses FUTUROS.

Cada asignación futura toma el orden EXACTO de su (puesto, persona) en el mes de
referencia; si esa persona no estaba en ese puesto en el mes de referencia, usa el
orden mínimo de ese puesto como respaldo. No toca meses pasados.

Uso:
    python manage.py realinear_orden_futuro            # usa el mes/año de hoy
    python manage.py realinear_orden_futuro --mes 6 --anio 2026
    python manage.py realinear_orden_futuro --dry-run
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from CoreFisica.models import Asignacion


class Command(BaseCommand):
    help = 'Propaga el orden del mes presente (o dado) hacia los meses futuros, fila por fila (puesto, persona).'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, default=None)
        parser.add_argument('--anio', type=int, default=None)
        parser.add_argument('--dry-run', action='store_true', help='No guarda; solo informa cuántas cambiarían.')

    def handle(self, *args, **opts):
        hoy = timezone.localdate()
        mes = opts['mes'] or hoy.month
        anio = opts['anio'] or hoy.year

        ref = Asignacion.objects.filter(estado='ACTIVO', mes=mes, anio=anio)
        orden_by_pp = {}
        orden_by_puesto = {}
        for a in ref.only('puesto_id', 'persona_id', 'orden'):
            if a.puesto_id is None:
                continue
            orden_by_pp[(a.puesto_id, a.persona_id)] = a.orden
            if a.puesto_id not in orden_by_puesto or a.orden < orden_by_puesto[a.puesto_id]:
                orden_by_puesto[a.puesto_id] = a.orden

        if not orden_by_puesto:
            self.stdout.write(self.style.WARNING(f'No hay asignaciones de referencia en {mes}/{anio}.'))
            return

        fut = (Asignacion.objects
               .filter(estado='ACTIVO')
               .filter(Q(anio__gt=anio) | Q(anio=anio, mes__gt=mes))
               .filter(puesto_id__in=list(orden_by_puesto.keys())))

        cambios = []
        for a in fut.only('id', 'orden', 'puesto_id', 'persona_id'):
            nv = orden_by_pp.get((a.puesto_id, a.persona_id))
            if nv is None:
                nv = orden_by_puesto.get(a.puesto_id)
            if nv is not None and a.orden != nv:
                a.orden = nv
                cambios.append(a)

        if opts['dry_run']:
            self.stdout.write(self.style.NOTICE(
                f'[dry-run] Cambiarían {len(cambios)} asignaciones futuras desde {mes}/{anio}.'))
            return

        if cambios:
            Asignacion.objects.bulk_update(cambios, ['orden'], batch_size=1000)
        self.stdout.write(self.style.SUCCESS(
            f'Reordenadas {len(cambios)} asignaciones futuras desde {mes}/{anio}.'))
