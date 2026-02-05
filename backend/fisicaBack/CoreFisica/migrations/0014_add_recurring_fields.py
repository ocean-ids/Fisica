from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0013_remove_asignacion_rotativo'),
    ]

    operations = [
        migrations.AddField(
            model_name='asignacion',
            name='recurring',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='asignacion',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='asignacion',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
