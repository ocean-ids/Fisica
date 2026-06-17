from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0008_remove_asignacion_dias_franco_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asignacion',
            name='resumen',
        ),
    ]
