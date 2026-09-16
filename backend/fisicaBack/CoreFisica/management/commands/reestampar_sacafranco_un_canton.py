"""Colapsa el scope de cantones de cada SacafrancoFila a UN SOLO cantón.

Antes, al importar, un sacafranco quedaba sellado con TODOS los cantones de la
vista (ej. [2,3,31,36,37,43,248]), por lo que la MISMA persona aparecía repetida
en cada página/vista de cantón. Este comando deja un solo cantón por fila:
el de la persona si está entre los sellados, si no el primero de la lista.

Uso:
  python manage.py reestampar_sacafranco_un_canton          # aplica
  python manage.py reestampar_sacafranco_un_canton --dry-run # solo reporta
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.models import SacafrancoFila


class Command(BaseCommand):
    help = "Deja un solo cantón por SacafrancoFila (evita que se repita por vista)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo reporta, no guarda cambios.')

    def handle(self, *args, **opts):
        dry = opts.get('dry_run')
        # Solo las filas con MÁS de un cantón sellado (las que causan la repetición).
        qs = SacafrancoFila.objects.select_related('persona').all()
        cambiadas = 0
        revisadas = 0
        for f in qs:
            cantones = list(f.cantones or [])
            if len(cantones) <= 1:
                continue
            revisadas += 1
            pc = getattr(f.persona, 'canton_id', None)
            uno = pc if (pc and pc in cantones) else cantones[0]
            if [uno] == cantones:
                continue
            if dry:
                cambiadas += 1
                continue
            with transaction.atomic():
                f.cantones = [uno]
                f.save(update_fields=['cantones'])
            cambiadas += 1

        self.stdout.write(self.style.SUCCESS(
            f"{'(dry-run) ' if dry else ''}Filas con >1 cantón: {revisadas} | "
            f"re-estampadas a un solo cantón: {cambiadas}"
        ))
