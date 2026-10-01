"""Quita de Asignaciones a las personas DESACTIVADAS (LIQUIDADO / SUSPENDIDO).

Del mes ACTUAL en adelante, para todos los tipos (FIJOS, SACAFRANCO, RETEN, ...):
  - sus asignaciones ACTIVAS pasan a INACTIVO (dejan de ocupar cupo y de salir en pantalla);
  - sus filas de sacafranco se ELIMINAN, salvo las que ya tienen asistencia registrada.
Los meses PASADOS no se tocan (son historial). Desde ahora esto también ocurre solo cuando
se desactiva a una persona en el módulo de Personas.

Uso:
    python manage.py limpiar_personas_desactivadas --dry-run
    python manage.py limpiar_personas_desactivadas
    python manage.py limpiar_personas_desactivadas --detalle
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.asignaciones_meses import limpiar_personas_desactivadas


class Command(BaseCommand):
    help = 'Quita de Asignaciones (mes actual en adelante) a las personas desactivadas.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='No guarda: solo informa lo que haría.')
        parser.add_argument('--detalle', action='store_true', help='Muestra cada persona afectada.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        log = (lambda m: self.stdout.write('   ' + m)) if opts['detalle'] else None
        self.stdout.write('PRUEBA (no se guarda nada)' if dry else 'GUARDANDO')
        with transaction.atomic():
            res = limpiar_personas_desactivadas(log=log)
            if dry:
                transaction.set_rollback(True)
        for nombre, valor in res.items():
            self.stdout.write(f'  {valor} {nombre}')
        if not res:
            self.stdout.write('  nada que limpiar')
        if dry:
            self.stdout.write('Prueba terminada: no se guardó nada.')
