"""Pasa al módulo Servicios Adicionales los ADICIONALES que ya existían (antes del formulario FR).

Los toma de la sección ADICIONALES del Reporte de Guardia (que se llenó desde la asistencia), desde siempre o
desde --desde. Cada uno queda INCOMPLETO: cliente, horario por defecto (el del puesto para ese turno), H calculada
y C = 1; Solicitado por, Recibido por, Medio y Precio vacíos hasta que los completen.
  - Los que vienen de la asistencia (fila de un fijo o de un sacafranco): uno por fila, fecha y turno.
  - Los que se agregaron A MANO en el Reporte de Guardia: uno por cliente, fecha y turno, con C = cuántos había
    (si el cliente no se encuentra en la lista, se omite y se informa).
No borra ni cambia nada de lo que ya existe. Se puede repetir (no duplica).

Uso:
    python manage.py pasar_adicionales_existentes --dry-run          (prueba: solo informa, no guarda)
    python manage.py pasar_adicionales_existentes --dry-run --detalle
    python manage.py pasar_adicionales_existentes
    python manage.py pasar_adicionales_existentes --desde 2026-09-01
"""
import datetime
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from CoreFisica.models import Cliente, Instalacion, ReporteGuardia, ServicioAdicional
from CoreFisica.views.servicios_adicionales_views import asegurar_servicio_adicional


def pasar_adicionales(desde=None, log=None):
    log = log or (lambda m: None)
    res = Counter()
    qs = (ReporteGuardia.objects.filter(seccion='ADICIONALES')
          .select_related('reporte_asistencia__asignacion__horario', 'sacafranco_fila')
          .order_by('fecha', 'turno', 'id'))
    if desde:
        qs = qs.filter(fecha__gte=desde)
    manuales = defaultdict(int)
    for g in qs:
        turno = g.turno if g.turno in ('Diurno', 'Nocturno') else 'Diurno'
        asig = getattr(g.reporte_asistencia, 'asignacion', None) if g.reporte_asistencia_id else None
        fila = g.sacafranco_fila if g.sacafranco_fila_id else None
        if asig is None and fila is None:
            manuales[(g.fecha, turno, (g.cliente or '').strip().upper())] += 1
            continue
        sa, creado = asegurar_servicio_adicional(g.fecha, turno, asignacion=asig,
                                                 sacafranco_fila=None if asig else fila)
        if creado:
            res['pasados desde la asistencia'] += 1
            log(f'{g.fecha:%d/%m/%Y} {turno}: {sa.instalacion or sa.cliente}')
        elif sa:
            res['ya estaban en el módulo'] += 1
        else:
            res['omitidos (sin cliente)'] += 1
            log(f'OMITIDO {g.fecha:%d/%m/%Y} {turno}: {g.cliente} / {g.puesto} (sin cliente)')
    # Filas agregadas a mano en el Reporte de Guardia: por el nombre del cliente (o de la instalación).
    for (fecha, turno, nombre), cantidad in manuales.items():
        cli = Cliente.objects.filter(nombre_comercial__iexact=nombre).first() if nombre else None
        inst = None if cli else (Instalacion.objects.filter(nombre__iexact=nombre).first() if nombre else None)
        if not cli and not inst:
            res['omitidos (cliente no encontrado)'] += 1
            log(f'OMITIDO {fecha:%d/%m/%Y} {turno}: "{nombre}" (cliente no encontrado)')
            continue
        cliente_id = cli.id if cli else inst.cliente_id
        if ServicioAdicional.objects.filter(fecha=fecha, turno=turno, cliente_id=cliente_id,
                                            asignacion__isnull=True, sacafranco_fila__isnull=True).exists():
            res['ya estaban en el módulo'] += 1
            continue
        ServicioAdicional.objects.create(fecha=fecha, turno=turno, cliente_id=cliente_id,
                                         instalacion_id=inst.id if inst else None, cantidad=cantidad)
        res['pasados desde filas a mano del Reporte de Guardia'] += 1
        log(f'{fecha:%d/%m/%Y} {turno}: {nombre} (a mano, C={cantidad})')
    return res


class Command(BaseCommand):
    help = 'Pasa al módulo Servicios Adicionales los adicionales que ya existían (incompletos).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='No guarda: solo informa lo que haría.')
        parser.add_argument('--detalle', action='store_true', help='Muestra cada registro.')
        parser.add_argument('--desde', help='Solo desde esta fecha (YYYY-MM-DD). Sin ella: desde siempre.')

    def handle(self, *args, **opts):
        desde = None
        if opts.get('desde'):
            try:
                desde = datetime.date.fromisoformat(opts['desde'])
            except ValueError:
                raise CommandError('--desde debe tener el formato YYYY-MM-DD')
        dry = opts['dry_run']
        log = (lambda m: self.stdout.write('   ' + m)) if opts['detalle'] else None
        self.stdout.write('PRUEBA (no se guarda nada)' if dry else 'GUARDANDO')
        with transaction.atomic():
            res = pasar_adicionales(desde=desde, log=log)
            if dry:
                transaction.set_rollback(True)
        for nombre, valor in res.items():
            self.stdout.write(f'  {valor} {nombre}')
        if not res:
            self.stdout.write('  no hay adicionales para pasar')
        if dry:
            self.stdout.write('Prueba terminada: no se guardó nada.')
