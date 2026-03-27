from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0067_remove_patronasignacion_start_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asignacion',
            name='sacafranco_fila',
        ),
    ]
