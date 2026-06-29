"""Corrige las entradas 'GUAYAQUIL' cargadas bajo una provincia equivocada.

Guayaquil es ciudad/cabecera de GUAYAS. Por captura errónea existían cantones
'GUAYAQUIL' bajo Pichincha, El Oro, Santa Elena y Orellana, con personas
asignadas. Esta migración reasigna esas referencias al cantón correcto
(GUAYAS/GUAYAQUIL) y elimina las entradas equivocadas. Idempotente.
"""
from django.db import migrations


def corregir(apps, schema_editor):
    Canton = apps.get_model('CoreFisica', 'Canton')
    Persona = apps.get_model('CoreFisica', 'Persona')
    Instalacion = apps.get_model('CoreFisica', 'Instalacion')
    Cliente = apps.get_model('CoreFisica', 'Cliente')

    correcto = Canton.objects.filter(nombre='GUAYAQUIL', provincia__nombre='GUAYAS').first()
    if not correcto:
        return  # nada que hacer si no existe el cantón correcto
    guayas = correcto.provincia

    malos = list(Canton.objects.filter(nombre='GUAYAQUIL').exclude(id=correcto.id))
    if not malos:
        return

    Persona.objects.filter(canton__in=malos).update(canton=correcto, provincia=guayas)
    Cliente.objects.filter(canton__in=malos).update(canton=correcto, provincia=guayas)
    Instalacion.objects.filter(canton__in=malos).update(canton=correcto)
    Canton.objects.filter(id__in=[c.id for c in malos]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0145_parroquia'),
    ]

    operations = [
        migrations.RunPython(corregir, migrations.RunPython.noop),
    ]
