from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Horario

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_horarios(request):
    horarios = Horario.objects.all().values('id', 'hora_ingreso', 'hora_salida', 'denominativo')
    return  JsonResponse(list(horarios), safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_horarios(request):
    try:
        data = json.loads(request.body)

        if not all(k in data for k in ('hora_ingreso', 'hora_salida', 'denominativo')):
            return JsonResponse({'error': 'Faltan campos requeridos'})

        horario = Horario.objects.create(
            hora_ingreso=data.get('hora_ingreso'),
            hora_salida=data.get('hora_salida'),
            denominativo=data.get('denominativo')
        )

        return JsonResponse({
            'message':'Horario creado exitosamente',
            'id': horario.id,
            'horario':{
                'id': horario.id,
                'hora_ingreso': str(horario.hora_ingreso),
                'hora_salida': str(horario.hora_salida),
                'denominativo': horario.denominativo

            }
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_horario(request, id):
    try:
        horario = Horario.objects.get(id=id)
        data = json.loads(request.body)

        horario.hora_ingreso = data.get('hora_ingreso', horario.hora_ingreso)
        horario.hora_salida = data.get('hora_salida', horario.hora_salida)
        horario.denominativo = data.get('denominativo', horario.denominativo)
        horario.save()

        return JsonResponse({
            'message': 'Horario actualizado exitosamente',
            'hoario': {
                'id': horario.id,
                'hora_ingreso': str(horario.hora_ingreso),
                'hora_salida': str(horario.hora_salida),
                'denominativo': horario.denominativo
            }
        }, status=200)
    except Horario.DoesNotExist:
        return JsonResponse({'error': 'Horario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_horario(request, id):
    try:
        horario = Horario.objects.get(id=id)
        horario.delete()
        return JsonResponse({'message': 'Horario eliminado exitosamente'}, status=200)
    except Horario.DoesNotExist:
        return JsonResponse({'error': 'Horario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




