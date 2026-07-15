import re

from django.db import migrations, models


def backfill_anio(apps, schema_editor):
    """Rellena 'anio' en los registros existentes: usa el año de 'fecha_desde';
    si no hay, el primer año del 'periodo' (ej. '2024 - 2025' -> 2024); si no,
    el año de creación."""
    RV = apps.get_model('CoreFisica', 'ReporteVacaciones')
    for r in RV.objects.all():
        anio = None
        if r.fecha_desde:
            anio = r.fecha_desde.year
        elif r.periodo:
            m = re.search(r'\d{4}', r.periodo)
            if m:
                anio = int(m.group())
        if anio is None and r.created_at:
            anio = r.created_at.year
        if anio is not None and r.anio != anio:
            r.anio = anio
            r.save(update_fields=['anio'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0158_reporteguardia_overrides'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportevacaciones',
            name='anio',
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='reportevacaciones',
            options={'ordering': ['-anio', '-fecha_desde', 'orden', 'id']},
        ),
        migrations.RunPython(backfill_anio, noop),
    ]
