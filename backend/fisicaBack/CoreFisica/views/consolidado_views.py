from django.http import JsonResponse
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Consolidado, PersonalConsola

ALLOWED_TURNOS = {choice[0] for choice in PersonalConsola.TURNOS}
ALLOWED_TIPOS = {choice[0] for choice in Consolidado.TIPOS}


def _serialize_item(item: Consolidado):
    return {
        'id': item.id,
        'fecha': item.fecha.isoformat() if item.fecha else None,
        'turno': item.turno,
        'tipo': item.tipo,
        'referencia_id': item.referencia_id,
        'observacion': item.observacion or ''
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_consolidado(request):
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    tipo = request.GET.get('tipo')
    referencia_id = request.GET.get('referencia_id')

    qs = Consolidado.objects.all()
    if fecha:
        fecha_obj = parse_date(fecha)
        if fecha_obj:
            qs = qs.filter(fecha=fecha_obj)
    if turno:
        qs = qs.filter(turno=turno)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if referencia_id:
        try:
            ref_id = int(referencia_id)
            qs = qs.filter(referencia_id=ref_id)
        except (TypeError, ValueError):
            pass

    data = [_serialize_item(item) for item in qs.order_by('fecha', 'turno', 'tipo', 'referencia_id')]
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_consolidado(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    fecha = parse_date(data.get('fecha')) if data.get('fecha') else None
    turno = data.get('turno')
    tipo = data.get('tipo')
    referencia_id = data.get('referencia_id')
    observacion = (data.get('observacion') or '').strip() or None

    if not fecha or not turno or not tipo or referencia_id in [None, '']:
        return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

    if turno not in ALLOWED_TURNOS:
        return JsonResponse({'error': 'Turno invalido'}, status=400)

    if tipo not in ALLOWED_TIPOS:
        return JsonResponse({'error': 'Tipo invalido'}, status=400)

    try:
        referencia_id = int(referencia_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'referencia_id invalido'}, status=400)

    item = Consolidado.objects.create(
        fecha=fecha,
        turno=turno,
        tipo=tipo,
        referencia_id=referencia_id,
        observacion=observacion
    )

    return JsonResponse(_serialize_item(item), status=201)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_consolidado(request, id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    item = Consolidado.objects.filter(id=id).first()
    if not item:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    if 'fecha' in data:
        fecha = parse_date(data.get('fecha')) if data.get('fecha') else None
        if fecha:
            item.fecha = fecha

    if 'turno' in data:
        turno = data.get('turno')
        if turno in ALLOWED_TURNOS:
            item.turno = turno

    if 'tipo' in data:
        tipo = data.get('tipo')
        if tipo in ALLOWED_TIPOS:
            item.tipo = tipo

    if 'referencia_id' in data:
        try:
            item.referencia_id = int(data.get('referencia_id'))
        except (TypeError, ValueError):
            pass

    if 'observacion' in data:
        item.observacion = (data.get('observacion') or '').strip() or None

    item.save()
    return JsonResponse(_serialize_item(item))


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_consolidado(request, id):
    item = Consolidado.objects.filter(id=id).first()
    if not item:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    item.delete()
    return JsonResponse({'message': 'Registro eliminado'}, status=200)
