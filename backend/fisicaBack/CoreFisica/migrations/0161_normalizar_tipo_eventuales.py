from django.db import migrations


def normalizar_eventuales(apps, schema_editor):
    """Unifica el tipo 'EVENTUALES' (plural, valor heredado de una importacion y
    fuera de TIPO_CHOICES) al valor oficial 'EVENTUAL', para que el filtro por
    tipo en Personas los incluya. No toca 'SUPERVISOR EVENTUAL' (es otro tipo)."""
    Persona = apps.get_model('CoreFisica', 'Persona')
    Persona.objects.filter(tipo='EVENTUALES').update(tipo='EVENTUAL')


def revertir(apps, schema_editor):
    # No se puede distinguir cuales eran originalmente 'EVENTUALES'; no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0160_tarifapago_reportepago'),
    ]

    operations = [
        migrations.RunPython(normalizar_eventuales, revertir),
    ]
