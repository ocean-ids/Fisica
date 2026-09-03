import datetime
from django.db import migrations


def _fin_de_mes(anio, mes):
    if mes >= 12:
        return datetime.date(anio, 12, 31)
    return datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)


def acotar_abiertas(apps, schema_editor):
    """Acota a su ULTIMO DIA DE MES las asignaciones recurrentes con end_date=NULL
    (abiertas). Una asignacion abierta se 'cuela' en el reporte de meses posteriores
    (aparece duplicada junto a la del mes real). El import nuevo ya acota end_date;
    esto aplica la misma regla a los datos existentes (viejos / creados a mano)."""
    Asignacion = apps.get_model('CoreFisica', 'Asignacion')
    qs = Asignacion.objects.filter(recurring=True, end_date__isnull=True).only(
        'id', 'mes', 'anio', 'start_date'
    )
    updates = []
    for a in qs.iterator():
        try:
            mes = int(a.mes) if a.mes else (a.start_date.month if a.start_date else None)
            anio = int(a.anio) if a.anio else (a.start_date.year if a.start_date else None)
            if not mes or not anio:
                continue
            a.end_date = _fin_de_mes(anio, mes)
            updates.append(a)
        except Exception:
            pass
    for i in range(0, len(updates), 500):
        Asignacion.objects.bulk_update(updates[i:i + 500], ['end_date'])


def noop(apps, schema_editor):
    # No se revierte: no hay forma fiable de saber cuales estaban en NULL antes.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0177_backfill_es_hueca'),
    ]

    operations = [
        migrations.RunPython(acotar_abiertas, noop),
    ]
