"""Nombre del banco solo con la ENTIDAD en MAYÚSCULAS: 'Banco Pichincha' -> 'PICHINCHA',
'Produbanco' -> 'PRODUBANCO', 'Banco del Pacífico' -> 'PACIFICO'. Datos de la persona
(EmpleadoOtrosDatos) y copias guardadas en los reportes de pago."""
from django.db import migrations


def _sin_tildes(txt):
    """Quita las tildes (Á -> A) pero conserva la Ñ."""
    import unicodedata
    return ''.join(
        ('Ñ' if c == 'Ñ' else unicodedata.normalize('NFD', c)[0])
        for c in txt
    )


def _entidad(nombre):
    t = _sin_tildes(str(nombre or '').upper()).split()
    if len(t) > 1 and t[0] in ('BANCO', 'BCO', 'BCO.'):
        t = t[1:]
        if len(t) > 1 and t[0] in ('DE', 'DEL'):
            t = t[1:]
    return ' '.join(t)


def normalizar(apps, schema_editor):
    for modelo in ('EmpleadoOtrosDatos', 'ReportePago'):
        M = apps.get_model('CoreFisica', modelo)
        for obj in M.objects.exclude(banco='').only('pk', 'banco'):
            nuevo = _entidad(obj.banco)
            if nuevo != obj.banco:
                M.objects.filter(pk=obj.pk).update(banco=nuevo)


class Migration(migrations.Migration):
    dependencies = [('CoreFisica', '0198_vacaciones_enlazar_personas_por_nombre')]
    operations = [migrations.RunPython(normalizar, migrations.RunPython.noop)]
