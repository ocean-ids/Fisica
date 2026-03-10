from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0051_reporteasistencia_reemplazo'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='asignacionsemanal',
            unique_together={('puesto', 'week_start')},
        ),
    ]
