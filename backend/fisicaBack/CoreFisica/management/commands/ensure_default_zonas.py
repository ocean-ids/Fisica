from django.core.management.base import BaseCommand
from CoreFisica.models import Instalacion, Zona


class Command(BaseCommand):
    help = "Garantiza una sola Zona 1 por instalación (crea si falta y limpia extras)."

    def handle(self, *args, **options):
        created_total = 0
        deleted_total = 0
        for inst in Instalacion.objects.all():
            zonas_qs = inst.zonas.order_by('id')
            count = zonas_qs.count()
            if count == 0:
                Zona.objects.create(instalacion=inst, titulo="Zona 1")
                created_total += 1
                continue
            if count > 1:
                keep = zonas_qs.first()
                deleted = zonas_qs.exclude(id=keep.id).delete()[0]
                deleted_total += deleted
        self.stdout.write(self.style.SUCCESS(f"Zonas creadas: {created_total}, zonas extras eliminadas: {deleted_total}"))
