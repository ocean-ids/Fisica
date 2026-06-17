import re
import unicodedata
from collections import defaultdict
from django.db import migrations


def _normalizar(nombre):
    s = str(nombre or '').strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    # Guiones, puntos y cualquier separador no alfanumérico -> espacio
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


def _nombre_limpio(nombre):
    """Nombre para mostrar: mayúsculas, guiones/puntuación -> espacio, conserva acentos."""
    s = str(nombre or '').strip().upper()
    s = re.sub(r'[^0-9A-ZÁÉÍÓÚÑÜ]+', ' ', s)
    return ' '.join(s.split())


def _mover_cantones(Canton, Instalacion, Persona, dup_ids, canonica_id):
    """Repunta cantones de provincias duplicadas a la canónica, fusionando por nombre."""
    # cantones ya existentes en la provincia canónica, por nombre normalizado
    canon_por_norm = {}
    for c in Canton.objects.filter(provincia_id=canonica_id):
        canon_por_norm.setdefault(_normalizar(c.nombre), c)

    for cant in Canton.objects.filter(provincia_id__in=dup_ids):
        clave = _normalizar(cant.nombre)
        existente = canon_por_norm.get(clave)
        if existente:
            # Fusionar: repuntar referencias del cantón duplicado al existente y borrarlo
            Instalacion.objects.filter(canton_id=cant.id).update(canton_id=existente.id)
            Persona.objects.filter(canton_id=cant.id).update(canton_id=existente.id)
            cant.delete()
        else:
            cant.provincia_id = canonica_id
            cant.save(update_fields=['provincia'])
            canon_por_norm[clave] = cant


def merge_provincias(apps, schema_editor):
    Provincia = apps.get_model('CoreFisica', 'Provincia')
    Canton = apps.get_model('CoreFisica', 'Canton')
    Instalacion = apps.get_model('CoreFisica', 'Instalacion')
    Persona = apps.get_model('CoreFisica', 'Persona')
    SacafrancoFila = apps.get_model('CoreFisica', 'SacafrancoFila')
    Consolidado = apps.get_model('CoreFisica', 'Consolidado')

    grupos = defaultdict(list)
    for p in Provincia.objects.all().order_by('id'):
        grupos[_normalizar(p.nombre)].append(p)

    for clave, provincias in grupos.items():
        if len(provincias) <= 1:
            unica = provincias[0]
            limpio = _nombre_limpio(unica.nombre)
            if limpio and limpio != unica.nombre:
                unica.nombre = limpio
                unica.save(update_fields=['nombre'])
            continue

        canonica = next((p for p in provincias if '-' not in p.nombre), provincias[0])
        dup_ids = [p.id for p in provincias if p.id != canonica.id]

        _mover_cantones(Canton, Instalacion, Persona, dup_ids, canonica.id)
        Persona.objects.filter(provincia_id__in=dup_ids).update(provincia_id=canonica.id)
        SacafrancoFila.objects.filter(provincia_id__in=dup_ids).update(provincia_id=canonica.id)
        Consolidado.objects.filter(provincia_ref_id__in=dup_ids).update(provincia_ref_id=canonica.id)

        Provincia.objects.filter(id__in=dup_ids).delete()

        limpio = _nombre_limpio(canonica.nombre)
        if limpio and limpio != canonica.nombre:
            canonica.nombre = limpio
            canonica.save(update_fields=['nombre'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0113_merge_provincias_duplicadas'),
    ]

    operations = [
        migrations.RunPython(merge_provincias, reverse_noop),
    ]
