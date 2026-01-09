from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import  Horario

@csrf_exempt
def obtener_horarios(request):
    if request.method == 'GET':
        horarios = Horario.objects.all().values('id', 'hora_ingreso', 'hora_salida', 'denominativo')
        print(horarios)
        return JsonResponse(list(horarios), safe=False)

@csrf_exempt
def crear_horario(request):
    if request.method == 'POST':
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