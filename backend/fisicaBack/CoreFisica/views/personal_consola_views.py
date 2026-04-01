from django.http import JsonResponse
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import PersonalConsola

ALLOWED_TURNOS = {choice[0] for choice in PersonalConsola.TURNOS}
ALLOWED_ESTADOS = {choice[0] for choice in PersonalConsola.ESTADOS}

def _parse_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    val = str(value).strip().lower()
    if val in ['true', '1', 'yes', 'si']:
        return True
    if val in ['false', '0', 'no']:
        return False
    return default

def _serialize_item(item: PersonalConsola):
    return {
        'id': item.id,
        'fecha': item.fecha.isoformat() if item.fecha else None,
        'turno': item.turno,
        'cedula': item.cedula or '',
        'nombres': item.nombres,
        'apellidos': item.apellidos,
        'estado': item.estado,
        'is_active': item.is_active,
    }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_personal_consola(request):
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')

    qs = PersonalConsola.objects.all()
    if fecha:
        fecha_obj = parse_date(fecha)
        if fecha_obj:
            qs = qs.filter(fecha=fecha_obj)
    if turno:
        qs = qs.filter(turno=turno)

    data = [_serialize_item(item) for item in qs.order_by('apellidos', 'nombres')]
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_personal_consola(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    fecha = parse_date(data.get('fecha')) if data.get('fecha') else None
    turno = data.get('turno')
    nombres = (data.get('nombres') or '').strip()
    apellidos = (data.get('apellidos') or '').strip()
    estado = data.get('estado')
    cedula = (data.get('cedula') or '').strip() or None
    is_active = _parse_bool(data.get('is_active'), True)

    if not fecha or not turno or not nombres or not apellidos or not estado:
        return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

    if turno not in ALLOWED_TURNOS:
        return JsonResponse({'error': 'Turno invalido'}, status=400)

    if estado not in ALLOWED_ESTADOS:
        return JsonResponse({'error': 'Estado invalido'}, status=400)

    item = PersonalConsola.objects.create(
        fecha=fecha,
        turno=turno,
        nombres=nombres,
        apellidos=apellidos,
        estado=estado,
        cedula=cedula,
        is_active=bool(is_active)
    )

    return JsonResponse(_serialize_item(item), status=201)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_personal_consola(request, id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    item = PersonalConsola.objects.filter(id=id).first()
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

    if 'nombres' in data:
        item.nombres = (data.get('nombres') or '').strip()

    if 'apellidos' in data:
        item.apellidos = (data.get('apellidos') or '').strip()

    if 'estado' in data:
        estado = data.get('estado')
        if estado in ALLOWED_ESTADOS:
            item.estado = estado

    if 'cedula' in data:
        item.cedula = (data.get('cedula') or '').strip() or None

    if 'is_active' in data:
        item.is_active = _parse_bool(data.get('is_active'), item.is_active)

    item.save()
    return JsonResponse(_serialize_item(item))

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_personal_consola(request, id):
    item = PersonalConsola.objects.filter(id=id).first()
    if not item:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    item.delete()
    return JsonResponse({'message': 'Registro eliminado'}, status=200)