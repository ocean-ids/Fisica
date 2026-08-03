"""Importa un Excel de horario (puestos/asignaciones) por linea de comandos,
sin pasar por la web ni por Cloudflare (evita el timeout 524).

Uso (dentro del contenedor del backend):
    python manage.py importar_horario /tmp/horario.xlsx --mes 8 --anio 2026 --meses 36
"""
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook

from CoreFisica.views.importar_puestos_asignaciones import (
    es_formato_reporte, importar_formato_reporte,
)


class _Req:
    """Request minimo: el importador solo lee GET/POST para mes/anio/meses/desactivar."""
    def __init__(self, mes=None, anio=None, meses=36, desactivar=False):
        self.GET = {
            'mes': str(mes) if mes else '',
            'anio': str(anio) if anio else '',
            'meses': str(meses),
            'desactivar_sobrantes': '1' if desactivar else '',
        }
        self.POST = {}


class Command(BaseCommand):
    help = 'Importa un Excel de horario (puestos/asignaciones) sin pasar por la web/Cloudflare.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta al .xlsx dentro del contenedor (ej. /tmp/horario.xlsx)')
        parser.add_argument('--mes', type=int, default=None)
        parser.add_argument('--anio', type=int, default=None)
        parser.add_argument('--meses', type=int, default=36, help='Meses de proyeccion (default 36)')
        parser.add_argument('--cliente-id', type=int, default=None)
        parser.add_argument('--desactivar-sobrantes', action='store_true',
                            help='Desactiva a quien ya no aparece en el archivo (por defecto NO).')

    def handle(self, *args, **opts):
        try:
            wb = load_workbook(opts['archivo'], read_only=False, data_only=True)
        except Exception as exc:
            raise CommandError(f'No se pudo abrir el archivo: {exc}')

        if not es_formato_reporte(wb):
            raise CommandError(
                'El archivo no tiene el FORMATO REPORTE que reconoce el importador. '
                'Este comando solo soporta ese formato.'
            )

        req = _Req(mes=opts.get('mes'), anio=opts.get('anio'),
                   meses=opts.get('meses'), desactivar=opts.get('desactivar_sobrantes'))

        self.stdout.write('Importando... (puede tardar unos minutos)')
        resumen = importar_formato_reporte(req, wb, opts.get('cliente_id'))

        self.stdout.write(self.style.SUCCESS('=== RESUMEN ==='))
        for k, v in resumen.items():
            if k == 'errores':
                self.stdout.write(f'  errores: {len(v)}')
            else:
                self.stdout.write(f'  {k}: {v}')
        errores = resumen.get('errores', [])
        if errores:
            self.stdout.write(self.style.WARNING('Primeros errores (filas no importadas):'))
            for e in errores[:50]:
                self.stdout.write(f'   - {e}')
            if len(errores) > 50:
                self.stdout.write(f'   ... y {len(errores) - 50} mas')
