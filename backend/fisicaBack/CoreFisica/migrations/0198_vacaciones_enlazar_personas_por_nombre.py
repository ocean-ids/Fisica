"""Datos: enlaza a la persona en los registros de vacaciones que quedaron solo con el nombre
escrito ("quién sale" / "quién cubre" sin la persona). Sin ese enlace el Reporte de Asistencia
no pone al sacavacaciones en el puesto. Solo enlaza si el nombre coincide con UNA persona.
"""
import unicodedata

from django.db import migrations


def _norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode()
    return ' '.join(s.upper().split())


def enlazar(apps, schema_editor):
    Persona = apps.get_model('CoreFisica', 'Persona')
    ReporteVacaciones = apps.get_model('CoreFisica', 'ReporteVacaciones')

    pendientes = list(
        ReporteVacaciones.objects.filter(persona_sale_ref__isnull=True).exclude(persona_sale='')
    ) + list(
        ReporteVacaciones.objects.filter(sacavacaciones_ref__isnull=True).exclude(sacavacaciones='')
    )
    if not pendientes:
        return

    # Índice nombre normalizado -> ids ("nombres apellidos" y "apellidos nombres").
    indice = {}
    for p in Persona.objects.all().only('id', 'nombres', 'apellidos'):
        n, a = _norm(p.nombres), _norm(p.apellidos)
        for k in {f"{n} {a}", f"{a} {n}"}:
            indice.setdefault(k, set()).add(p.id)

    def unico(texto):
        ids = indice.get(_norm(texto)) or set()
        return next(iter(ids)) if len(ids) == 1 else None

    for fila in {f.id: f for f in pendientes}.values():
        fila = ReporteVacaciones.objects.get(id=fila.id)
        cambios = []
        if not fila.persona_sale_ref_id and (fila.persona_sale or '').strip():
            pid = unico(fila.persona_sale)
            if pid:
                fila.persona_sale_ref_id = pid
                cambios.append('persona_sale_ref')
        if not fila.sacavacaciones_ref_id and (fila.sacavacaciones or '').strip():
            pid = unico(fila.sacavacaciones)
            if pid:
                fila.sacavacaciones_ref_id = pid
                cambios.append('sacavacaciones_ref')
        if cambios:
            fila.save(update_fields=cambios)


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0197_horaseventual_cliente_texto_and_more'),
    ]

    operations = [
        migrations.RunPython(enlazar, migrations.RunPython.noop),
    ]
