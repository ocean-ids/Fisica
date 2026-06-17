import unicodedata
from collections import defaultdict
from django.db import migrations


def _normalizar(nombre):
    s = str(nombre or '').strip().upper()
    # Quitar acentos para comparar (MANABÍ == MANABI)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    # Colapsar espacios
    s = ' '.join(s.split())
    return s


def merge_provincias(apps, schema_editor):
    Provincia = apps.get_model('CoreFisica', 'Provincia')
    Canton = apps.get_model('CoreFisica', 'Canton')
    Persona = apps.get_model('CoreFisica', 'Persona')
    SacafrancoFila = apps.get_model('CoreFisica', 'SacafrancoFila')
    Consolidado = apps.get_model('CoreFisica', 'Consolidado')

    grupos = defaultdict(list)
    for p in Provincia.objects.all().order_by('id'):
        grupos[_normalizar(p.nombre)].append(p)

    for clave, provincias in grupos.items():
        if len(provincias) <= 1:
            continue
        canonica = provincias[0]
        duplicadas = provincias[1:]
        dup_ids = [d.id for d in duplicadas]

        # Repuntar todas las referencias a la provincia canónica
        Canton.objects.filter(provincia_id__in=dup_ids).update(provincia_id=canonica.id)
        Persona.objects.filter(provincia_id__in=dup_ids).update(provincia_id=canonica.id)
        SacafrancoFila.objects.filter(provincia_id__in=dup_ids).update(provincia_id=canonica.id)
        Consolidado.objects.filter(provincia_ref_id__in=dup_ids).update(provincia_ref_id=canonica.id)

        # Eliminar las provincias duplicadas
        Provincia.objects.filter(id__in=dup_ids).delete()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0112_limpiar_asignaciones_vacantes_duplicadas'),
    ]

    operations = [
        migrations.RunPython(merge_provincias, reverse_noop),
    ]
