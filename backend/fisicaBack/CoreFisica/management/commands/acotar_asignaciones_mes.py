"""Acota cada asignacion recurrente a SU mes: end_date = ultimo dia del mes
(segun mes/anio). Sirve para limpiar de una sola vez el solape historico:
antes las asignaciones quedaban abiertas (end_date=None) y se pisaban entre
meses, haciendo que una persona saliera DUPLICADA en Reporte/Consolidado de
los meses siguientes. Al acotarlas, cada fecha queda cubierta por una sola.

No borra nada (solo ajusta end_date). No toca meses/anios vacios.

Uso:
    python manage.py acotar_asignaciones_mes --dry-run
    python manage.py acotar_asignaciones_mes
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from CoreFisica.models import Asignacion


def _ultimo_dia(mes, anio):
    return (date(anio, mes + 1, 1) - timedelta(days=1)) if mes < 12 else date(anio, 12, 31)


class Command(BaseCommand):
    help = "Acota cada asignacion recurrente a su mes (end_date = fin de mes). Elimina el solape/duplicados."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra cuantas cambiarian, no guarda.')

    def handle(self, *args, **opts):
        dry = opts.get('dry_run')
        qs = Asignacion.objects.filter(recurring=True).exclude(mes__isnull=True).exclude(anio__isnull=True)
        total = qs.count()
        por_cambiar = []
        for a in qs.only('id', 'mes', 'anio', 'end_date').iterator():
            ld = _ultimo_dia(a.mes, a.anio)
            if a.end_date != ld:
                por_cambiar.append((a.id, ld))

        self.stdout.write(f"Asignaciones recurrentes: {total}")
        self.stdout.write(f"A acotar (end_date != fin de mes): {len(por_cambiar)}")

        if dry:
            self.stdout.write("Dry-run: no se guardo nada.")
            return

        with transaction.atomic():
            n = 0
            for aid, ld in por_cambiar:
                Asignacion.objects.filter(id=aid).update(end_date=ld)
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Listo: {n} asignaciones acotadas a su mes."))
