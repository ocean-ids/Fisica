from django.db import migrations
from collections import Counter


def backfill_puesto_horario(apps, schema_editor):
    Puesto = apps.get_model('CoreFisica', 'Puesto')
    Asignacion = apps.get_model('CoreFisica', 'Asignacion')

    for puesto in Puesto.objects.filter(horario__isnull=True):
        horario_ids = list(
            Asignacion.objects.filter(
                puesto_id=puesto.id,
                horario__isnull=False
            ).values_list('horario_id', flat=True)
        )
        if not horario_ids:
            continue
        # Horario mas usado en las asignaciones del puesto
        mas_usado = Counter(horario_ids).most_common(1)[0][0]
        puesto.horario_id = mas_usado
        puesto.save(update_fields=['horario'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0109_puesto_horario'),
    ]

    operations = [
        migrations.RunPython(backfill_puesto_horario, reverse_noop),
    ]
