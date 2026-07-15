from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0157_reportevacaciones_dias_pendientes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporteguardia',
            name='overrides',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
