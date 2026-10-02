"""Cierre de mes automático.

Los cambios que se hacen durante el mes se quedan en ese mes: NO se copian en vivo a los meses
siguientes. El mes siguiente se GENERA una sola vez, la última noche del mes, desde el estado
FINAL del mes que termina:

  - mismas personas en los mismos puestos y en el mismo ORDEN,
  - vacantes, estados y horarios,
  - sacafranco (con su vista y orden),
  - el CRONOGRAMA de cada persona (fijos, sacafranco y vacantes) continuando la secuencia donde
    terminó el mes.

El comando decide solo qué hacer según el día:
  - ÚLTIMO DÍA del mes: genera el mes siguiente (si ya existía una copia vieja, la re-alinea: queda
    igual al mes que termina; pisa lo que alguien haya cambiado a mano en ese mes siguiente).
  - Cualquier otro día: solo se asegura de que exista el mes ACTUAL (si falló el cierre de la noche
    anterior, lo crea desde el mes anterior para no empezar un mes vacío). No toca nada más.

Uso:
    python manage.py cierre_de_mes --dry-run                 # muestra lo que haría hoy, sin guardar
    python manage.py cierre_de_mes --hoy 2026-10-31 --dry-run  # simula la noche del 31 de octubre
    python manage.py cierre_de_mes --siguiente --dry-run     # fuerza generar el mes siguiente hoy
    python manage.py cierre_de_mes

Programarlo en el servidor (cron). Django usa la hora de Ecuador (America/Guayaquil) para saber qué
día es, pero cron usa la hora del SERVIDOR (revísala con `date`). Se busca que corra a las 23:55 de
Ecuador, todavía el último día del mes:
    # Si el servidor está en UTC (Ecuador = UTC-5): 23:55 de Ecuador son las 04:55 UTC
    55 4 * * *   docker exec sf_backend python manage.py cierre_de_mes >> /var/log/sf_cierre_mes.log 2>&1
    # Seguro a la 1:15 (hora de Ecuador = 06:15 UTC): crea el mes actual si falta
    15 6 * * *   docker exec sf_backend python manage.py cierre_de_mes >> /var/log/sf_cierre_mes.log 2>&1
"""
import calendar
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from CoreFisica.asignaciones_meses import asegurar_horizonte


class Command(BaseCommand):
    help = 'Cierre de mes: el último día genera el mes siguiente desde el estado final; otros días solo asegura el mes actual.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='No guarda: solo informa lo que haría.')
        parser.add_argument('--detalle', action='store_true', help='Muestra cada cambio.')
        parser.add_argument('--hoy', help='Fecha a usar como "hoy" (YYYY-MM-DD). Para pruebas o simulaciones.')
        parser.add_argument('--siguiente', action='store_true',
                            help='Genera el mes siguiente aunque hoy no sea el último día del mes.')

    def handle(self, *args, **opts):
        hoy = timezone.localdate()
        if opts['hoy']:
            try:
                hoy = datetime.date.fromisoformat(opts['hoy'])
            except ValueError:
                raise CommandError('--hoy debe ser YYYY-MM-DD')
        ultimo_dia = hoy.day == calendar.monthrange(hoy.year, hoy.month)[1]
        siguiente = ultimo_dia or opts['siguiente']
        log = (lambda m: self.stdout.write('      ' + m)) if opts['detalle'] else None
        dry = opts['dry_run']
        self.stdout.write(('PRUEBA (no se guarda nada)' if dry else 'GUARDANDO')
                          + f': hoy {hoy.isoformat()} - '
                          + ('se genera el MES SIGUIENTE desde el estado final de este mes'
                             if siguiente else 'solo se verifica que exista el mes actual'))
        with transaction.atomic():
            creados = asegurar_horizonte(hoy=hoy, meses_adelante=1 if siguiente else 0, log=log,
                                         alinear_existentes=siguiente)
            if dry:
                transaction.set_rollback(True)
        if not creados:
            self.stdout.write('Nada que crear: el mes ya existe.')
        for anio, mes, res in creados:
            resumen = ', '.join(f'{v} {n}' for n, v in res.items() if v) or 'sin cambios'
            self.stdout.write(f'  Mes {mes:02d}/{anio} generado: {resumen}')
        if dry:
            self.stdout.write('Prueba terminada: no se guardó nada.')
