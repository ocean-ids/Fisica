import datetime
from django.db import migrations


def backfill_horas(apps, schema_editor):
    """Rellena hora_ingreso/salida por turno en los PuestoHorario que las tienen
    vacias (NULL): Diurno -> 07:00-19:00, Nocturno -> 19:00-07:00. No toca los que
    ya tienen hora (respeta lo importado del horario real o lo editado a mano)."""
    PuestoHorario = apps.get_model('CoreFisica', 'PuestoHorario')
    dia_i, dia_s = datetime.time(7, 0), datetime.time(19, 0)
    noc_i, noc_s = datetime.time(19, 0), datetime.time(7, 0)
    qs = PuestoHorario.objects.filter(hora_ingreso__isnull=True, hora_salida__isnull=True)
    ups = []
    for h in qs.only('id', 'turno').iterator():
        t = (h.turno or '').strip().lower()
        if t.startswith('d'):
            h.hora_ingreso, h.hora_salida = dia_i, dia_s
        elif t.startswith('n'):
            h.hora_ingreso, h.hora_salida = noc_i, noc_s
        else:
            continue
        ups.append(h)
    for i in range(0, len(ups), 1000):
        PuestoHorario.objects.bulk_update(ups[i:i + 1000], ['hora_ingreso', 'hora_salida'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0179_alter_puestohorario_unique_together'),
    ]

    operations = [
        migrations.RunPython(backfill_horas, noop),
    ]
