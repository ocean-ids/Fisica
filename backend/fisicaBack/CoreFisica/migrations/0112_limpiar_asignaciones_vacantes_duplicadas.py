from django.db import migrations
from collections import defaultdict


def limpiar_vacantes_duplicadas(apps, schema_editor):
    """
    Elimina filas de Asignacion VACANTES (sin persona) que sobran para un mismo
    puesto+mes+anio, cuando el puesto ya tiene cubiertos sus cupos (cantidad_puestos)
    con asignaciones ocupadas. Estas filas son residuo del bug anterior de división.
    """
    Asignacion = apps.get_model('CoreFisica', 'Asignacion')
    AsignacionSemanal = apps.get_model('CoreFisica', 'AsignacionSemanal')

    activos = Asignacion.objects.filter(estado='ACTIVO').select_related('puesto')

    grupos = defaultdict(list)
    for a in activos:
        grupos[(a.puesto_id, a.mes, a.anio)].append(a)

    ids_a_eliminar = []
    for (puesto_id, mes, anio), filas in grupos.items():
        if len(filas) <= 1:
            continue
        cupos = 1
        if filas[0].puesto_id:
            try:
                cupos = int(getattr(filas[0].puesto, 'cantidad_puestos', 1) or 1)
            except Exception:
                cupos = 1

        ocupadas = [f for f in filas if f.persona_id is not None]
        vacantes = [f for f in filas if f.persona_id is None]

        # Cuántas filas sobran respecto a los cupos
        sobrantes = len(filas) - max(cupos, len(ocupadas))
        if sobrantes <= 0:
            continue

        # Eliminar primero las vacantes (preferir conservar ocupadas)
        # y, entre vacantes, las que no tienen calendario con datos.
        def tiene_calendario(asig):
            return AsignacionSemanal.objects.filter(asignacion_id=asig.id).exclude(
                mon='', tue='', wed='', thu='', fri='', sat='', sun=''
            ).exists()

        vacantes_ordenadas = sorted(vacantes, key=lambda f: (tiene_calendario(f), -f.id))
        for f in vacantes_ordenadas:
            if sobrantes <= 0:
                break
            ids_a_eliminar.append(f.id)
            sobrantes -= 1

    if ids_a_eliminar:
        AsignacionSemanal.objects.filter(asignacion_id__in=ids_a_eliminar).delete()
        Asignacion.objects.filter(id__in=ids_a_eliminar).delete()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0111_alter_asignacion_persona'),
    ]

    operations = [
        migrations.RunPython(limpiar_vacantes_duplicadas, reverse_noop),
    ]
