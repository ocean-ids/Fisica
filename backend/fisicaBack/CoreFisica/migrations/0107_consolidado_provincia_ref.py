from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0106_rename_corefisica__estado__22a55d_idx_corefisica__estado__0152f2_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='consolidado',
            name='provincia_ref',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='consolidados',
                to='CoreFisica.provincia',
            ),
        ),
    ]
