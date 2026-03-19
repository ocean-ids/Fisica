from django.db import migrations, models


def copy_codigo_to_cliente(apps, schema_editor):
    Cliente = apps.get_model('CoreFisica', 'Cliente')
    Instalacion = apps.get_model('CoreFisica', 'Instalacion')
    for cliente in Cliente.objects.all():
        if getattr(cliente, 'codigo', None):
            continue
        inst = (
            Instalacion.objects.filter(cliente_id=cliente.id)
            .exclude(codigo__isnull=True)
            .exclude(codigo='')
            .first()
        )
        if inst:
            cliente.codigo = inst.codigo
            cliente.save(update_fields=['codigo'])


def copy_codigo_to_instalacion(apps, schema_editor):
    Cliente = apps.get_model('CoreFisica', 'Cliente')
    Instalacion = apps.get_model('CoreFisica', 'Instalacion')
    for cliente in Cliente.objects.exclude(codigo__isnull=True).exclude(codigo=''):
        inst = Instalacion.objects.filter(cliente_id=cliente.id, codigo__isnull=True).first()
        if inst:
            inst.codigo = cliente.codigo
            inst.save(update_fields=['codigo'])


class Migration(migrations.Migration):
    dependencies = [
        ('CoreFisica', '0055_cliente_fecha_ingreso_cliente_fecha_retiro'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='codigo',
            field=models.CharField(max_length=20, blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(copy_codigo_to_cliente, copy_codigo_to_instalacion),
        migrations.RemoveField(
            model_name='instalacion',
            name='codigo',
        ),
    ]
