"""Normaliza la capacidad de los puestos existentes a 1.

Antes, "Cantidad de Puestos = N" creaba N registros de Puesto (cada uno con
cantidad_puestos=N). A partir de ahora un puesto es UN registro con N cupos, y
las asignaciones se crean hasta llenar esos cupos.

Para no alterar el comportamiento de lo ya existente (cada registro actual es
1 cupo físico), se fija cantidad_puestos=1 en todos los puestos existentes.
"""
from django.db import migrations


def set_cantidad_uno(apps, schema_editor):
    Puesto = apps.get_model('CoreFisica', 'Puesto')
    Puesto.objects.update(cantidad_puestos=1)


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0127_puestohorario_hora_ingreso_puestohorario_hora_salida'),
    ]

    operations = [
        migrations.RunPython(set_cantidad_uno, migrations.RunPython.noop),
    ]
