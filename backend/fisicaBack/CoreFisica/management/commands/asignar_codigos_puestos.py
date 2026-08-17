"""Asigna el `codigo` corto a los puestos GARITA/RONDA para usarlo en el sacafranco
(token turno+nominativo+codigo, ej. DU6R1). El codigo se DERIVA del nombre/tipo:

  - GARITA -> G,  RONDA -> R
  - si el nombre trae numero ("GARITA 2", "RONDA 1") -> usa ese numero: G2, R1
  - si NO trae numero y hay varias en la instalacion -> se numeran por orden (id)
    rellenando huecos que no choquen con los numeros explicitos.

Solo toca puestos GARITA/RONDA. No pisa codigos ya puestos a mano salvo con --forzar.

Uso:
    python manage.py asignar_codigos_puestos --dry-run
    python manage.py asignar_codigos_puestos
    python manage.py asignar_codigos_puestos --forzar     # reescribe todos
"""
import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from CoreFisica.models import Puesto

_NUM_RE = re.compile(r'(GARITA|RONDA)\s*0*([0-9]+)', re.I)


def _grupo(p):
    txt = f"{p.tipo or ''} {p.nombre or ''}".upper()
    if 'GARITA' in txt:
        return 'G'
    if 'RONDA' in txt:
        return 'R'
    return None


def _num_en_nombre(p):
    txt = f"{p.tipo or ''} {p.nombre or ''}"
    m = _NUM_RE.search(txt)
    return int(m.group(2)) if m else None


class Command(BaseCommand):
    help = "Asigna codigo (G1/R1...) a puestos GARITA/RONDA, derivado del nombre."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra, no guarda.')
        parser.add_argument('--forzar', action='store_true', help='Reescribe aunque ya tenga codigo.')

    def handle(self, *args, **opts):
        dry = opts.get('dry_run')
        forzar = opts.get('forzar')

        # Agrupar puestos GARITA/RONDA ACTIVOS por (instalacion, grupo G/R).
        # Los puestos CERRADOS (activo=False) NO se numeran (no deben robar el G1/R1
        # al activo) y ademas se les LIMPIA el codigo para que no quede uno viejo.
        por_inst = defaultdict(lambda: {'G': [], 'R': []})
        total_gr = 0
        cerrados_a_limpiar = []
        for p in Puesto.objects.filter(instalacion__isnull=False).order_by('instalacion_id', 'id'):
            g = _grupo(p)
            if not g:
                continue
            total_gr += 1
            if not getattr(p, 'activo', True):
                if (p.codigo or ''):
                    cerrados_a_limpiar.append(p)
                continue
            por_inst[p.instalacion_id][g].append(p)

        cambios = []  # (puesto, codigo_nuevo)
        for inst_id, grupos in por_inst.items():
            for g, puestos in grupos.items():
                usados = set()
                pendientes = []
                # 1) los que traen numero explicito en el nombre
                for p in puestos:
                    n = _num_en_nombre(p)
                    if n is not None and n not in usados:
                        usados.add(n)
                        nuevo = f"{g}{n}"
                        if forzar or (p.codigo or '') != nuevo:
                            cambios.append((p, nuevo))
                        else:
                            pass
                    else:
                        pendientes.append(p)
                # 2) los sin numero -> siguiente numero libre por orden
                k = 1
                for p in pendientes:
                    while k in usados:
                        k += 1
                    usados.add(k)
                    nuevo = f"{g}{k}"
                    k += 1
                    if forzar or (p.codigo or '') != nuevo:
                        cambios.append((p, nuevo))

        self.stdout.write(f"Puestos GARITA/RONDA (total): {total_gr}")
        self.stdout.write(f"Codigos a asignar/cambiar (ACTIVOS): {len(cambios)}")
        self.stdout.write(f"Codigos a LIMPIAR (puestos cerrados): {len(cerrados_a_limpiar)}")
        for p, nuevo in cambios[:20]:
            self.stdout.write(f"    [{nuevo}] inst {p.instalacion_id}  {p.nombre}  (tipo={p.tipo})")
        if len(cambios) > 20:
            self.stdout.write(f"    ... y {len(cambios) - 20} mas")

        if dry:
            self.stdout.write("Dry-run: no se guardo nada.")
            return

        with transaction.atomic():
            for p, nuevo in cambios:
                p.codigo = nuevo
                p.save(update_fields=['codigo'])
            for p in cerrados_a_limpiar:
                p.codigo = None
                p.save(update_fields=['codigo'])
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(cambios)} activos con codigo, {len(cerrados_a_limpiar)} cerrados limpiados."))
