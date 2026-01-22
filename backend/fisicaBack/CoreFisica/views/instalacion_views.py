from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Cliente, Instalacion

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_instalaciones(request):
    instalaciones = Instalacion.objects.all().values('id', 'provincia', 'ciudad', 'cliente_id')
    return JsonResponse(list(instalaciones), safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_instalacion(request):
    data = json.loads(request.body)
    print(data)
    cliente_id = data.get('cliente_id')
    cliente = Cliente.objects.get(id=cliente_id)

    instalacion = Instalacion.objects.create(
        cliente=cliente,
        ciudad=data.get('ciudad'),
        provincia=data.get('provincia'),
    )

    return JsonResponse({'message': 'Instalación creada', 'id': instalacion.id})

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_instalacion(request, id):
    try:
        data = json.loads(request.body)

        try:
            instalacion = Instalacion.objects.get(id=id)
        except Instalacion.DoesNotExist:
            return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

        try:
            cliente = Cliente.objects.get(id=data.get('cliente'))
        except Cliente.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

        instalacion.cliente = cliente
        instalacion.ciudad = data.get('ciudad', instalacion.ciudad)
        instalacion.provincia = data.get('provincia', instalacion.provincia)
        instalacion.save()

        return JsonResponse({'message': 'Instalación actualizada', 'id': instalacion.id})

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
    