from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
import json
from ..models import Instalacion, Puesto
from django.db.models import F
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    cantidad_guardias = data.get('cantidad_guardias', 1)
    horas_trabajo = data.get('horas_trabajo')
    turno = data.get('turno', 'dia')  
    dias = data.get('dias', [])

    instalacion = Instalacion.objects.get(id=instalacion_id)
    puesto = Puesto.objects.create(
        nombre=data.get('nombre'),
        cantidad_guardias=cantidad_guardias,
        horas_trabajo=horas_trabajo,
        turno=turno,  
        dias=dias,
        instalacion_id=instalacion.id
    )
    return JsonResponse({'message': 'Puesto creado', 'id': puesto.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos(request):
    puestos = Puesto.objects.all().values(
        'id', 'nombre', 'cantidad_guardias', 'horas_trabajo',
        'turno', 'dias', 'instalacion_id', 'resumen'  
    )
    return JsonResponse(list(puestos), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_instalacion(request, instalacion_id):
    puestos = Puesto.objects.filter(instalacion_id=instalacion_id).values(
        'id', 'nombre', 'cantidad_guardias', 'horas_trabajo',
        'turno', 'dias', 'instalacion_id', 'resumen'  
    )
    return JsonResponse(list(puestos), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_cliente(request, cliente_id):
    puestos = Puesto.objects.filter(instalacion__cliente_id=cliente_id)
    # Añadir el nombre de la instalación como `instalacion_nombre` para el frontend
    puestos = puestos.annotate(instalacion_nombre=F('instalacion__nombre')).values(
        'id', 'nombre', 'cantidad_guardias', 'horas_trabajo',
        'turno', 'dias', 'instalacion_id', 'resumen',
        'instalacion__provincia', 'instalacion__ciudad', 'instalacion_nombre'
    )
    return JsonResponse(list(puestos), safe=False)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_puesto(request, id):
    try:
        data = json.loads(request.body)
        print('Payload recibido:', data)  
        puesto = Puesto.objects.get(id=id)

        instalacion_id = data.get('instalacion_id')
        if instalacion_id:
            if not Instalacion.objects.filter(id=instalacion_id).exists():
                return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
            puesto.instalacion_id = instalacion_id

        puesto.nombre = data.get('nombre', puesto.nombre)
        puesto.cantidad_guardias = data.get('cantidad_guardias', puesto.cantidad_guardias)
        puesto.horas_trabajo = data.get('horas_trabajo', puesto.horas_trabajo)
        turno = data.get('turno')
        if turno not in ['dia', 'noche']:
            return JsonResponse({'error': 'Valor de turno inválido'}, status=400)
        puesto.turno = turno
        puesto.dias = data.get('dias', puesto.dias)

        puesto.save()
        return JsonResponse({
            'message': 'Puesto actualizado correctamente',
            'puesto': {
                'id': puesto.id,
                'nombre': puesto.nombre,
                'cantidad_guardias': puesto.cantidad_guardias,
                'horas_trabajo': puesto.horas_trabajo,
                'turno': puesto.turno,
                'dias': puesto.dias,
                'instalacion_id': puesto.instalacion_id,
            }
        }, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
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