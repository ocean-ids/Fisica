from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Instalacion
from django.db.models import Q
from ..serializers import InstalacionSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_instalaciones(request):
    q = (request.GET.get('q') or '').strip()
    cliente_id = request.GET.get('cliente_id')

    qs = Instalacion.objects.select_related('cliente').all()

    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(codigo__icontains=q) |
            Q(provincia__icontains=q) |
            Q(ciudad__icontains=q) |
            Q(direccion__icontains=q)
        )

    instalaciones = qs.values('id', 'nombre', 'provincia', 'ciudad', 'cliente_id', 'codigo', 'direccion')
    return JsonResponse(list(instalaciones), safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_instalacion(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # soportar `cliente_id` desde frontend
    if 'cliente_id' in data and 'cliente' not in data:
        data['cliente'] = data.pop('cliente_id')

    serializer = InstalacionSerializer(data=data)
    if serializer.is_valid():
        instalacion = serializer.save()
        return JsonResponse({'message': 'Instalación creada', 'id': instalacion.id})
    else:
        return JsonResponse({'error': 'Datos inválidos', 'details': serializer.errors}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_instalacion(request, id):
    try:
        data = json.loads(request.body)

        try:
            instalacion = Instalacion.objects.get(id=id)
        except Instalacion.DoesNotExist:
            return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

        # soportar `cliente_id` desde frontend
        if 'cliente_id' in data and 'cliente' not in data:
            data['cliente'] = data.pop('cliente_id')

        serializer = InstalacionSerializer(instalacion, data=data, partial=True)
        if serializer.is_valid():
            instalacion = serializer.save()
            return JsonResponse({'message': 'Instalación actualizada', 'id': instalacion.id})
        else:
            return JsonResponse({'error': 'Datos inválidos', 'details': serializer.errors}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_instalacion(request, id):
    try:
        instalacion = Instalacion.objects.get(id=id)
        instalacion.delete()
        return JsonResponse({'message':'Instalación eliminada correctamente'}, status=200)
    except Instalacion.DoesNotExist:
        return JsonResponse({'error':'Instalación no encontrada'}, status=404)
    