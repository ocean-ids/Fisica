from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import  Horario

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_horarios(request):
    horarios = Horario.objects.all().values('id', 'hora_ingreso', 'hora_salida', 'denominativo')
    print(horarios)
    return JsonResponse(list(horarios), safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_horario(request):
    data = json.loads(request.body)
    print("daniel:", data)
    #puesto_id = data.get('puesto_id')
    #puesto = Puesto.objects.get(id=puesto_id)
    horario = Horario.objects.create(
        #puesto=puesto,
        hora_ingreso=data.get('hora_ingreso'),
        hora_salida=data.get('hora_salida'),
        denominativo=data.get('denominativo')
    )
    return JsonResponse({'message': 'Horario creado', 'id': horario.id})