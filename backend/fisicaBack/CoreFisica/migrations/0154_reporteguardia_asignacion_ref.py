from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0153_reporteguardia_auto_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporteguardia',
            name='asignacion_ref',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reporte_guardia_no_cubierto',
                to='CoreFisica.asignacion',
            ),
        ),
    ]
