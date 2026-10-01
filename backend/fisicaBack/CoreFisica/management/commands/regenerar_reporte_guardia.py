"""Regenera el Reporte de Guardia de un RANGO de días desde la asistencia de cada día.

Es lo mismo que pulsar "Regenerar desde asistencia" día por día. Sirve una sola vez para
llenar los días pasados (el reporte ya se llena solo al guardar la asistencia).

  python manage.py regenerar_reporte_guardia --desde 2026-09-01 --hasta 2026-09-30 --dry-run
  python manage.py regenerar_reporte_guardia --desde 2026-09-01 --hasta 2026-09-30

- Con --dry-run NO guarda nada: muestra cuántas filas automáticas tendría cada día.
- Conserva las filas manuales y las ediciones a mano. Vuelve a traer las filas automáticas
  que se habían eliminado a mano.
- Se puede repetir sin duplicar.
"""
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from CoreFisica.models import ReporteGuardia
from CoreFisica.views.reporte_guardia_views import regenerar_guardia_dia


def _fecha(v):
    try:
        return datetime.date.fromisoformat(v)
    except ValueError:
        raise CommandError(f'Fecha invalida: {v} (use YYYY-MM-DD)')


class Command(BaseCommand):
    help = 'Regenera el Reporte de Guardia de un rango de dias desde la asistencia de cada dia.'

    def add_arguments(self, parser):
        parser.add_argument('--desde', required=True, help='YYYY-MM-DD')
        parser.add_argument('--hasta', required=True, help='YYYY-MM-DD')
        parser.add_argument('--dry-run', action='store_true', help='No guarda: solo muestra lo que haria.')

    def handle(self, *args, **opts):
        desde, hasta = _fecha(opts['desde']), _fecha(opts['hasta'])
        if hasta < desde:
            raise CommandError('--hasta no puede ser anterior a --desde')
        dry = opts['dry_run']
        self.stdout.write(('PRUEBA (no se guarda nada)' if dry else 'GUARDANDO') + f': {desde} a {hasta}')
        total_antes = total_despues = errores = 0
        dia = desde
        with transaction.atomic():
            while dia <= hasta:
                antes = ReporteGuardia.objects.filter(fecha=dia, auto=True).count()
                res = regenerar_guardia_dia(dia)
                despues = ReporteGuardia.objects.filter(fecha=dia, auto=True).count()
                errores += res['errores']
                total_antes += antes
                total_despues += despues
                self.stdout.write(f'  {dia}: filas automaticas {antes} -> {despues}'
                                  + (f' | errores: {res["errores"]}' if res['errores'] else ''))
                dia += datetime.timedelta(days=1)
            if dry:
                transaction.set_rollback(True)
        self.stdout.write(f'TOTAL filas automaticas: {total_antes} -> {total_despues} | errores: {errores}')
        if dry:
            self.stdout.write('Prueba terminada: no se guardo nada.')
