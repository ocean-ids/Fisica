"""Hace que los meses SIGUIENTES a un mes base queden igual que ese mes.

Al importar el Excel de asignaciones, el sistema copia las asignaciones a los meses
siguientes; esas copias no se actualizaban cuando después se editaba el mes base. Este
comando las vuelve a alinear (ver CoreFisica/asignaciones_meses.py):

  1. REGISTROS: cada persona del mes base queda en el mismo puesto, con el mismo orden,
     horario y estado en los meses siguientes (se crea la fila si no existía).
  2. SOBRANTES: se desactiva la fila que sobra en un puesto (FIJOS que ya no están, vacantes).
     RETEN / SACAVACACIONES / SACAFRANCO que solo existen en el mes siguiente no se tocan.
  3. CRONOGRAMA: el turno de cada persona continúa la secuencia donde terminó el mes base.
     Un cronograma con cambios a mano (vacaciones, coberturas) no se toca.
  4. SACAFRANCO: misma vista, orden, provincia y horario que en el mes base (se crean los
     que faltan). Los que solo existen en el mes siguiente se informan; para eliminarlos use
     --quitar-sacafranco-sobrantes.
  0. Las filas recurrentes con fecha de fin vacía se acotan al fin de su mes.

Las pestañas / vistas personalizadas de Asignaciones son filtros guardados que usan el mismo
orden global: al igualar registros y orden, todas las vistas quedan iguales al mes base.

No borra nada: solo actualiza, crea o desactiva (INACTIVO). Se puede repetir.

Uso:
    python manage.py continuar_meses_desde --mes 9 --anio 2026 --dry-run
    python manage.py continuar_meses_desde --mes 9 --anio 2026
    python manage.py continuar_meses_desde --mes 9 --anio 2026 --meses 24 --detalle
"""
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from CoreFisica.asignaciones_meses import MESES_POR_DEFECTO, alinear_meses
from CoreFisica.models import Asignacion


class Command(BaseCommand):
    help = 'Alinea los meses siguientes con un mes base (registros, orden y cronograma).'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, required=True, help='Mes base (1-12)')
        parser.add_argument('--anio', type=int, required=True, help='Año del mes base')
        parser.add_argument('--meses', type=int, default=MESES_POR_DEFECTO,
                            help=f'Cuántos meses siguientes revisar ({MESES_POR_DEFECTO} por defecto: los que tienen copia completa)')
        parser.add_argument('--dry-run', action='store_true', help='No guarda: solo informa lo que haría.')
        parser.add_argument('--detalle', action='store_true', help='Muestra cada cambio, no solo los totales.')
        parser.add_argument('--quitar-sacafranco-sobrantes', action='store_true',
                            help='Elimina los sacafranco que solo existen en el mes siguiente (por defecto solo se informan).')

    def handle(self, *args, **opts):
        mes, anio = opts['mes'], opts['anio']
        if not 1 <= mes <= 12:
            raise CommandError('--mes debe estar entre 1 y 12')
        if not Asignacion.objects.filter(mes=mes, anio=anio).exists():
            raise CommandError(f'No hay asignaciones en {mes:02d}/{anio}')
        dry = opts['dry_run']
        log = (lambda m: self.stdout.write('      ' + m)) if opts['detalle'] else None
        self.stdout.write(('PRUEBA (no se guarda nada)' if dry else 'GUARDANDO')
                          + f': meses siguientes a {mes:02d}/{anio} (hasta {opts["meses"]})')
        total = Counter()
        with transaction.atomic():
            for ty, tm, res in alinear_meses(mes, anio, meses=opts['meses'], log=log,
                                             quitar_sacafranco_sobrantes=opts['quitar_sacafranco_sobrantes']):
                total.update(res)
                resumen = ', '.join(f'{v} {n}' for n, v in res.items() if v) or 'sin cambios'
                self.stdout.write(f'  {tm:02d}/{ty}: {resumen}')
            if dry:
                transaction.set_rollback(True)
        self.stdout.write('TOTAL: ' + (', '.join(f'{v} {n}' for n, v in total.items() if v) or 'sin cambios'))
        if dry:
            self.stdout.write('Prueba terminada: no se guardó nada.')
