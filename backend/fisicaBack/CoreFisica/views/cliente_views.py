from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import Cliente
@csrf_exempt
def crear_cliente(request):
    #codigo de daniel
    # if request.method == 'POST':
    #     data = json.loads(request.body)
    #     cliente = Cliente.objects.create(
    #         razon_social=data.get('razon_social'),
    #         nombre_comercial=data.get('nombre_comercial'),
    #         direccion=data.get('direccion')
    #     )
    #     return JsonResponse({'message': 'Cliente creado', 'id': cliente.id})
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
def actualizar_cliente(request):
    #codigo daniel
    # if request.method == 'POST':
    #     try:
    #         data = json.loads(request.body)
    #         cliente_id = data.get('id')

    #         if not cliente_id:
    #             return JsonResponse({'error': 'ID de cliente no proporcionado'}, status=400)

    #         try:
    #             cliente = Cliente.objects.get(id=cliente_id)
    #         except Cliente.DoesNotExist:
    #             return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

    #         cliente.razon_social = data.get('razon_social', cliente.razon_social)
    #         cliente.nombre_comercial = data.get('nombre_comercial', cliente.nombre_comercial)
    #         cliente.direccion = data.get('direccion', cliente.direccion)

    #         cliente.save()

    #         return JsonResponse({'message': 'Cliente actualizado correctamente', 'id': cliente.id})
    #     except json.JSONDecodeError:
    #         return JsonResponse({'error': 'JSON inválido'}, status=400)

    # return JsonResponse({'error': 'Método no permitido'}, status=405)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cliente_id = data.get('id')

            if not cliente_id:
                return JsonResponse({'error': 'ID de cliente no proporcionado'}, status=400)

            try:
                cliente = Cliente.objects.get(pk=cliente_id)
            except Cliente.DoesNotExist:
                return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

            razon_social = data.get('razon_social', cliente.razon_social)
            nombre_comercial = data.get('nombre_comercial', cliente.nombre_comercial)
            direccion = data.get('direccion', cliente.direccion)

            if not razon_social or not nombre_comercial or not direccion:
                return JsonResponse({'error': 'Los campos no pueden estar vacíos'}, status=400)

            cliente.razon_social = razon_social
            cliente.nombre_comercial = nombre_comercial
            cliente.direccion = direccion

            cliente.save()

            return JsonResponse({'message': 'Cliente actualizado correctamente', 'id': cliente.id}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def obtener_clientes(request):
    if request.method == 'GET':
        clientes = Cliente.objects.all().values('id', 'razon_social', 'nombre_comercial', 'direccion')
        return JsonResponse(list(clientes), safe=False)


def obtener_Cliente(request,idCliente):


    clientes = Cliente.objects.raw("SELECT * FROM obtener_datosCliente(%s)",[idCliente])
    data = []

    for c in clientes:
        data.append({
            "idCliente": c.id,
            "razonSocial":c.razonsocial,
            "nombre_comercial":c.nombre_comercial,
            "direccion":c.direccion,
            
        })

    return JsonResponse(data, safe=False)