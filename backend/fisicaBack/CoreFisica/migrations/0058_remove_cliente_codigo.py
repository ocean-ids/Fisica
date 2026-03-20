from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0057_add_instalacion_codigo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cliente',
            name='codigo',
        ),
    ]
