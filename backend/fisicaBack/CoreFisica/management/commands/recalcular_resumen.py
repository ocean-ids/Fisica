from django.core.management.base import BaseCommand
from CoreFisica.models import Puesto


class Command(BaseCommand):
    help = 'Recalcula el campo resumen para todos los puestos'

    def handle(self, *args, **kwargs):
        puestos = Puesto.objects.all()
        for puesto in puestos:
            puesto.save()  # Esto recalculará el resumen del puesto
        self.stdout.write(self.style.SUCCESS('Resumen recalculado para todos los puestos'))