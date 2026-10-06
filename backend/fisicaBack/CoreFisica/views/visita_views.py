"""Visitas (rondas) del supervisor a un puesto, con GPS.

- La app móvil envía cada visita con un `uuid_cliente` propio: si el celular la reenvía (sin conexión, reintentos)
  NO se duplica: el servidor responde con la ya guardada.
- El servidor revalida el GPS: precisión del celular y distancia al puesto.
- La ubicación del puesto se fija en una primera visita y Consola la confirma; hasta entonces las visitas
  quedan como "SIN_UBICACION_PUESTO" (se guardan igual).
"""
import datetime
import math
import uuid as uuid_lib
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Instalacion, Puesto, VisitaSupervisor

# Error máximo del GPS (en metros) que se acepta como "buena" precisión.
PRECISION_MAX_M = 50


def distancia_m(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos puntos (fórmula de haversine)."""
    r = 6371000.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = p2 - p1
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def evaluar_gps(instalacion, lat, lon, precision):
    """(estado_gps, distancia_m) de una visita. Orden: sin GPS -> precisión baja -> ubicación del puesto -> rango."""
    if lat is None or lon is None:
        return 'SIN_GPS', None
    dist = None
    if instalacion.ubicacion_confirmada and instalacion.latitud is not None and instalacion.longitud is not None:
        dist = distancia_m(instalacion.latitud, instalacion.longitud, lat, lon)
    if precision is not None and precision > PRECISION_MAX_M:
        return 'PRECISION_BAJA', dist
    if dist is None:
        return 'SIN_UBICACION_PUESTO', None
    return ('OK' if dist <= (instalacion.radio_m or 150) else 'FUERA_DE_RANGO'), dist


def _serialize(v):
    return {
        'id': v.id,
        'uuid_cliente': str(v.uuid_cliente),
        'usuario': (v.usuario.get_full_name() or v.usuario.get_username()) if v.usuario else '',
        'instalacion_id': v.instalacion_id,
        'instalacion': v.instalacion.nombre or '',
        'codigo': v.instalacion.codigo or '',
        'puesto_id': v.puesto_id,
        'fecha_hora': v.fecha_hora.isoformat() if v.fecha_hora else None,
        'recibido_en': v.recibido_en.isoformat() if v.recibido_en else None,
        'latitud': float(v.latitud) if v.latitud is not None else None,
        'longitud': float(v.longitud) if v.longitud is not None else None,
        'precision_m': v.precision_m,
        'distancia_m': round(v.distancia_m, 1) if v.distancia_m is not None else None,
        'estado_gps': v.estado_gps,
        'estado_gps_texto': v.get_estado_gps_display(),
        'nota': v.nota,
    }


def _dec(v):
    if v in (None, ''):
        return None
    try:
        return Decimal(str(v)).quantize(Decimal('0.000001'))
    except (InvalidOperation, ValueError):
        raise ValueError('coordenada inválida')


def _num(v):
    if v in (None, ''):
        return None
    return float(v)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def visitas(request):
    if request.method == 'GET':
        return _listar(request)
    return _crear(request)


def _listar(request):
    if not request.user.has_perm('CoreFisica.view_visitasupervisor'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    qs = VisitaSupervisor.objects.select_related('usuario', 'instalacion')
    fecha = request.GET.get('fecha')
    if fecha:
        try:
            d = datetime.date.fromisoformat(fecha)
        except ValueError:
            return Response({'error': 'fecha inválida (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        qs = qs.filter(fecha_hora__date=d)
    estado = (request.GET.get('estado_gps') or '').strip().upper()
    if estado:
        qs = qs.filter(estado_gps=estado)
    return Response([_serialize(v) for v in qs[:500]])


def _crear(request):
    if not request.user.has_perm('CoreFisica.add_visitasupervisor'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    data = request.data

    try:
        uid = uuid_lib.UUID(str(data.get('uuid_cliente')))
    except (ValueError, AttributeError, TypeError):
        return Response({'error': 'uuid_cliente es obligatorio (un identificador único por visita)'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Reenvío: la visita ya llegó antes -> se devuelve la guardada, no se duplica.
    previa = VisitaSupervisor.objects.select_related('usuario', 'instalacion').filter(uuid_cliente=uid).first()
    if previa:
        return Response({**_serialize(previa), 'duplicada': True}, status=status.HTTP_200_OK)

    inst = Instalacion.objects.filter(id=data.get('instalacion_id')).first() if str(data.get('instalacion_id') or '').isdigit() else None
    if not inst:
        return Response({'error': 'La instalación no existe'}, status=status.HTTP_400_BAD_REQUEST)
    puesto = None
    if str(data.get('puesto_id') or '').isdigit():
        puesto = Puesto.objects.filter(id=data.get('puesto_id'), instalacion=inst).first()
        if not puesto:
            return Response({'error': 'El puesto no pertenece a la instalación'}, status=status.HTTP_400_BAD_REQUEST)

    fecha_hora = parse_datetime(str(data.get('fecha_hora') or '')) or timezone.now()
    if timezone.is_naive(fecha_hora):
        fecha_hora = timezone.make_aware(fecha_hora)
    try:
        lat, lon = _dec(data.get('latitud')), _dec(data.get('longitud'))
        precision = _num(data.get('precision_m'))
    except ValueError:
        return Response({'error': 'Ubicación inválida'}, status=status.HTTP_400_BAD_REQUEST)
    if (lat is None) != (lon is None) or (lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180)):
        return Response({'error': 'Latitud y longitud deben venir juntas y ser válidas'}, status=status.HTTP_400_BAD_REQUEST)

    estado, dist = evaluar_gps(inst, lat, lon, precision)
    try:
        with transaction.atomic():
            v = VisitaSupervisor.objects.create(
                uuid_cliente=uid, usuario=request.user, instalacion=inst, puesto=puesto, fecha_hora=fecha_hora,
                latitud=lat, longitud=lon, precision_m=precision, distancia_m=dist, estado_gps=estado,
                nota=str(data.get('nota') or '').strip()[:2000],
            )
    except IntegrityError:           # dos envíos simultáneos con el mismo uuid
        previa = VisitaSupervisor.objects.select_related('usuario', 'instalacion').get(uuid_cliente=uid)
        return Response({**_serialize(previa), 'duplicada': True}, status=status.HTTP_200_OK)
    v = VisitaSupervisor.objects.select_related('usuario', 'instalacion').get(id=v.id)
    return Response({**_serialize(v), 'duplicada': False}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirmar_ubicacion_visita(request, id):
    """Consola toma la ubicación de esta visita como la del puesto (instalación) y la deja confirmada."""
    if not request.user.has_perm('CoreFisica.change_instalacion'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    v = VisitaSupervisor.objects.select_related('instalacion').filter(id=id).first()
    if not v:
        return Response({'error': 'Visita no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    if v.latitud is None or v.longitud is None:
        return Response({'error': 'Esta visita no tiene GPS'}, status=status.HTTP_400_BAD_REQUEST)
    inst = v.instalacion
    inst.latitud, inst.longitud, inst.ubicacion_confirmada = v.latitud, v.longitud, True
    inst.save(update_fields=['latitud', 'longitud', 'ubicacion_confirmada'])
    return Response({'ok': True, 'instalacion_id': inst.id, 'latitud': float(inst.latitud), 'longitud': float(inst.longitud)})
