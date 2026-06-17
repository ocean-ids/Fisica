from django.db import migrations


def forwards(apps, schema_editor):
    Puesto = apps.get_model('CoreFisica', 'Puesto')
    for p in Puesto.objects.all():
        val = (p.turno or '').strip().lower()
        if val == 'dia':
            p.turno = 'Diurno'
            p.save(update_fields=['turno'])
        elif val == 'noche':
            p.turno = 'Nocturno'
            p.save(update_fields=['turno'])


def backwards(apps, schema_editor):
    Puesto = apps.get_model('CoreFisica', 'Puesto')
    for p in Puesto.objects.all():
        val = (p.turno or '').strip().lower()
        if val == 'diurno':
            p.turno = 'dia'
            p.save(update_fields=['turno'])
        elif val == 'nocturno':
            p.turno = 'noche'
            p.save(update_fields=['turno'])


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0021_persona_is_active'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
