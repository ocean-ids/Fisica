from django.core.management.base import BaseCommand
from CoreFisica.models import Asignacion

class Command(BaseCommand):
    help = 'Recalcula el campo resumen para todas las asignaciones'

    def handle(self, *args, **kwargs):
        asignaciones = Asignacion.objects.all()
        for asignacion in asignaciones:
            asignacion.save()  # Esto recalculará el resumen
        self.stdout.write(self.style.SUCCESS('Resumen recalculado para todas las asignaciones'))