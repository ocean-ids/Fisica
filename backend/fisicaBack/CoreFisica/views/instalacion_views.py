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

@csrf_exempt
def actualizar_instalacion(request, id):
    if request.method == 'PUT':
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

            instalacion.nombre = data.get('nombre', instalacion.nombre)
            instalacion.codigo = data.get('codigo', instalacion.codigo)
            instalacion.cliente = cliente
            instalacion.ciudad = data.get('ciudad', instalacion.ciudad)
            instalacion.provincia = data.get('provincia', instalacion.provincia)
            instalacion.save()

            return JsonResponse({'message': 'Instalación actualizada', 'id': instalacion.id})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def eliminar_instalacion(request, id):
    if request.method == 'DELETE':
        try:
            instalacion = Instalacion.objects.get(id=id)
            instalacion.delete()
            return JsonResponse({'message':'Instalación eliminada correctamente'}, status=200)
        except Instalacion.DoesNotExist:
            return JsonResponse({'error':'Instalación no encontrada'}, status=404)
    return JsonResponse({'error':'Método no peromitido'}, status=405)
    