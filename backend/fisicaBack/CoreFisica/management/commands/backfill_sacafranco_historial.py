"""Siembra el historial de asistencia de sacafranco a partir del estado ACTUAL de cada
SacafrancoAsistencia existente. El historial (SacafrancoAsistenciaHistorial) empezó a
registrarse cuando se agregó la función, así que las marcas anteriores no tienen ninguna
entrada y el "Historial" del reporte sale vacío. Este comando crea UNA entrada por cada
SacafrancoAsistencia que aún no tenga historial en su misma fecha, con su estado actual.

Uso:
    python manage.py backfill_sacafranco_historial --dry-run
    python manage.py backfill_sacafranco_historial
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.models import SacafrancoAsistencia, SacafrancoAsistenciaHistorial


class Command(BaseCommand):
    help = "Siembra el historial de sacafranco desde el estado actual de cada marca."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra cuántas entradas se crearían, sin escribir.'
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        marcas = SacafrancoAsistencia.objects.select_related('reemplazo', 'modificado_por').all()
        total = marcas.count()
        creadas = 0
        saltadas = 0

        for m in marcas:
            # Si ya hay historial para esa fila+fecha, no duplicar (idempotente).
            ya = SacafrancoAsistenciaHistorial.objects.filter(
                sacafranco_fila_id=m.sacafranco_fila_id, fecha_reporte=m.fecha
            ).exists()
            if ya:
                saltadas += 1
                continue

            if dry:
                creadas += 1
                continue

            with transaction.atomic():
                h = SacafrancoAsistenciaHistorial.objects.create(
                    sacafranco_fila_id=m.sacafranco_fila_id,
                    fecha_reporte=m.fecha,
                    usuario=m.modificado_por,
                    estado=m.estado or '',
                    estado_asistencia=m.estado_asistencia or '',
                    reemplazo=m.reemplazo,
                    descripcion=m.descripcion or '',
                    row_color=m.row_color or '',
                    hueca=bool(m.hueca),
                    hueca_motivo=m.hueca_motivo or '',
                )
                # creado_en es auto_now_add; lo alineamos con la última modificación real.
                if m.modificado_en:
                    SacafrancoAsistenciaHistorial.objects.filter(pk=h.pk).update(
                        creado_en=m.modificado_en
                    )
            creadas += 1

        prefijo = '[DRY-RUN] ' if dry else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefijo}Marcas: {total} | entradas creadas: {creadas} | ya tenían historial: {saltadas}"
        ))
