"""Siembra ZonaOperativa + Nominativo desde los codigos actuales de Instalacion.

Por cada instalacion con codigo tipo letra(1-3)+numero (ej. U20, AR5):
  - crea/reusa la ZonaOperativa de esa letra (Zona 1,2,3... por orden alfabetico),
  - crea/reusa el Nominativo (letra+numero) y lo liga a la instalacion.

Es idempotente (se puede correr varias veces). No toca Instalacion.codigo ni el
modelo Zona actual: solo AGREGA.

Uso:
    python manage.py sembrar_nominativos --dry-run
    python manage.py sembrar_nominativos
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from CoreFisica.models import Instalacion, ZonaOperativa, Nominativo

_COD_RE = re.compile(r'^([A-Z]{1,3})\s*0*(\d+)$')


class Command(BaseCommand):
    help = "Crea Zonas y Nominativos a partir de los codigos de Instalacion (aditivo, idempotente)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra, no escribe.')

    def handle(self, *args, **options):
        dry = options.get('dry_run')

        insts = list(Instalacion.objects.exclude(codigo__isnull=True).exclude(codigo='').order_by('codigo'))
        # 1) Descubrir letras y numeros validos.
        parsed = []       # (instalacion, letra, numero)
        invalidos = []    # codigos que no cumplen letra(1-3)+numero
        for inst in insts:
            cod = str(inst.codigo or '').strip().upper()
            m = _COD_RE.match(cod)
            if not m:
                invalidos.append((inst.id, cod))
                continue
            parsed.append((inst, m.group(1), int(m.group(2))))

        letras = sorted({l for (_i, l, _n) in parsed})

        self.stdout.write(f"Instalaciones con codigo: {len(insts)}")
        self.stdout.write(f"Codigos validos (letra 1-3 + numero): {len(parsed)}")
        self.stdout.write(f"Codigos invalidos (se omiten): {len(invalidos)}")
        for iid, cod in invalidos[:15]:
            self.stdout.write(f"    - instalacion {iid}: '{cod}'")
        self.stdout.write(f"Letras (zonas) detectadas: {len(letras)} -> {', '.join(letras)}")

        if dry:
            # Simular conflictos de nominativo (misma letra+numero en 2 instalaciones).
            vistos, conflictos = {}, 0
            for inst, letra, numero in parsed:
                k = (letra, numero)
                if k in vistos:
                    conflictos += 1
                else:
                    vistos[k] = inst.id
            self.stdout.write(f"Conflictos (mismo nominativo en 2 instalaciones): {conflictos}")
            self.stdout.write("Dry-run: no se escribio nada.")
            return

        creadas_z = creados_n = ligados = conflictos = 0
        with transaction.atomic():
            # 2) Crear zonas por letra (numero = orden alfabetico, sin pisar existentes).
            zona_por_letra = {}
            siguiente_num = (ZonaOperativa.objects.order_by('-numero').values_list('numero', flat=True).first() or 0)
            for letra in letras:
                z = ZonaOperativa.objects.filter(letra=letra).first()
                if not z:
                    siguiente_num += 1
                    z = ZonaOperativa.objects.create(numero=siguiente_num, nombre=letra, letra=letra)
                    creadas_z += 1
                zona_por_letra[letra] = z

            # 3) Crear/ligar nominativos.
            for inst, letra, numero in parsed:
                z = zona_por_letra[letra]
                nom = Nominativo.objects.filter(zona=z, numero=numero).first()
                if nom:
                    if nom.instalacion_id and nom.instalacion_id != inst.id:
                        conflictos += 1  # ya ligado a otra instalacion
                        continue
                    if not nom.instalacion_id:
                        nom.instalacion = inst
                        nom.save(update_fields=['instalacion'])
                        ligados += 1
                    continue
                Nominativo.objects.create(zona=z, numero=numero, instalacion=inst)
                creados_n += 1

        self.stdout.write(self.style.SUCCESS(
            f"Zonas creadas: {creadas_z} | Nominativos creados: {creados_n} | "
            f"ligados a existentes: {ligados} | conflictos omitidos: {conflictos}"
        ))
