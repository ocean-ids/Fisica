import re
import unicodedata
from collections import defaultdict
from django.db import migrations


def _norm(nombre):
    s = str(nombre or '').strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


def merge(apps, schema_editor):
    Provincia = apps.get_model('CoreFisica', 'Provincia')
    Canton = apps.get_model('CoreFisica', 'Canton')
    Instalacion = apps.get_model('CoreFisica', 'Instalacion')
    Persona = apps.get_model('CoreFisica', 'Persona')
    SacafrancoFila = apps.get_model('CoreFisica', 'SacafrancoFila')
    Consolidado = apps.get_model('CoreFisica', 'Consolidado')

    def mover_cantones(dup_ids, canonica_id):
        canon_por_norm = {}
        for c in Canton.objects.filter(provincia_id=canonica_id):
            canon_por_norm.setdefault(_norm(c.nombre), c)
        for cant in Canton.objects.filter(provincia_id__in=dup_ids):
            clave = _norm(cant.nombre)
            existente = canon_por_norm.get(clave)
            if existente and existente.id != cant.id:
                Instalacion.objects.filter(canton_id=cant.id).update(canton_id=existente.id)
                Persona.objects.filter(canton_id=cant.id).update(canton_id=existente.id)
                cant.delete()
            else:
                cant.provincia_id = canonica_id
                cant.save(update_fields=['provincia'])
                canon_por_norm[clave] = cant

    # 1) Fusionar SANTO DOMINGO -> SANTO DOMINGO DE LOS TSÁCHILAS
    corta = Provincia.objects.filter(nombre__iexact='SANTO DOMINGO').first()
    larga = None
    for p in Provincia.objects.all():
        if _norm(p.nombre).startswith('SANTO DOMINGO DE LOS TSACHILAS'):
            larga = p
            break
    if corta and larga and corta.id != larga.id:
        mover_cantones([corta.id], larga.id)
        Persona.objects.filter(provincia_id=corta.id).update(provincia_id=larga.id)
        SacafrancoFila.objects.filter(provincia_id=corta.id).update(provincia_id=larga.id)
        Consolidado.objects.filter(provincia_ref_id=corta.id).update(provincia_ref_id=larga.id)
        Provincia.objects.filter(id=corta.id).delete()

    # 2) Deduplicar cantones repetidos dentro de cada provincia (por nombre normalizado)
    for prov in Provincia.objects.all():
        grupos = defaultdict(list)
        for c in Canton.objects.filter(provincia_id=prov.id).order_by('id'):
            grupos[_norm(c.nombre)].append(c)
        for clave, cantones in grupos.items():
            if len(cantones) <= 1:
                continue
            canonico = cantones[0]
            for dup in cantones[1:]:
                Instalacion.objects.filter(canton_id=dup.id).update(canton_id=canonico.id)
                Persona.objects.filter(canton_id=dup.id).update(canton_id=canonico.id)
                dup.delete()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0115_seed_provincias_cantones'),
    ]

    operations = [
        migrations.RunPython(merge, reverse_noop),
    ]
