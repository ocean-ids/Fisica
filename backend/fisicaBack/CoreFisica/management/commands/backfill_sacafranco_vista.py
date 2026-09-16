"""Asigna la VISTA (pestaña) a cada SacafrancoFila existente, SIN reimportar.

Antes, al importar, la fila se sellaba con TODOS los cantones/clientes de la
vista. Este comando lee ese scope y lo empareja con la VistaCanton correspondiente
para setear `vista`, de modo que cada sacafranco se muestre SOLO en su vista y no
se repita en otras que compartan cantón/cliente.

Emparejamiento (por fila):
  - clientes seteados  -> vista de tipo 'cliente' con el MISMO conjunto de clientes
    (si no hay match exacto, la de mayor solape).
  - cantones seteados  -> vista de tipo 'canton' con el MISMO conjunto de cantones
    (si no, el superset más pequeño que los contenga; si no, la de mayor solape).

Con --collapse además deja UN solo cantón por fila (el de la persona dentro de la
vista) para que tampoco se repita en la paginación por cantón.

Uso:
  python manage.py backfill_sacafranco_vista --dry-run
  python manage.py backfill_sacafranco_vista --collapse
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.models import SacafrancoFila, VistaCanton


class Command(BaseCommand):
    help = "Asigna la vista a cada SacafrancoFila según su scope (evita repetición entre vistas)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo reporta.')
        parser.add_argument('--collapse', action='store_true',
                            help='Además deja un solo cantón por fila.')

    def handle(self, *args, **opts):
        dry = opts.get('dry_run')
        collapse = opts.get('collapse')
        cant_views = [v for v in VistaCanton.objects.all() if v.tipo == 'canton']
        cli_views = [v for v in VistaCanton.objects.all() if v.tipo == 'cliente']

        def best_cliente(cl):
            exact = [v for v in cli_views if set(v.clientes or []) == cl]
            if exact:
                return exact[0]
            cand = [v for v in cli_views if set(v.clientes or []) & cl]
            return max(cand, key=lambda v: len(set(v.clientes or []) & cl), default=None)

        def best_canton(cs):
            exact = [v for v in cant_views if set(v.cantones or []) == cs]
            if exact:
                return exact[0]
            supers = [v for v in cant_views if cs <= set(v.cantones or [])]
            if supers:
                return min(supers, key=lambda v: len(v.cantones or []))
            cand = [v for v in cant_views if set(v.cantones or []) & cs]
            return max(cand, key=lambda v: len(set(v.cantones or []) & cs), default=None)

        asignadas = 0
        sin_match = 0
        for f in SacafrancoFila.objects.select_related('persona'):
            cs = set(f.cantones or [])
            cl = set(f.clientes or [])
            best = best_cliente(cl) if cl else (best_canton(cs) if cs else None)
            if not best:
                sin_match += 1
                continue

            nuevos_cant = list(f.cantones or [])
            if collapse and best.tipo == 'canton':
                vc = set(best.cantones or [])
                pc = getattr(f.persona, 'canton_id', None)
                uno = pc if (pc and pc in vc) else (sorted(vc)[0] if vc else None)
                nuevos_cant = [uno] if uno else []

            if dry:
                asignadas += 1
                continue
            with transaction.atomic():
                f.vista = best
                if collapse:
                    f.cantones = nuevos_cant
                    f.save(update_fields=['vista', 'cantones'])
                else:
                    f.save(update_fields=['vista'])
            asignadas += 1

        self.stdout.write(self.style.SUCCESS(
            f"{'(dry-run) ' if dry else ''}vista asignada: {asignadas} | sin vista que empareje: {sin_match}"
        ))
