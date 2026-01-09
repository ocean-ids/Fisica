from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import Cliente, Instalacion

@csrf_exempt
def obtener_instalaciones(request):
    if request.method == 'GET':
        instalaciones = Instalacion.objects.all().values('id', 'nombre', 'provincia', 'ciudad', 'cliente_id')
        return JsonResponse(list(instalaciones), safe=False)


@csrf_exempt
def crear_instalacion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(data)
        cliente_id = data.get('cliente_id')
        cliente = Cliente.objects.get(id=cliente_id)

        instalacion = Instalacion.objects.create(
            nombre=data.get('nombre_instalacion'),
            codigo=data.get('codigo'),
            cliente=cliente,
            ciudad=data.get('ciudad'),
            provincia=data.get('provincia'),
        )

        return JsonResponse({'message': 'Instalación creada', 'id': instalacion.id})