from django.db import migrations


def backfill_es_hueca(apps, schema_editor):
    """Marca como HUECA (es_hueca=True) las asignaciones ya existentes SIN persona
    que tienen calendario (algun dia marcado). Son las huecas importadas antes de
    existir el campo es_hueca. Se excluyen las vacantes sin calendario (posibles
    'No Cubierto' por reasignacion), que se dejan como estaban."""
    Asignacion = apps.get_model('CoreFisica', 'Asignacion')
    AsignacionSemanal = apps.get_model('CoreFisica', 'AsignacionSemanal')
    WEEK = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

    ids = set()
    qs = (AsignacionSemanal.objects
          .filter(asignacion__persona__isnull=True, asignacion__es_hueca=False)
          .only('asignacion_id', *WEEK)
          .iterator())
    for s in qs:
        if any((getattr(s, k, '') or '').strip() for k in WEEK):
            ids.add(s.asignacion_id)

    ids = list(ids)
    for i in range(0, len(ids), 2000):
        Asignacion.objects.filter(id__in=ids[i:i + 2000]).update(es_hueca=True)


def noop(apps, schema_editor):
    # No se revierte: no hay forma fiable de saber cuales estaban en False antes.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0176_asignacion_es_hueca'),
    ]

    operations = [
        migrations.RunPython(backfill_es_hueca, noop),
    ]
