from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import Cliente

@csrf_exempt
def crear_cliente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razon_social = data.get('razon_social')
            nombre_comercial = data.get('nombre_comercial')
            direccion = data.get('direccion')

            if not razon_social or not nombre_comercial or not direccion:
                return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

            cliente = Cliente.objects.create(
                razon_social=razon_social,
                nombre_comercial=nombre_comercial,
                direccion=direccion
            )

            return JsonResponse({'message': 'Cliente creado correctamente', 'id': cliente.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)


@csrf_exempt
def obtener_clientes(request):
    if request.method == 'GET':
        clientes = Cliente.objects.all().values('id', 'razon_social', 'nombre_comercial', 'direccion')
        return JsonResponse(list(clientes), safe=False)


@csrf_exempt
def obtener_cliente_id(request, id):
    if request.method == 'GET':
        try:
            cliente = Cliente.objects.get(pk=id)
            data = {
                "id": cliente.id,
                "razon_social": cliente.razon_social,
                "nombre_comercial": cliente.nombre_comercial,
                "direccion": cliente.direccion
            }
            return JsonResponse(data)
        except Cliente.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)


@csrf_exempt
def actualizar_cliente(request, id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)

            try:
                cliente = Cliente.objects.get(pk=id)
            except Cliente.DoesNotExist:
                return JsonResponse(
                    {'error': 'Cliente no encontrado'},
                    status=404
                )

            cliente.razon_social = data.get(
                'razon_social', cliente.razon_social
            )
            cliente.nombre_comercial = data.get(
                'nombre_comercial', cliente.nombre_comercial
            )
            cliente.direccion = data.get(
                'direccion', cliente.direccion
            )

            cliente.save()

            return JsonResponse({
                'message': 'Cliente actualizado correctamente',
                'id': cliente.id
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def eliminar_cliente(request, id):
    if request.method == 'DELETE':
        try:
            cliente = Cliente.objects.get(pk=id)
            cliente.delete()
            return JsonResponse({'message': 'Cliente eliminado correctamente'}, status=200)
        except Cliente.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

            