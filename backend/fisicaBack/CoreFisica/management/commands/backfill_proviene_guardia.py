"""Actualiza `proviene` = tipo de la persona en las filas auto del reporte de
guardia (por si quedaron con otro valor). Idempotente.

Uso:  python manage.py backfill_proviene_guardia
"""
from django.core.management.base import BaseCommand
from CoreFisica.models import ReporteGuardia


class Command(BaseCommand):
    help = 'Pone proviene = tipo de la persona en las filas auto del reporte de guardia.'

    def handle(self, *args, **options):
        qs = ReporteGuardia.objects.filter(auto=True).select_related('persona_ref')
        actualizadas = 0
        for r in qs:
            tipo = str(getattr(r.persona_ref, 'tipo', '') or '')
            if r.proviene != tipo:
                r.proviene = tipo
                r.save(update_fields=['proviene'])
                actualizadas += 1
        self.stdout.write(self.style.SUCCESS(f'Filas actualizadas: {actualizadas}'))
