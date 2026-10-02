"""Alinea los meses SIGUIENTES de Asignaciones con un mes base.

Contexto: al importar el Excel de asignaciones, el sistema copia las asignaciones a los
24 meses siguientes. Esas copias no se actualizaban cuando después se editaba el mes base
(se cambia a alguien de puesto, se asigna a alguien nuevo...), y los meses siguientes
quedaban con una foto vieja. Este módulo los vuelve a alinear con el mes base:

  0. ACOTAR: una asignación recurrente con end_date vacío se acota al fin de SU mes
     (abierta se cuela, duplicada, en los meses siguientes).
  1. REGISTROS: cada persona del mes base queda en el mismo puesto, con el mismo orden,
     horario y estado en los meses siguientes (se crea la fila si no existía).
  2. SOBRANTES: si un puesto queda con más filas activas que en el mes base, se desactiva
     la que sobra (personas FIJOS que ya no están en el mes base, o vacantes). No se toca a
     RETEN / SACAVACACIONES / SACAFRANCO que solo existen en el mes siguiente: se informan.
  3. CRONOGRAMA: el turno de cada persona continúa la secuencia donde terminó el mes base
     (ciclo exacto de su cronograma). Solo se reescribe un cronograma vacío o que es un ciclo
     limpio; si tiene cambios a mano (vacaciones, coberturas) NO se toca y se informa.
  4. SACAFRANCO (solo al alinear el mes completo): cada sacafranco del mes base queda en la
     misma vista, con el mismo orden, provincia y horario en los meses siguientes (se crea la
     fila si no existía) y su cronograma continúa la secuencia. Los sacafranco que solo existen
     en el mes siguiente se informan; solo se eliminan con `quitar_sacafranco_sobrantes=True`.
  5. SOLO DE OCTUBRE (opcional, `quitar_solo_octubre=True`): las personas RETEN / SACAVACACIONES /
     SACAFRANCO que tienen asignación en el mes siguiente pero NO en el mes base se desactivan
     (y el puesto vuelve a su vacante si el mes base la tenía), y sus filas de sacafranco que
     no están en el mes base se eliminan. Evita personas que salen duplicadas (asignación y
     sacafranco) o que ya no van. Por defecto solo se informan.

Las pestañas / vistas personalizadas de Asignaciones son filtros guardados (cantón, empresa,
instalación, tipo) que usan el mismo orden global (provincia, orden, id): al dejar iguales los
registros y el orden, TODAS las vistas quedan iguales al mes base.

No borra nada: solo actualiza, crea o desactiva (estado INACTIVO). Se puede repetir.

- `alinear_meses(...)`: lo usa el comando `continuar_meses_desde` y `asegurar_horizonte`.
- `asegurar_horizonte(...)`: lo usa el comando `cierre_de_mes`. NO se copian cambios en vivo a los
  meses siguientes: el mes siguiente se crea (o se re-alinea) UNA vez, al cambiar de mes, desde el
  estado final del mes que termina.
"""
import datetime
import logging
from collections import Counter, defaultdict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Asignacion, AsignacionSemanal, Persona, SacafrancoFila, SacafrancoFilaSemanal

logger = logging.getLogger(__name__)

DIAS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
# Tipos que pueden existir solo en un mes siguiente (no se desactivan por no estar en el base).
TIPOS_PROTEGIDOS = {'RETEN', 'SACAVACACIONES', 'SACAFRANCO'}
CAMPOS_COPIA = (
    'cliente_id', 'instalacion_id', 'puesto_id', 'horario_id', 'patronAsignacion_id',
    'sacafranco_grupo_id', 'agregar_sacafranco', 'es_hueca', 'orden', 'estado',
    'cedula_color', 'publicada_calendario',
)
MESES_POR_DEFECTO = 12
# HORIZONTE OPERATIVO: SOLO el mes actual. No se copia nada por adelantado: el mes siguiente se GENERA
# una sola vez, la última noche del mes, desde el estado final del mes que termina (`cierre_de_mes`).
# (Para generar los N meses siguientes, `asegurar_horizonte(meses_adelante=N)`.)
MESES_ADELANTE = 0


def sumar_meses(anio, mes, k):
    n = anio * 12 + (mes - 1) + k
    return n // 12, n % 12 + 1


def ultimo_dia(anio, mes):
    ay, am = sumar_meses(anio, mes, 1)
    return (datetime.date(ay, am, 1) - datetime.timedelta(days=1)).day


def tokens_mes(filas, anio, mes):
    """Token de turno por día del mes (lista). filas: {week_start: AsignacionSemanal}.
    Acepta semanas estilo mensual (día 1 + saltos de 7) y estilo ISO (lunes)."""
    d1 = datetime.date(anio, mes, 1)
    out = []
    for d in range(1, ultimo_dia(anio, mes) + 1):
        fecha = datetime.date(anio, mes, d)
        fila = (filas.get(d1 + datetime.timedelta(days=((d - 1) // 7) * 7))
                or filas.get(fecha - datetime.timedelta(days=fecha.weekday())))
        out.append((getattr(fila, DIAS[fecha.weekday()], '') or '').strip().upper() if fila else '')
    return out


def periodo_exacto(seq):
    """Largo del ciclo si seq es un ciclo exacto repetido al menos 2 veces; None si no."""
    n = len(seq)
    if n == 0 or any(not t for t in seq):
        return None
    for p in range(1, n // 2 + 1):
        if all(seq[i] == seq[i % p] for i in range(n)):
            return p
    return None


def ciclo_de_continuacion(tokens):
    """Ciclo con el que continuar el cronograma del mes siguiente: (ciclo, ancla) o None.

    ciclo[(i - ancla) % len(ciclo)] es el turno del día i (0 = día 1 del mes base).
    1) Si todo el mes es un ciclo exacto, ese ciclo (ancla 0).
    2) Si el mes tiene cambios a mano, el ciclo de sus ÚLTIMOS días (28, 21 o 14): la secuencia
       en que quedó el mes. Se exige que el ciclo tenga al menos 2 turnos distintos (no se
       continúa indefinidamente un día suelto como una vacación).
    3) Si no hay ciclo claro, None (no se inventa un cronograma)."""
    n = len(tokens)
    p = periodo_exacto(tokens)
    if p:
        return tokens[:p], 0
    for largo in (28, 21, 14):
        if n < largo:
            continue
        cola = tokens[-largo:]
        p = periodo_exacto(cola)
        if p and p > 1 and len(set(cola[:p])) > 1:
            return cola[:p], n - largo
    return None


def escribir_mes(asig, anio, mes, tokens):
    """Reemplaza el cronograma del mes de esta asignación (semanas estilo mensual)."""
    d1 = datetime.date(anio, mes, 1)
    ult = datetime.date(anio, mes, ultimo_dia(anio, mes))
    AsignacionSemanal.objects.filter(
        asignacion_id=asig.id,
        week_start__gte=d1 - datetime.timedelta(days=6), week_start__lte=ult,
    ).delete()
    semanas = defaultdict(dict)
    for d, tok in enumerate(tokens, start=1):
        fecha = datetime.date(anio, mes, d)
        ws = d1 + datetime.timedelta(days=((d - 1) // 7) * 7)
        semanas[ws][DIAS[fecha.weekday()]] = tok
    AsignacionSemanal.objects.bulk_create([
        AsignacionSemanal(asignacion_id=asig.id, puesto_id=asig.puesto_id, week_start=ws,
                          **{dia: m.get(dia, '') for dia in DIAS})
        for ws, m in semanas.items()
    ])


def escribir_mes_saca(fila, anio, mes, tokens):
    """Reemplaza el cronograma del mes de esta fila de sacafranco (semanas estilo mensual)."""
    d1 = datetime.date(anio, mes, 1)
    ult = datetime.date(anio, mes, ultimo_dia(anio, mes))
    SacafrancoFilaSemanal.objects.filter(
        sacafranco_fila_id=fila.id,
        week_start__gte=d1 - datetime.timedelta(days=6), week_start__lte=ult,
    ).delete()
    semanas = defaultdict(dict)
    for d, tok in enumerate(tokens, start=1):
        fecha = datetime.date(anio, mes, d)
        ws = d1 + datetime.timedelta(days=((d - 1) // 7) * 7)
        semanas[ws][DIAS[fecha.weekday()]] = tok
    SacafrancoFilaSemanal.objects.bulk_create([
        SacafrancoFilaSemanal(sacafranco_fila_id=fila.id, week_start=ws,
                              **{dia: m.get(dia, '') for dia in DIAS})
        for ws, m in semanas.items()
    ])


def _filtro(personas, puestos):
    """Q para limitar las filas a ciertas personas/puestos; None = sin límite."""
    if personas is None and puestos is None:
        return None
    q = Q(pk__in=[])
    if personas:
        q |= Q(persona_id__in=personas)
    if puestos:
        q |= Q(puesto_id__in=puestos)
    return q


def alinear_meses(mes, anio, meses=MESES_POR_DEFECTO, personas=None, puestos=None, log=None,
                  incluir_sacafranco=None, quitar_sacafranco_sobrantes=False, quitar_solo_octubre=False,
                  conservar_personas=None, crear_meses=False):
    """Alinea los `meses` meses siguientes a (mes, anio) con ese mes base.

    personas / puestos: conjuntos de ids para limitar el alcance (None = todo el mes).
    log: función opcional que recibe una línea de detalle por cada cambio.
    incluir_sacafranco: alinear también las filas de sacafranco (por defecto solo si se alinea
        el mes completo). quitar_sacafranco_sobrantes: eliminar los sacafranco que solo existen
        en el mes siguiente (por defecto solo se informan).
    quitar_solo_octubre: desactivar RETEN / SACAVACACIONES / SACAFRANCO con asignación solo en el
        mes siguiente (y eliminar sus filas de sacafranco que no están en el mes base).
    conservar_personas: ids de personas que NO se quitan aunque estén solo en el mes siguiente.
    crear_meses: crear el mes siguiente aunque todavía no tenga filas (lo usa `asegurar_horizonte`).
    Devuelve una lista [(anio, mes, Counter), ...] de los meses revisados."""
    log = log or (lambda msg: None)
    conservar = set(conservar_personas or ())
    flt = _filtro(personas, puestos)
    base_qs = Asignacion.objects.filter(mes=mes, anio=anio).select_related('persona')
    if flt is not None:
        base_qs = base_qs.filter(flt)
    base = list(base_qs)
    if not base and flt is None:
        return []
    base_filas = defaultdict(dict)
    for r in AsignacionSemanal.objects.filter(asignacion_id__in=[a.id for a in base]):
        base_filas[r.asignacion_id][r.week_start] = r
    base_por_persona = {a.persona_id: a for a in base if a.persona_id}
    # Todas las personas que tienen fila en el mes base (aunque no estén en el alcance): una
    # persona solo "sobra" en un mes siguiente si NO está en el mes base en ningún puesto.
    personas_en_base = set(Asignacion.objects.filter(
        mes=mes, anio=anio, persona_id__isnull=False).values_list('persona_id', flat=True))

    if incluir_sacafranco is None:
        incluir_sacafranco = flt is None
    base_saca, base_saca_filas = [], defaultdict(dict)
    if incluir_sacafranco:
        base_saca = list(SacafrancoFila.objects.filter(mes=mes, anio=anio, persona__isnull=False)
                         .select_related('persona').order_by('orden', 'id'))
        for r in SacafrancoFilaSemanal.objects.filter(sacafranco_fila_id__in=[f.id for f in base_saca]):
            base_saca_filas[r.sacafranco_fila_id][r.week_start] = r

    resultados = []
    # 0) Acotar el propio mes base.
    res0 = Counter()
    _acotar(base, anio, mes, res0)
    if res0:
        resultados.append((anio, mes, res0))
    for k in range(1, meses + 1):
        ty, tm = sumar_meses(anio, mes, k)
        if not crear_meses and not Asignacion.objects.filter(mes=tm, anio=ty).exists():
            continue
        res = _alinear_mes(base, base_por_persona, personas_en_base, base_filas, mes, anio, tm, ty,
                           personas, puestos, flt, log, quitar_solo_octubre and personas is None, conservar)
        if incluir_sacafranco:
            res.update(_alinear_sacafranco(base_saca, base_saca_filas, mes, anio, tm, ty,
                                           quitar_sacafranco_sobrantes or quitar_solo_octubre, log, conservar))
        resultados.append((ty, tm, res))
    return resultados


def _acotar(filas, anio, mes, res):
    """Una asignación recurrente con end_date vacío se acota al fin de su mes."""
    fin = datetime.date(anio, mes, ultimo_dia(anio, mes))
    for a in filas:
        if a.recurring and a.end_date is None:
            Asignacion.objects.filter(pk=a.pk).update(end_date=fin)
            a.end_date = fin
            res['filas acotadas al fin de su mes'] += 1


def _alinear_mes(base, base_por_persona, personas_en_base, base_filas, bm, by, tm, ty,
                 personas, puestos, flt, log, quitar_solo_octubre=False, conservar=frozenset()):
    res = Counter()
    destino_qs = Asignacion.objects.filter(mes=tm, anio=ty).select_related('persona')
    if flt is not None:
        destino_qs = destino_qs.filter(flt)
    destino = list(destino_qs)
    dest_por_persona = {a.persona_id: a for a in destino if a.persona_id}
    d1, ult = datetime.date(ty, tm, 1), datetime.date(ty, tm, ultimo_dia(ty, tm))
    offset = (d1 - datetime.date(by, bm, 1)).days      # días entre el día 1 del mes base y el del destino
    _acotar(destino, ty, tm, res)

    # ---- 1) REGISTROS: cada persona del mes base queda como en el mes base ----
    for pid, b in base_por_persona.items():
        if personas is not None and pid not in personas:
            continue
        nuevos = {c: getattr(b, c) for c in CAMPOS_COPIA}
        t = dest_por_persona.get(pid)
        if t is None:
            if b.estado != 'ACTIVO' or not getattr(b.persona, 'is_active', True):
                continue          # ni inactivas ni de personas desactivadas
            t = Asignacion.objects.create(
                persona_id=pid, mes=tm, anio=ty, recurring=True, start_date=d1, end_date=ult,
                fecha=None, **nuevos)
            dest_por_persona[pid] = t
            destino.append(t)
            res['filas creadas'] += 1
            log(f'CREAR  {b.persona} -> puesto {b.puesto_id}')
            continue
        cambios = {c: v for c, v in nuevos.items() if getattr(t, c) != v}
        if not cambios:
            continue
        if 'puesto_id' in cambios:
            res['personas movidas de puesto'] += 1
            AsignacionSemanal.objects.filter(asignacion_id=t.id).update(puesto_id=b.puesto_id)
            log(f'MOVER  {b.persona}: puesto {t.puesto_id} -> {b.puesto_id}')
        if 'estado' in cambios:
            res['estados corregidos'] += 1
        if set(cambios) <= {'orden'}:
            res['orden corregido'] += 1
        Asignacion.objects.filter(pk=t.pk).update(**cambios)
        for c, v in cambios.items():
            setattr(t, c, v)

    # ---- 1b) SOLO DE OCTUBRE (opcional): retenes / sacavacaciones / sacafranco que no están en el base ----
    if quitar_solo_octubre:
        for a in destino:
            if (a.estado == 'ACTIVO' and a.persona_id and a.persona_id not in personas_en_base
                    and a.persona_id not in conservar
                    and getattr(a.persona, 'tipo', '') in TIPOS_PROTEGIDOS):
                Asignacion.objects.filter(pk=a.pk).update(estado='INACTIVO')
                a.estado = 'INACTIVO'
                res['retenes/sacavacaciones/sacafranco solo del mes siguiente desactivados'] += 1
                log(f'DESACTIVAR (solo del mes siguiente) {a.persona} [{a.persona.tipo}] puesto {a.puesto_id}')

    # ---- 2) SOBRANTES / FALTANTES por puesto ----
    # Se cuentan solo las filas VISIBLES: activas y sin persona con la ficha desactivada
    # (la pantalla oculta a las personas desactivadas, así que no ocupan cupo).
    def _cuenta(a):
        return a.estado == 'ACTIVO' and (not a.persona_id or getattr(a.persona, 'is_active', True))

    base_activas = Counter(a.puesto_id for a in base if _cuenta(a))
    dest_activas = defaultdict(list)
    for a in destino:
        if _cuenta(a):
            dest_activas[a.puesto_id].append(a)
    for puesto_id in set(base_activas) | set(dest_activas):
        if puestos is not None and puesto_id not in puestos:
            continue
        exceso = len(dest_activas[puesto_id]) - base_activas[puesto_id]
        if exceso > 0:
            # Primero las personas FIJOS que ya no están en el mes base, luego las vacantes.
            cand = [a for a in dest_activas[puesto_id]
                    if a.persona_id and a.persona_id not in personas_en_base
                    and getattr(a.persona, 'tipo', '') not in TIPOS_PROTEGIDOS]
            cand += [a for a in dest_activas[puesto_id] if not a.persona_id]
            for a in cand[:exceso]:
                Asignacion.objects.filter(pk=a.pk).update(estado='INACTIVO')
                a.estado = 'INACTIVO'
                res['filas desactivadas (sobraban)'] += 1
                log(f'DESACTIVAR  puesto {puesto_id}: {a.persona or "VACANTE"}')
            if exceso > len(cand):
                res['puestos con sobrantes sin resolver (retenes/sacavacaciones/sacafranco)'] += 1
        elif exceso < 0:
            # Faltan filas activas: solo se pueden recrear las VACANTES del mes base.
            vacantes_base = [a for a in base if a.estado == 'ACTIVO' and a.puesto_id == puesto_id and not a.persona_id]
            for b in vacantes_base[:-exceso]:
                nueva = Asignacion.objects.create(
                    persona=None, mes=tm, anio=ty, recurring=True, start_date=d1, end_date=ult, fecha=None,
                    **{c: getattr(b, c) for c in CAMPOS_COPIA})
                res['vacantes creadas'] += 1
                log(f'VACANTE nueva en puesto {puesto_id}')
                # Si la vacante tenía cronograma, también continúa su secuencia.
                cont = ciclo_de_continuacion(tokens_mes(base_filas.get(b.id, {}), by, bm))
                if cont:
                    ciclo, ancla = cont
                    escribir_mes(nueva, ty, tm, [ciclo[(offset + d - ancla) % len(ciclo)]
                                                 for d in range(ultimo_dia(ty, tm))])

    # ---- 3) CRONOGRAMA: continuar la secuencia donde terminó el mes base ----
    offset = (datetime.date(ty, tm, 1) - datetime.date(by, bm, 1)).days
    ids = [a.id for a in destino if a.persona_id in base_por_persona and a.estado == 'ACTIVO']
    dest_filas = defaultdict(dict)
    for r in AsignacionSemanal.objects.filter(asignacion_id__in=ids):
        dest_filas[r.asignacion_id][r.week_start] = r
    for a in destino:
        if a.id not in ids:
            continue
        if personas is not None and a.persona_id not in personas:
            continue
        b = base_por_persona.get(a.persona_id)
        if b is None or a.estado != 'ACTIVO':
            continue
        tokens_base = tokens_mes(base_filas.get(b.id, {}), by, bm)
        cont = ciclo_de_continuacion(tokens_base)
        if cont is None:
            res['cronogramas no continuados (el mes base no tiene un ciclo claro)'] += 1
            log(f'CRONOGRAMA OMITIDO {a.persona}: el mes base no tiene un ciclo claro')
            continue
        ciclo, ancla = cont
        p = len(ciclo)
        deseado = [ciclo[(offset + d - ancla) % p] for d in range(ultimo_dia(ty, tm))]
        actual = tokens_mes(dest_filas.get(a.id, {}), ty, tm)
        if actual == deseado:
            continue
        limpio = (not any(actual)) or periodo_exacto(actual) is not None
        if not limpio:
            res['cronogramas con cambios a mano (no se tocan)'] += 1
            log(f'CRONOGRAMA CON CAMBIOS A MANO {a.persona}: no se toca')
            continue
        escribir_mes(a, ty, tm, deseado)
        res['cronogramas corregidos'] += 1
        log(f'CRONOGRAMA {a.persona}: continuado desde el mes base')
    return res


def _alinear_sacafranco(base_saca, base_filas, bm, by, tm, ty, quitar_sobrantes, log, conservar=frozenset()):
    """Deja las filas de sacafranco del mes (tm, ty) como las del mes base: misma vista,
    orden, provincia, horario y alcance; y su cronograma continuando la secuencia."""
    res = Counter()
    destino = list(SacafrancoFila.objects.filter(mes=tm, anio=ty).select_related('persona')
                   .order_by('orden', 'id'))
    dest_por_persona = {}
    for f in destino:
        if f.persona_id:
            dest_por_persona.setdefault(f.persona_id, f)
    base_ids = set()
    offset = (datetime.date(ty, tm, 1) - datetime.date(by, bm, 1)).days
    dest_filas = defaultdict(dict)
    for r in SacafrancoFilaSemanal.objects.filter(sacafranco_fila_id__in=[f.id for f in destino]):
        dest_filas[r.sacafranco_fila_id][r.week_start] = r

    vistos = set()
    for b in base_saca:
        if b.persona_id in vistos:
            continue                      # persona repetida en el mes base: se usa la primera
        vistos.add(b.persona_id)
        base_ids.add(b.persona_id)
        campos = {
            'orden': b.orden, 'provincia_id': b.provincia_id, 'hora_ingreso': b.hora_ingreso,
            'hora_salida': b.hora_salida, 'cantones': list(b.cantones or []),
            'clientes': list(b.clientes or []), 'vista_id': b.vista_id,
        }
        t = dest_por_persona.get(b.persona_id)
        if t is None:
            if not getattr(b.persona, 'is_active', True):
                continue          # no se crean filas de personas desactivadas
            t = SacafrancoFila.objects.create(mes=tm, anio=ty, persona_id=b.persona_id, **campos)
            dest_por_persona[b.persona_id] = t
            res['sacafranco creados'] += 1
            log(f'SACAFRANCO CREAR {b.persona}')
        else:
            cambios = {c: v for c, v in campos.items() if getattr(t, c) != v}
            if cambios:
                if 'vista_id' in cambios:
                    res['sacafranco movidos de vista'] += 1
                    log(f'SACAFRANCO VISTA {b.persona}: {t.vista_id} -> {b.vista_id}')
                elif set(cambios) <= {'orden'}:
                    res['sacafranco con orden corregido'] += 1
                else:
                    res['sacafranco corregidos'] += 1
                SacafrancoFila.objects.filter(pk=t.pk).update(**cambios)
                for c, v in cambios.items():
                    setattr(t, c, v)
        # Cronograma: continuar la secuencia donde terminó el mes base.
        tokens_base = tokens_mes(base_filas.get(b.id, {}), by, bm)
        cont = ciclo_de_continuacion(tokens_base)
        if cont is None:
            res['sacafranco: cronogramas no continuados (el mes base no tiene un ciclo claro)'] += 1
            continue
        ciclo, ancla = cont
        p = len(ciclo)
        deseado = [ciclo[(offset + d - ancla) % p] for d in range(ultimo_dia(ty, tm))]
        actual = tokens_mes(dest_filas.get(t.id, {}), ty, tm)
        if actual == deseado:
            continue
        if any(actual) and periodo_exacto(actual) is None:
            res['sacafranco: cronogramas con cambios a mano (no se tocan)'] += 1
            continue
        escribir_mes_saca(t, ty, tm, deseado)
        res['sacafranco: cronogramas corregidos'] += 1

    sobrantes = [f for f in destino if f.persona_id and f.persona_id not in base_ids
                 and f.persona_id not in conservar]
    if sobrantes and quitar_sobrantes:
        for f in sobrantes:
            log(f'SACAFRANCO ELIMINAR {f.persona}')
            f.delete()
        res['sacafranco eliminados (solo estaban en el mes siguiente)'] += len(sobrantes)
    elif sobrantes:
        res['sacafranco solo en el mes siguiente (no se tocan)'] += len(sobrantes)
    return res


def asegurar_horizonte(hoy=None, meses_adelante=MESES_ADELANTE, log=None, alinear_existentes=False):
    """Asegura que existan el mes actual y los `meses_adelante` meses siguientes.

    Los cambios que se hacen durante el mes NO se copian en vivo a los meses siguientes: el mes
    siguiente se crea (o se re-alinea con `alinear_existentes`) al cambiar de mes.

    Un mes que falta se CREA desde el estado FINAL del mes anterior: mismas personas en los
    mismos puestos, mismo orden, vacantes, sacafranco (vista y orden) y cronograma continuando
    la secuencia. Por defecto un mes que ya existe NO se toca (los cambios del mes actual ya se
    copian solos al editar): es idempotente y se puede correr a diario.

    alinear_existentes=True: además VUELVE A ALINEAR el mes siguiente aunque ya exista (por ejemplo
    una copia vieja del import), dejándolo igual al estado final del mes anterior. Pisa lo que
    alguien haya cambiado a mano en ese mes siguiente. Se usa una vez al mes, al cambiar de mes.
    Devuelve [(anio, mes, Counter), ...] de los meses creados o alineados."""
    hoy = hoy or timezone.localdate()
    creados = []
    # Seguro: si falta el mes ACTUAL (por ejemplo falló el cierre de la noche anterior), se crea desde
    # el mes anterior para que nunca se empiece un mes vacío.
    if not Asignacion.objects.filter(mes=hoy.month, anio=hoy.year).exists():
        py, pm = sumar_meses(hoy.year, hoy.month, -1)
        if Asignacion.objects.filter(mes=pm, anio=py).exists():
            with transaction.atomic():
                for _a, _m, res in alinear_meses(pm, py, meses=1, log=log, crear_meses=True):
                    if (_a, _m) == (hoy.year, hoy.month):
                        creados.append((_a, _m, res))
    for k in range(1, meses_adelante + 1):
        by, bm = sumar_meses(hoy.year, hoy.month, k - 1)
        ty, tm = sumar_meses(hoy.year, hoy.month, k)
        if Asignacion.objects.filter(mes=tm, anio=ty).exists() and not alinear_existentes:
            continue
        if not Asignacion.objects.filter(mes=bm, anio=by).exists():
            break                                  # no hay mes base desde donde crear
        with transaction.atomic():
            for _a, _m, res in alinear_meses(bm, by, meses=1, log=log, crear_meses=True):
                if (_a, _m) == (ty, tm):
                    creados.append((ty, tm, res))
    return creados


# ---------------------------------------------------------------------------
# Personas DESACTIVADAS (LIQUIDADO / SUSPENDIDO)
# ---------------------------------------------------------------------------
def limpiar_personas_desactivadas(persona_ids=None, desde=None, log=None):
    """Quita de Asignaciones a las personas desactivadas, del mes ACTUAL en adelante.

    - Sus asignaciones ACTIVAS pasan a INACTIVO (dejan de ocupar cupo y de salir en pantalla).
    - Sus filas de sacafranco se ELIMINAN, salvo las que ya tienen asistencia registrada
      (esas son historial: se conservan; igual no se muestran porque la persona está desactivada).
    - Los meses PASADOS no se tocan (son historial de asistencia, pagos y reportes).
    Sirve para todos los tipos (FIJOS, SACAFRANCO, RETEN, ...). Devuelve un Counter."""
    res = Counter()
    hoy = timezone.localdate()
    anio, mes = desde or (hoy.year, hoy.month)
    personas = Persona.objects.filter(is_active=False)
    if persona_ids is not None:
        personas = personas.filter(pk__in=list(persona_ids))
    periodo = Q(anio__gt=anio) | Q(anio=anio, mes__gte=mes)

    asig_qs = Asignacion.objects.filter(estado='ACTIVO', persona__in=personas).filter(periodo)
    if log:
        for a in asig_qs.select_related('persona')[:300]:
            log(f'ASIGNACION a INACTIVO: {a.persona} {a.mes:02d}/{a.anio} (puesto {a.puesto_id})')
    res['asignaciones de personas desactivadas pasadas a INACTIVO'] += asig_qs.update(estado='INACTIVO')

    saca_qs = SacafrancoFila.objects.filter(persona__in=personas).filter(periodo)
    con_historial = saca_qs.filter(Q(asistencias__isnull=False) | Q(historial_asistencia__isnull=False))
    borrables = saca_qs.exclude(pk__in=con_historial.values('pk'))
    n_borrar = borrables.count()
    res['filas de sacafranco conservadas (tienen asistencia registrada)'] += saca_qs.count() - n_borrar
    if log:
        for f in borrables.select_related('persona')[:300]:
            log(f'SACAFRANCO ELIMINAR: {f.persona} {f.mes:02d}/{f.anio}')
    if n_borrar:
        borrables.delete()
    res['filas de sacafranco de personas desactivadas eliminadas'] += n_borrar
    return +res

