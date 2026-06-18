"""Vistas de Puestos: CRUD, listados por cliente/instalación y secuencia de horario (rotación D/N/F)."""
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
import json
from ..models import Instalacion, Puesto, PuestoHorario, Zona, AsignacionSemanal
from ..utils import parse_input
import logging

logger = logging.getLogger(__name__)

_DOW_FIELDS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def _norm_dnf_token(value):
    """Normaliza un valor de celda del calendario a D / N / F."""
    s = (value or '').strip().upper()
    if not s:
        return 'F'  # celda vacía = día libre (franco) para la secuencia
    c = s[0]
    if c == 'D':
        return 'D'
    if c == 'N':
        return 'N'
    return 'F'  # F, 1, L u otros => franco


def _periodo(seq):
    """Período (ciclo) más corto de la secuencia, tolerante a colas parciales."""
    n = len(seq)
    for p in range(1, n):
        if all(seq[i] == seq[i + p] for i in range(n - p)):
            return p
    return n


def _secuencia_dnf_puesto(puesto_id):
    """Deriva la secuencia de rotación D/N/F del calendario de un puesto.

    Toma la asignación con más semanas registradas (la representativa), arma su
    secuencia cronológica de días, detecta el ciclo y devuelve los run-lengths
    normalizados con el/los días libres (franco) al final. Ej: DDDNNNFF -> "3,3,2".
    """
    filas_all = list(
        AsignacionSemanal.objects
        .filter(puesto_id=puesto_id)
        .order_by('asignacion_id', 'week_start')
    )
    if not filas_all:
        return ''

    por_asig = {}
    for r in filas_all:
        por_asig.setdefault(r.asignacion_id, []).append(r)

    def _build_seq(filas_sem):
        s = []
        for r in filas_sem:
            for f in _DOW_FIELDS:
                s.append(_norm_dnf_token(getattr(r, f)))
        return s

    def _runs_de(filas):
        filas = sorted(filas, key=lambda r: r.week_start)
        recientes = filas[-3:]                      # rotación vigente (no todo el historial)
        seq = _build_seq(recientes)
        if not seq:
            return []
        p = _periodo(seq)
        if p == len(seq) and len(recientes) > 1:    # sin ciclo claro -> última semana
            seq = _build_seq(filas[-1:])
            p = _periodo(seq)
        ciclo = seq[:p]
        if not ciclo:
            return []
        # Normalizar: que el/los franco queden al final (ej. DDDNNNF -> 331).
        n = len(ciclo)
        if any(t != 'F' for t in ciclo) and any(t == 'F' for t in ciclo):
            start = 0
            for i in range(n):
                if ciclo[i] != 'F' and ciclo[(i - 1) % n] == 'F':
                    start = i
                    break
            ciclo = ciclo[start:] + ciclo[:start]
        runs = []
        for t in ciclo:
            if runs and runs[-1][0] == t:
                runs[-1][1] += 1
            else:
                runs.append([t, 1])
        return runs

    # Elegir la asignación que MEJOR refleja la rotación: la que tiene más variedad
    # de letras (D/N/F), luego la de bloques más limpios. Una persona fija (todo "D")
    # da un solo bloque y se descarta -> evita el "1".
    mejor = []
    mejor_score = (0, 0)
    for filas in por_asig.values():
        runs = _runs_de(filas)
        if len(runs) <= 1:
            continue
        score = (len(set(r[0] for r in runs)), -len(runs))
        if score > mejor_score:
            mejor_score = score
            mejor = runs

    if len(mejor) <= 1:
        return ''
    # Formato sin separadores para coincidir con el del Excel original: DDDNNNF -> "331".
    return ''.join(str(cnt) for _, cnt in mejor)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secuencia_horario_puesto(request, id):
    """Devuelve la secuencia de rotación (horario) y el resumen de un puesto."""
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    puesto = Puesto.objects.filter(id=id).first()
    if not puesto:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
    return JsonResponse({
        'secuencia': _secuencia_dnf_puesto(id),
        'resumen': puesto.resumen or '',
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    if not request.user.has_perm('CoreFisica.add_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    zona_id = data.get('zona_id') or data.get('zona')
    cantidad_puestos = data.get('cantidad_puestos', 1)
    tipo = data.get('tipo')
    horarios = data.get('horarios')
    horarios_text = data.get('horarios_text')
    horario_raw = data.get('horario')
    horario_id = int(horario_raw) if horario_raw not in [None, '', 'null', 0] else None

    try:
        instalacion = Instalacion.objects.get(id=instalacion_id)
    except Instalacion.DoesNotExist:
        return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

    # Validar zona pertenece a la instalación
    zona = None
    if zona_id:
        try:
            zona = Zona.objects.get(id=zona_id)
        except Zona.DoesNotExist:
            return JsonResponse({'error': 'Zona no encontrada'}, status=404)
        if zona.instalacion_id != instalacion.id:
            return JsonResponse({'error': 'La zona no pertenece a la instalación'}, status=400)
    try:
        cantidad_puestos = int(cantidad_puestos)
    except (TypeError, ValueError):
        cantidad_puestos = 1
    if cantidad_puestos < 1:
        cantidad_puestos = 1

    horarios_payload = []
    try:
        if horarios_text:
            parsed = parse_input(horarios_text)
            for r in parsed:
                horarios_payload.append({
                    'dia': r.get('dia'),
                    'horas': r.get('horas', 12),
                    'turno': r.get('turno') or 'Diurno'
                })
        elif isinstance(horarios, list):
            for h in horarios:
                dia = h.get('dia')
                horas = h.get('horas')
                if dia and horas is not None:
                    horarios_payload.append({
                        'dia': dia,
                        'horas': h.get('horas', 12),
                        'turno': h.get('turno') or 'Diurno',
                        'hora_ingreso': h.get('hora_ingreso') or None,
                        'hora_salida': h.get('hora_salida') or None,
                    })
    except Exception:
        horarios_payload = []

    puestos_creados = []
    # Se crea UN solo puesto con `cantidad_puestos = N` como CAPACIDAD (cupos).
    # Las asignaciones se crean luego hasta llenar esos N cupos.
    for _ in range(1):
        puesto = Puesto.objects.create(
            nombre=data.get('nombre'),
            tipo=tipo,
            cantidad_puestos=cantidad_puestos,
            instalacion_id=instalacion.id,
            zona=zona,
            horario_id=horario_id
        )

        for h in horarios_payload:
            if h.get('dia'):
                PuestoHorario.objects.create(
                    puesto=puesto,
                    dia=h['dia'],
                    horas=h.get('horas', 12),
                    turno=h.get('turno') or 'Diurno',
                    hora_ingreso=h.get('hora_ingreso') or None,
                    hora_salida=h.get('hora_salida') or None,
                )

        try:
            puesto.sync_from_horarios()
            puesto.save()
        except Exception:
            pass

        puestos_creados.append({
            'id': puesto.id,
            'nombre': puesto.nombre,
            'tipo': puesto.tipo,
            'cantidad_puestos': puesto.cantidad_puestos,
            'turno': puesto.get_turno(),
            'turno_display': puesto.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno,
                          'hora_ingreso': str(h.hora_ingreso) if h.hora_ingreso else None,
                          'hora_salida': str(h.hora_salida) if h.hora_salida else None}
                         for h in puesto.horarios.all()],
            'instalacion_id': puesto.instalacion_id,
            'zona_id': puesto.zona_id,
            'resumen': puesto.resumen,
        })

    return JsonResponse({
        'message': 'Puesto creado',
        'cantidad_creada': len(puestos_creados),
        'puesto': puestos_creados[0] if puestos_creados else None,
        'puestos': puestos_creados
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos(request):
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    puestos_qs = Puesto.objects.select_related('zona', 'horario').prefetch_related('horarios')
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo': p.tipo,
            'activo': p.activo,
            'cantidad_puestos': p.cantidad_puestos,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno,
                          'hora_ingreso': str(h.hora_ingreso) if h.hora_ingreso else None,
                          'hora_salida': str(h.hora_salida) if h.hora_salida else None}
                         for h in p.horarios.all()],
            'horario': p.horario_id,
            'horario_detalle': ({
                'id': p.horario.id,
                'hora_ingreso': str(p.horario.hora_ingreso),
                'hora_salida': str(p.horario.hora_salida),
            } if p.horario_id else None),
            'instalacion_id': p.instalacion_id,
            'zona_id': p.zona_id,
            'zona_titulo': getattr(p.zona, 'titulo', None),
            'resumen': p.resumen,
        })
    return JsonResponse(resultado, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_instalacion(request, instalacion_id):
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    puestos_qs = Puesto.objects.filter(instalacion_id=instalacion_id).select_related('zona', 'horario').prefetch_related('horarios')
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo': p.tipo,
            'activo': p.activo,
            'cantidad_puestos': p.cantidad_puestos,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno,
                          'hora_ingreso': str(h.hora_ingreso) if h.hora_ingreso else None,
                          'hora_salida': str(h.hora_salida) if h.hora_salida else None}
                         for h in p.horarios.all()],
            'horario': p.horario_id,
            'horario_detalle': ({
                'id': p.horario.id,
                'hora_ingreso': str(p.horario.hora_ingreso),
                'hora_salida': str(p.horario.hora_salida),
            } if p.horario_id else None),
            'instalacion_id': p.instalacion_id,
            'zona_id': p.zona_id,
            'zona_titulo': getattr(p.zona, 'titulo', None),
            'resumen': p.resumen,
        })
    return JsonResponse(resultado, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_cliente(request, cliente_id):
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403
        )

    puestos_qs = Puesto.objects.filter(instalacion__cliente_id=cliente_id).select_related('instalacion', 'zona', 'horario').prefetch_related('horarios')
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo': p.tipo,
            'activo': p.activo,
            'cantidad_puestos': p.cantidad_puestos,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno,
                          'hora_ingreso': str(h.hora_ingreso) if h.hora_ingreso else None,
                          'hora_salida': str(h.hora_salida) if h.hora_salida else None}
                         for h in p.horarios.all()],
            'horario': p.horario_id,
            'horario_detalle': ({
                'id': p.horario.id,
                'hora_ingreso': str(p.horario.hora_ingreso),
                'hora_salida': str(p.horario.hora_salida),
            } if p.horario_id else None),
            'instalacion_id': p.instalacion_id,
            'resumen': p.resumen,
            'instalacion__provincia': getattr(p.instalacion, 'provincia', None),
            'instalacion__ciudad': getattr(p.instalacion, 'ciudad', None),
            'instalacion_nombre': getattr(p.instalacion, 'nombre', None),
            'instalacion_codigo': getattr(p.instalacion, 'codigo', None),
            'instalacion_sector': getattr(p.instalacion, 'sector', None),
            'zona_id': p.zona_id,
            'zona_titulo': getattr(p.zona, 'titulo', None),
        })
    return JsonResponse(resultado, safe=False)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_puesto(request, id):
    if not request.user.has_perm('CoreFisica.change_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        data = json.loads(request.body)
        print('Payload recibido:', data)  
        puesto = Puesto.objects.get(id=id)

        instalacion_id = data.get('instalacion_id')
        zona_id = data.get('zona_id') or data.get('zona')
        if instalacion_id:
            if not Instalacion.objects.filter(id=instalacion_id).exists():
                return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
            puesto.instalacion_id = instalacion_id

        if zona_id:
            try:
                zona = Zona.objects.get(id=zona_id)
            except Zona.DoesNotExist:
                return JsonResponse({'error': 'Zona no encontrada'}, status=404)
            if instalacion_id and zona.instalacion_id != instalacion_id:
                return JsonResponse({'error': 'La zona no pertenece a la instalación'}, status=400)
            if not instalacion_id and zona.instalacion_id != puesto.instalacion_id:
                return JsonResponse({'error': 'La zona no pertenece a la instalación'}, status=400)
            puesto.zona = zona

        puesto.nombre = data.get('nombre', puesto.nombre)
        puesto.tipo = data.get('tipo', puesto.tipo)
        if 'horario' in data:
            horario_val = data.get('horario')
            puesto.horario_id = int(horario_val) if horario_val not in [None, '', 'null', 0] else None
        cantidad_puestos = data.get('cantidad_puestos', puesto.cantidad_puestos)
        try:
            cantidad_puestos = int(cantidad_puestos)
        except (TypeError, ValueError):
            cantidad_puestos = puesto.cantidad_puestos
        if cantidad_puestos < 1:
            cantidad_puestos = 1
        puesto.cantidad_puestos = cantidad_puestos
        # turno ya no se guarda a nivel de Puesto; se maneja por horario
        # actualizar horarios si vienen
        horarios = data.get('horarios')
        horarios_text = data.get('horarios_text')

        # aplicar cambios básicos
        puesto.save()
        horarios_payload = []
        try:
            if horarios_text:
                parsed = parse_input(horarios_text)
                puesto.horarios.all().delete()
                for r in parsed:
                    turno_val = r.get('turno') or 'Diurno'
                    PuestoHorario.objects.create(puesto=puesto, dia=r['dia'], horas=r['horas'], turno=turno_val)
                    horarios_payload.append({
                        'dia': r.get('dia'),
                        'horas': r.get('horas', 12),
                        'turno': turno_val
                    })
            elif isinstance(horarios, list):
                puesto.horarios.all().delete()
                for h in horarios:
                    dia = h.get('dia')
                    horas = h.get('horas')
                    if dia and horas is not None:
                        turno_val = h.get('turno') or 'Diurno'
                        hi = h.get('hora_ingreso') or None
                        ho = h.get('hora_salida') or None
                        PuestoHorario.objects.create(puesto=puesto, dia=dia, horas=horas, turno=turno_val,
                                                     hora_ingreso=hi, hora_salida=ho)
                        horarios_payload.append({
                            'dia': dia,
                            'horas': horas,
                            'turno': turno_val,
                            'hora_ingreso': hi,
                            'hora_salida': ho,
                        })
        except Exception:
            pass
        try:
            puesto.sync_from_horarios()
            puesto.save()
        except Exception:
            pass

        # Ya NO se crean puestos adicionales: la cantidad es la CAPACIDAD (cupos)
        # de este único registro y se respeta al crear asignaciones.
        return JsonResponse({
            'message': 'Puesto actualizado correctamente',
            'puesto': {
                'id': puesto.id,
                'nombre': puesto.nombre,
                'tipo': puesto.tipo,
                'cantidad_puestos': puesto.cantidad_puestos,
                'turno': puesto.get_turno(),
                'turno_display': puesto.get_turno_display(),
                'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno,
                          'hora_ingreso': str(h.hora_ingreso) if h.hora_ingreso else None,
                          'hora_salida': str(h.hora_salida) if h.hora_salida else None}
                         for h in puesto.horarios.all()],
                'instalacion_id': puesto.instalacion_id,
                'zona_id': puesto.zona_id,
            }
        }, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_puesto(request, id):
    if not request.user.has_perm('CoreFisica.delete_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    try:
        puesto = Puesto.objects.get(id=id)
        puesto.delete()
        return JsonResponse({'message': 'Puesto Eliminado Correctamente'}, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)