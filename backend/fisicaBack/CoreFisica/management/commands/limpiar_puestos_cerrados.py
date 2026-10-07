"""Limpia los puestos CERRADOS (puesto inactivo) que siguen saliendo o proyectándose a futuro.

Es para los datos que quedaron de ANTES de la corrección del cierre. Para cada puesto inactivo:
  - Fecha del cierre = la de su última novedad CIERRE; si no tiene (p. ej. se cerró la instalación entera),
    se usa HOY.
  - Sus asignaciones salen hasta esa fecha incluida y desde el día siguiente ya no (end_date = fecha).
  - Las de los meses posteriores pasan a INACTIVO (no se proyectan a futuro).
No borra nada. Los días anteriores al cierre y la asistencia ya registrada no se tocan. Se puede repetir.

Uso:
    python manage.py limpiar_puestos_cerrados --dry-run      (prueba: solo informa, no guarda)
    python manage.py limpiar_puestos_cerrados --dry-run --detalle
    python manage.py limpiar_puestos_cerrados
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from CoreFisica.models import Asignacion, NovedadPuesto, Puesto
from CoreFisica.views.novedad_puesto_views import _cerrar_asignaciones_futuras


def limpiar_puestos_cerrados(hoy=None, log=None):
    """Aplica el corte a todos los puestos inactivos. Devuelve {nombre: cantidad} de lo que cambió."""
    hoy = hoy or timezone.localdate()
    log = log or (lambda m: None)
    res = {'puestos revisados': 0, 'puestos corregidos': 0,
           'filas que dejan de salir despues del cierre': 0, 'filas de meses futuros desactivadas': 0}
    for puesto in Puesto.objects.filter(activo=False).select_related('instalacion').order_by('id'):
        res['puestos revisados'] += 1
        cierre = (NovedadPuesto.objects.filter(puesto=puesto, novedad='CIERRE')
                  .order_by('-fecha', '-id').values_list('fecha', flat=True).first())
        fc = cierre or hoy
        acts = Asignacion.objects.filter(puesto=puesto, estado='ACTIVO')
        # Lo que va a cambiar (para informar): filas que se recortan y filas futuras que se desactivan.
        recortar = acts.filter(Q(anio__lt=fc.year) | Q(anio=fc.year, mes__lte=fc.month)).filter(
            Q(end_date__isnull=True) | Q(end_date__gt=fc)).exclude(
            ~Q(anio=fc.year, mes=fc.month) & Q(persona__isnull=True)).count()
        futuras = acts.filter(Q(anio__gt=fc.year) | Q(anio=fc.year, mes__gt=fc.month)).count()
        if not (recortar or futuras):
            continue
        _cerrar_asignaciones_futuras(puesto, fc)
        res['puestos corregidos'] += 1
        res['filas que dejan de salir despues del cierre'] += recortar
        res['filas de meses futuros desactivadas'] += futuras
        inst = getattr(puesto.instalacion, 'nombre', '') or ''
        log(f'{inst} · {puesto.nombre} (puesto {puesto.id}): cierre {fc:%d/%m/%Y}'
            f'{"" if cierre else " (sin novedad: hoy)"} -> {recortar} recortadas, {futuras} futuras desactivadas')
    return res


class Command(BaseCommand):
    help = 'Puestos cerrados: salen hasta el día del cierre y no se proyectan a futuro (datos anteriores).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='No guarda: solo informa lo que haría.')
        parser.add_argument('--detalle', action='store_true', help='Muestra cada puesto corregido.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        log = (lambda m: self.stdout.write('   ' + m)) if opts['detalle'] else None
        self.stdout.write('PRUEBA (no se guarda nada)' if dry else 'GUARDANDO')
        with transaction.atomic():
            res = limpiar_puestos_cerrados(log=log)
            if dry:
                transaction.set_rollback(True)
        for nombre, valor in res.items():
            self.stdout.write(f'  {valor} {nombre}')
        if dry:
            self.stdout.write('Prueba terminada: no se guardó nada.')
