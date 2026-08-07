"""Limpia semanas de sacafranco mal ancladas.

Borra filas de SacafrancoFilaSemanal cuyo week_start pertenece a un mes/anio
distinto al de su SacafrancoFila. Esas filas (data de imports viejos) hacen que
un sacafranco de otro mes aparezca DUPLICADO en el grid del mes visto.

Uso:
    python manage.py limpiar_sacafranco_semanas            # aplica la limpieza
    python manage.py limpiar_sacafranco_semanas --dry-run  # solo muestra cuantas
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.models import SacafrancoFilaSemanal


class Command(BaseCommand):
    help = "Borra semanas de sacafranco con week_start de un mes distinto al de su fila."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo cuenta las corruptas, no borra.')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        ids = []
        qs = SacafrancoFilaSemanal.objects.select_related('sacafranco_fila')
        for s in qs.iterator():
            f = s.sacafranco_fila
            if f and (s.week_start.month != f.mes or s.week_start.year != f.anio):
                ids.append(s.id)

        self.stdout.write(f"Semanas de sacafranco mal ancladas (corruptas): {len(ids)}")
        if dry:
            self.stdout.write("Dry-run: no se borro nada.")
            return
        if not ids:
            self.stdout.write(self.style.SUCCESS("Nada que limpiar."))
            return

        with transaction.atomic():
            borradas, _ = SacafrancoFilaSemanal.objects.filter(id__in=ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Borradas: {borradas}"))
