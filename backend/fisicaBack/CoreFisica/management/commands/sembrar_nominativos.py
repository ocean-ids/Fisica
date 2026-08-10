"""Siembra ZonaOperativa + Nominativo desde los datos actuales.

Cada instalacion con codigo tipo letra(1-3)+numero (ej. G15, U6):
  - se crea/reusa la ZonaOperativa (Zona 1, 2, 3...) segun la ZONA que la
    instalacion YA tiene hoy en el modelo viejo `Zona` (titulo "Zona 1/2/3"),
  - se crea/reusa el Nominativo (letra+numero) y se liga a la instalacion,
    colocandolo en esa zona.

La letra vive en el NOMINATIVO, no en la zona: asi una zona puede tener varias
letras (ej. Zona 3 = G, P, Q). Es idempotente. No toca Instalacion.codigo ni el
modelo Zona: solo AGREGA a ZonaOperativa/Nominativo.

Uso:
    python manage.py sembrar_nominativos --dry-run
    python manage.py sembrar_nominativos --reset   # borra y resiembra limpio
    python manage.py sembrar_nominativos
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.models import Instalacion, ZonaOperativa, Nominativo, Zona

_COD_RE = re.compile(r'^([A-Z]{1,3})\s*0*(\d+)$')
_ZONA_NUM_RE = re.compile(r'(\d+)')


class Command(BaseCommand):
    help = "Crea Zonas (1/2/3) y Nominativos (letra+numero) desde los codigos y la zona actual de cada instalacion."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra, no escribe.')
        parser.add_argument('--reset', action='store_true', help='Borra ZonaOperativa/Nominativo antes de sembrar.')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        reset = options.get('reset')

        # 1) Mapa instalacion_id -> (numero de zona, titulo) desde el modelo viejo Zona.
        inst_zona = {}
        for z in Zona.objects.select_related('instalacion'):
            inst = z.instalacion
            if not inst:
                continue
            m = _ZONA_NUM_RE.search(str(z.titulo or ''))
            if not m:
                continue
            inst_zona[inst.id] = (int(m.group(1)), str(z.titulo).strip())

        # 2) Instalaciones con codigo valido y con zona conocida.
        insts = list(Instalacion.objects.exclude(codigo__isnull=True).exclude(codigo='').order_by('codigo'))
        parsed = []       # (instalacion, letra, numero, zona_num, zona_nombre)
        invalidos = []    # codigo no cumple letra(1-3)+numero
        sin_zona = []     # sin zona en el modelo viejo
        for inst in insts:
            cod = str(inst.codigo or '').strip().upper()
            m = _COD_RE.match(cod)
            if not m:
                invalidos.append((inst.id, cod))
                continue
            zi = inst_zona.get(inst.id)
            if not zi:
                sin_zona.append((inst.id, cod))
                continue
            parsed.append((inst, m.group(1), int(m.group(2)), zi[0], zi[1]))

        zonas_nums = sorted({(zn, znm) for (_i, _l, _n, zn, znm) in parsed})

        self.stdout.write(f"Instalaciones con codigo: {len(insts)}")
        self.stdout.write(f"Codigos validos y con zona: {len(parsed)}")
        self.stdout.write(f"Codigos invalidos (se omiten): {len(invalidos)}")
        for iid, cod in invalidos[:15]:
            self.stdout.write(f"    - instalacion {iid}: '{cod}'")
        self.stdout.write(f"Sin zona en modelo viejo (se omiten): {len(sin_zona)}")
        for iid, cod in sin_zona[:15]:
            self.stdout.write(f"    - instalacion {iid}: '{cod}'")
        self.stdout.write(f"Zonas detectadas: {len(zonas_nums)} -> {', '.join(f'Zona {n}' for n, _t in zonas_nums)}")

        # Simular: mismo codigo en 2 instalaciones -> MISMO cliente (permitido) vs DISTINTO (conflicto).
        por_codigo = {}
        for inst, letra, numero, _zn, _znm in parsed:
            por_codigo.setdefault((letra, numero), []).append(inst)
        repes_mismo, conflictos_sim = [], []
        for (letra, numero), lst in por_codigo.items():
            if len(lst) < 2:
                continue
            clientes = {i.cliente_id for i in lst}
            if len(clientes) == 1:
                repes_mismo.append((f"{letra}{numero}", len(lst)))
            else:
                conflictos_sim.append((f"{letra}{numero}", [i.id for i in lst]))
        self.stdout.write(f"Codigos repetidos MISMO cliente (permitidos): {len(repes_mismo)}")
        for cod, n in repes_mismo[:15]:
            self.stdout.write(f"    - {cod}: {n} instalaciones")
        self.stdout.write(f"Conflictos (mismo codigo, cliente DISTINTO): {len(conflictos_sim)}")
        for cod, ids in conflictos_sim[:15]:
            self.stdout.write(f"    - {cod}: instalaciones {ids}")

        if dry:
            self.stdout.write("Dry-run: no se escribio nada.")
            return

        creadas_z = creados_n = repetidos_ok = movidos = conflictos = 0
        with transaction.atomic():
            if reset:
                nb = Nominativo.objects.all().delete()[0]
                zb = ZonaOperativa.objects.all().delete()[0]
                self.stdout.write(f"Reset: borrados {nb} nominativos y {zb} zonas.")

            # 3) Crear zonas por numero (Zona 1, 2, 3...).
            zona_por_num = {}
            for zn, znm in zonas_nums:
                z = ZonaOperativa.objects.filter(numero=zn).first()
                if not z:
                    z = ZonaOperativa.objects.create(numero=zn, nombre=znm)
                    creadas_z += 1
                zona_por_num[zn] = z

            # 4) Crear/ligar nominativos (letra vive en el nominativo).
            for inst, letra, numero, zn, _znm in parsed:
                z = zona_por_num[zn]
                # ¿esta instalacion ya tiene nominativo? (idempotencia)
                nom = Nominativo.objects.filter(instalacion=inst).first()
                if nom:
                    changed = False
                    if (nom.letra, nom.numero) != (letra, numero):
                        nom.letra, nom.numero = letra, numero
                        changed = True
                    if nom.zona_id != z.id:
                        nom.zona = z
                        movidos += 1
                        changed = True
                    if changed:
                        nom.save()
                    continue
                # ¿el codigo ya existe en otra(s) instalacion(es)?
                otros = list(Nominativo.objects.filter(letra=letra, numero=numero).select_related('instalacion'))
                if otros:
                    otros_cli = {o.instalacion.cliente_id for o in otros if o.instalacion_id}
                    if otros_cli and inst.cliente_id not in otros_cli:
                        conflictos += 1  # codigo en cliente DISTINTO -> no se crea
                        continue
                    # mismo cliente -> se PERMITE repetir el codigo
                    Nominativo.objects.create(zona=z, letra=letra, numero=numero, instalacion=inst)
                    repetidos_ok += 1
                    continue
                Nominativo.objects.create(zona=z, letra=letra, numero=numero, instalacion=inst)
                creados_n += 1

        self.stdout.write(self.style.SUCCESS(
            f"Zonas creadas: {creadas_z} | Nominativos creados: {creados_n} | "
            f"repetidos mismo cliente: {repetidos_ok} | movidos de zona: {movidos} | "
            f"conflictos (cliente distinto) omitidos: {conflictos}"
        ))
