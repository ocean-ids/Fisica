from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0104_alter_consolidado_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporteasistencia',
            name='estado_asistencia',
            field=models.CharField(
                blank=True,
                choices=[('ASISTIO', 'Asistio'), ('FALTO', 'Falto')],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='reporteasistenciahistorial',
            name='estado_asistencia',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddIndex(
            model_name='reporteasistencia',
            index=models.Index(fields=['estado_asistencia'], name='CoreFisica__estado__22a55d_idx'),
        ),
    ]
