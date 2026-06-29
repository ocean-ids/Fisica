"""Importa el catálogo de parroquias (DPA INEC) desde CoreFisica/data/parroquias_ec.json.

Enlaza cada parroquia a su Cantón existente, emparejando por nombre normalizado
(exacto -> por subcadena -> alias de variantes). Idempotente: usa get_or_create.

Uso:  python manage.py importar_parroquias
"""
import json
import os
import re
import unicodedata

from django.core.management.base import BaseCommand
from CoreFisica.models import Canton, Parroquia


def _norm(s):
    """Normaliza: mayúsculas, sin acentos/ñ, y separadores (guiones, puntos) -> espacio."""
    s = str(s or '').strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


# Alias para variantes de abreviatura (clave y valor se comparan ya normalizados).
_ALIAS = {
    'CRNEL MARCELINO MARIDUENA': 'CORONEL MARCELINO MARIDUENA',
    'GNRAL ANTONIO ELIZALDE': 'GENERAL ANTONIO ELIZALDE',
    'EMPALME': 'EL EMPALME',
    '24 DE MAYO': 'VEINTICUATRO DE MAYO',
}


class Command(BaseCommand):
    help = 'Importa parroquias (DPA INEC) y las enlaza a los cantones existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Borra todas las parroquias antes de importar (re-siembra limpia).')

    def handle(self, *args, **options):
        if options.get('reset'):
            borradas = Parroquia.objects.count()
            Parroquia.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Reset: {borradas} parroquias borradas.'))
        ruta = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'parroquias_ec.json')
        ruta = os.path.abspath(ruta)
        with open(ruta, encoding='utf-8') as f:
            rows = json.load(f)

        # Índices de cantones: (provincia_norm, canton_norm) -> Canton, y por provincia lista.
        cantones = list(Canton.objects.select_related('provincia'))
        por_clave = {(_norm(c.provincia.nombre), _norm(c.nombre)): c for c in cantones}
        por_provincia = {}
        for c in cantones:
            por_provincia.setdefault(_norm(c.provincia.nombre), []).append(c)

        def resolver_canton(prov_n, cant_n):
            # 1) exacto
            c = por_clave.get((prov_n, cant_n))
            if c:
                return c
            # 2) alias
            ali = _ALIAS.get(cant_n)
            if ali:
                c = por_clave.get((prov_n, _norm(ali)))
                if c:
                    return c
            # 3) por subcadena dentro de la misma provincia
            candidatos = por_provincia.get(prov_n, [])
            for c in candidatos:
                cn = _norm(c.nombre)
                if cant_n in cn or cn in cant_n:
                    return c
            return None

        creadas = 0
        existentes = 0
        sin_canton = {}
        for r in rows:
            prov_n = _norm(r['provincia'])
            cant_n = _norm(r['canton'])
            canton = resolver_canton(prov_n, cant_n)
            if not canton:
                sin_canton.setdefault((r['provincia'], r['canton']), 0)
                sin_canton[(r['provincia'], r['canton'])] += 1
                continue
            _, creado = Parroquia.objects.get_or_create(
                canton=canton, nombre=str(r['parroquia']).strip().upper(),
                defaults={'codigo': r.get('cod_parroquia', '')},
            )
            creadas += int(creado)
            existentes += int(not creado)

        self.stdout.write(self.style.SUCCESS(
            f'Parroquias: {creadas} creadas, {existentes} ya existían. '
            f'Cantones sin match: {len(sin_canton)} ({sum(sin_canton.values())} parroquias).'
        ))
        for (prov, cant), n in sorted(sin_canton.items()):
            self.stdout.write(f'  SIN CANTÓN: {prov} / {cant} ({n} parroquias)')
