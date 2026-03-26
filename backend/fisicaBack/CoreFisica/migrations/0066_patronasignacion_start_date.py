from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0065_rename_corefisica_sacafranco_fila_semanal_week_start_idx_corefisica__week_st_373e58_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='patronasignacion',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
