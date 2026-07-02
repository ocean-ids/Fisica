"""Actualiza `proviene` = nombre de la instalación en las filas auto del
reporte de guardia (las que se generaron desde el reporte de asistencia antes
de que el sync usara la instalación). Idempotente.

Uso:  python manage.py backfill_proviene_guardia
"""
from django.core.management.base import BaseCommand
from CoreFisica.models import ReporteGuardia


class Command(BaseCommand):
    help = 'Pone proviene = nombre de la instalación en las filas auto del reporte de guardia.'

    def handle(self, *args, **options):
        qs = ReporteGuardia.objects.filter(auto=True).select_related(
            'reporte_asistencia__asignacion__instalacion'
        )
        actualizadas = 0
        for r in qs:
            ra = r.reporte_asistencia
            inst = getattr(getattr(getattr(ra, 'asignacion', None), 'instalacion', None), 'nombre', '') or ''
            if inst and r.proviene != inst:
                r.proviene = inst
                r.save(update_fields=['proviene'])
                actualizadas += 1
        self.stdout.write(self.style.SUCCESS(f'Filas actualizadas: {actualizadas}'))
