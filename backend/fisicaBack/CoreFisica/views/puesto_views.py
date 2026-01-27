from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
import json
from ..models import Instalacion, Puesto


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    cantidad_guardias = data.get('cantidad_guardias', 1)
    instalacion = Instalacion.objects.get(id=instalacion_id)
    puesto = Puesto.objects.create(
        nombre=data.get('nombre'),
        cantidad_guardias=cantidad_guardias,
        instalacion_id=instalacion.id
    )
    return JsonResponse({'message': 'Puesto creado', 'id': puesto.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos(request):
    puestos = Puesto.objects.all().values('id', 'nombre','cantidad_guardias', 'instalacion_id')
    return JsonResponse(list(puestos), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_instalacion(request, instalacion_id):
    puestos = Puesto.objects.filter(instalacion_id=instalacion_id).values('id', 'nombre', 'cantidad_guardias', 'horas_trabajo', 'instalacion_id')
    return JsonResponse(list(puestos), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_cliente(request, cliente_id):
    puestos = Puesto.objects.filter(instalacion__cliente_id=cliente_id).values(
        'id', 'nombre', 'cantidad_guardias', 'horas_trabajo', 'instalacion_id', 
        'instalacion__provincia', 'instalacion__ciudad'
    )
    return JsonResponse(list(puestos), safe=False)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_puesto(request, id):
    try:
        data = json.loads(request.body)
        puesto = Puesto.objects.get(id=id)

        puesto.nombre = data.get('nombre', puesto.nombre)
        puesto.cantidad_guardias = data.get('cantidad_guardias', puesto.cantidad_guardias)
        puesto.horas_trabajo = data.get('horas_trabajo', puesto.horas_trabajo)
        puesto.instalacion_id = data.get('instalacion_id', puesto.instalacion_id)

        puesto.save()
        return JsonResponse({'message': 'Puesto actualizado correctamente'}, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontardo'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_puesto(request, id):
        try:
            puesto = Puesto.objects.get(id=id)
            puesto.delete()
            return JsonResponse({'message': 'Puesto Eliminado Correctamente'}, status=200)
        except Puesto.DoesNotExist:
            return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)