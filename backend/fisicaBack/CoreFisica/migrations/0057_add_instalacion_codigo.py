from django.db import migrations, models


def copy_codigo_to_instalacion(apps, schema_editor):
    Cliente = apps.get_model('CoreFisica', 'Cliente')
    Instalacion = apps.get_model('CoreFisica', 'Instalacion')
    for cliente in Cliente.objects.exclude(codigo__isnull=True).exclude(codigo=''):
        Instalacion.objects.filter(cliente_id=cliente.id, codigo__isnull=True).update(codigo=cliente.codigo)
        Instalacion.objects.filter(cliente_id=cliente.id, codigo='').update(codigo=cliente.codigo)


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0056_move_codigo_to_cliente'),
    ]

    operations = [
        migrations.AddField(
            model_name='instalacion',
            name='codigo',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True),
        ),
        migrations.RunPython(copy_codigo_to_instalacion, migrations.RunPython.noop),
    ]
