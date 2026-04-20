from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Horario

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_horarios(request):
    #si el usuario no tiene permiso para ver horarios, devolver error 403
    if not request.user.has_perm('CoreFisica.view_horario'):
            return JsonResponse({'error': 'No autorizado'}, status=403)
    # data es una lista de diccionarios con los horarios
    data = []
    # iterar sobre todos los horarios y agregar un diccionario con su id, hora_ingreso y hora_salida a la lista data
    for h in Horario.objects.all():
        data.append({
            'id': h.id,
            'hora_ingreso': h.hora_ingreso,
            'hora_salida': h.hora_salida,
        })
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_horario(request):
    #si el usuario no tiene permiso para crear horarios, devolver error 403
    if not request.user.has_perm('CoreFisica.add_horario'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        # data es un diccionario con los campos hora_ingreso y hora_salida para crear un nuevo horario
        data = json.loads(request.body)
        print(f"📥 Datos recibidos para crear horario: {data}")

        #si no se reciben los campos hora_ingreso y hora_salida, devolver error 400
        if not all(k in data for k in ('hora_ingreso', 'hora_salida')):
            return JsonResponse({'error': 'Faltan campos requeridos (hora_ingreso, hora_salida)'}, status=400)

        #crear un nuevo horario con los datos recibidos y guardarlo en la base de datos
        horario = Horario.objects.create(
            hora_ingreso=data.get('hora_ingreso'),
            hora_salida=data.get('hora_salida'),
        )
        #returna un json con un mensaje de éxito, el id del nuevo horario y los datos del horario creado, con status 201
        return JsonResponse({
            'message':'Horario creado exitosamente',
            'id': horario.id,
            'horario':{
                'id': horario.id,
                'hora_ingreso': str(horario.hora_ingreso),
                'hora_salida': str(horario.hora_salida),
            }
        }, status=201)
    except Exception as e:
        print(f"❌ Error al crear horario: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_horario(request, id):
    # si el usuario no tiene permiso para actualizar horarios, devolver error 403
    if not request.user.has_perm('CoreFisica.change_horario'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        #obtener el horario con el id 
        horario = Horario.objects.get(id=id)
        #data es un diccionario con los campos hora_ingreso y hora_salida para actualizar el horario
        data = json.loads(request.body)
        
        horario.hora_ingreso = data.get('hora_ingreso', horario.hora_ingreso)
        horario.hora_salida = data.get('hora_salida', horario.hora_salida)
        #guardar los cambios en la base de datos
        horario.save()
        # retornaun json con un mensaje de éxito, el id del horario actualizado y los datos del horario actualizado, con status 200
        return JsonResponse({
            'message': 'Horario actualizado exitosamente',
            'horario': {
                'id': horario.id,
                'hora_ingreso': str(horario.hora_ingreso),
                'hora_salida': str(horario.hora_salida),
            }
        }, status=200)
    except Horario.DoesNotExist:
        return JsonResponse({'error': 'Horario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_horario(request, id):
    # si el usuario no tiene permiso para eliminar horarios, devolver error 403
    if not request.user.has_perm('CoreFisica.delete_horario'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        #obtener el horario con el id y eliminarlo de la base de datos
        horario = Horario.objects.get(id=id)
        #eliminar el horario de la base de datos
        horario.delete()
        #retorna un json con un mensaje de éxito y status 200
        return JsonResponse({'message': 'Horario eliminado exitosamente'}, status=200)
    except Horario.DoesNotExist:
        return JsonResponse({'error': 'Horario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




