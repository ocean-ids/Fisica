"""Utilities para parseo de texto de horarios de `Puesto`.

Funciones principales:
- `expand_days(token)`: convierte tokens de día/rango en lista de enteros 1..7.
- `parse_input(text)`: convierte cadenas como "1 14H L-V / 9H S / 5H D"
  en lista de diccionarios {'dia', 'horas', 'cantidad'}.
"""

import re
import unicodedata
from typing import List, Dict, Optional


DAY_MAP = {'L': 1, 'M': 2, 'X': 3, 'J': 4, 'V': 5, 'S': 6, 'D': 7}
DAY_NAMES = {
    'LUNES': 1, 'MARTES': 2, 'MIERCOLES': 3, 'JUEVES': 4,
    'VIERNES': 5, 'SABADO': 6, 'DOMINGO': 7
}


def _strip_accents(s: str) -> str:
    """Quita acentos de la cadena y devuelve la forma sin diacríticos."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def _day_token_to_number(tok: str) -> Optional[int]:
    """Convierte un token de día ('L', 'Lunes', 'Miércoles') en su número 1..7.

    Devuelve ``None`` si no reconoce el token.
    """
    tok = (tok or '').strip()
    if not tok:
        return None
    key = _strip_accents(tok).upper()
    if key in DAY_MAP:
        return DAY_MAP[key]
    if key in DAY_NAMES:
        return DAY_NAMES[key]
    return DAY_MAP.get(key[0], None)


def expand_days(token: str) -> List[int]:
    """Convierte 'L-V', 'L,M,X' o 'Lunes' en lista de enteros 1..7.

    - Acepta letras, nombres completos, rangos con '-' y listas separadas por ','.
    - Devuelve lista sin duplicados, en el orden especificado.
    """
    token = (token or '').strip()
    if not token:
        return []
    token_clean = token.upper().replace(' ', '')
    if '-' in token_clean:
        a, b = token_clean.split('-', 1)
        na = _day_token_to_number(a)
        nb = _day_token_to_number(b)
        if na is None or nb is None:
            raise ValueError(f"Rango inválido: {token}")
        if na <= nb:
            return list(range(na, nb + 1))
        # rango circular (ej. V-L)
        return list(range(na, 8)) + list(range(1, nb + 1))

    parts = [p for p in token_clean.split(',') if p]
    days: List[int] = []
    for p in parts:
        n = _day_token_to_number(p)
        if n is None:
            raise ValueError(f"Día inválido: {p}")
        if n not in days:
            days.append(n)
    return days


def parse_input(text: str) -> List[Dict[str, int]]:
    """Parsea la entrada y devuelve una lista de reglas.

    Ejemplo: "1 14H L-V Diurno / 9H S Ambos / 5H D" ->
    [{'dia':1,'horas':14,'cantidad':1,'turno':'Diurno'}, ...]
    """
    text = (text or '').strip()
    if not text:
        return []

    qty = 1
    m_qty = re.match(r'^\s*(\d+)\s+(.*)$', text)
    if m_qty:
        qty = int(m_qty.group(1))
        text = m_qty.group(2)

    rules: List[Dict[str, int]] = []
    for seg in text.split('/'):
        seg = seg.strip()
        if not seg:
            continue
        # Captura horas, días y turno opcional (Diurno/Nocturno/24h o D/N/A/H)
        m = re.match(
            r'(?P<h>\d+)\s*H\s*(?P<d>.+?)(?:\s+(?P<t>diurno|nocturno|ambos|d|n|a|h|24h))?$',
            seg,
            flags=re.I,
        )
        if not m:
            raise ValueError(f"Formato inválido en segmento: '{seg}'")
        hours = int(m.group('h'))
        days_token = m.group('d').strip()
        raw_turno = (m.group('t') or '').lower()
        if raw_turno.startswith('d'):
            turno = 'Diurno'
        elif raw_turno.startswith('n'):
            turno = 'Nocturno'
        elif raw_turno.startswith('a') or raw_turno.startswith('h') or raw_turno.startswith('24'):
            turno = 'Ambos'
        else:
            turno = 'Diurno'  
        days = expand_days(days_token)
        for d in days:
            rules.append({'dia': d, 'horas': hours, 'cantidad': qty, 'turno': turno})
    return rules


import unicodedata


def normalizar_nombre(nombre):
    """Normaliza un nombre para comparar sin acentos, guiones, puntuación ni mayúsculas.
    Ej: 'EL-ORO', 'EL ORO', 'el oro' -> 'EL ORO'."""
    s = str(nombre or '').strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    # Tratar guiones, puntos y cualquier separador no alfanumérico como espacio
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


def buscar_o_crear_provincia(provincia_token, Provincia):
    """Devuelve o crea una Provincia a partir de id o nombre, sin duplicar por acentos/mayúsculas."""
    if not provincia_token:
        return None
    # Intentar por id
    try:
        obj = Provincia.objects.filter(pk=int(provincia_token)).first()
        if obj:
            return obj
    except (TypeError, ValueError):
        pass
    objetivo = normalizar_nombre(provincia_token)
    if not objetivo:
        return None
    # Comparar contra existentes ya normalizadas (insensible a acentos)
    for p in Provincia.objects.all():
        if normalizar_nombre(p.nombre) == objetivo:
            return p
    return Provincia.objects.create(nombre=str(provincia_token).strip().upper())
