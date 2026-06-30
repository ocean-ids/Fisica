"""Backfill estado_empleado: los empleados ya inactivos pasan a LIQUIDADO,
los activos a ACTIVO. (LIQUIDADO y SUSPENDIDO equivalen a deshabilitado.)"""
from django.db import migrations


def backfill(apps, schema_editor):
    Persona = apps.get_model('CoreFisica', 'Persona')
    Persona.objects.filter(is_active=True).update(estado_empleado='ACTIVO')
    Persona.objects.filter(is_active=False).update(estado_empleado='LIQUIDADO')


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0150_persona_estado_empleado'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
