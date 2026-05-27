from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0101_delete_personalconsola_alter_persona_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='consolidado',
            name='puesto',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
    ]
