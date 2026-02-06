from django.core.management.base import BaseCommand

from CoreFisica.models import Cliente


class Command(BaseCommand):
    help = 'Populate missing RUC for Cliente objects with a unique placeholder RUC (10 digits).'

    def handle(self, *args, **options):
        updated = 0
        qs = Cliente.objects.filter(ruc__isnull=True)
        for c in qs:
            # generate a 10-digit placeholder RUC based on id (ensures uniqueness)
            c.ruc = str(1000000000 + c.id)
            c.save(update_fields=['ruc'])
            self.stdout.write(self.style.SUCCESS(f'Updated Cliente id={c.id} ruc={c.ruc}'))
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Completed. Updated {updated} clients.'))
