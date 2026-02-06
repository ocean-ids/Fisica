from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Cliente


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_clientes(request):
    qs = Cliente.objects.all().values('id', 'razon_social', 'nombre_comercial', 'ruc')
    try:
        count = qs.count()
    except Exception:
        count = len(list(qs))
    print(f"[DEBUG] obtener_clientes: returning {count} clientes")
    # print first item for quick inspection
    first = qs.first()
    if first:
        print(f"[DEBUG] first cliente sample: {first}")
    return JsonResponse(list(qs), safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_cliente_id(request, id):
    try:
        cliente = Cliente.objects.get(pk=id)
        data = {
            "id": cliente.id,
            "ruc": cliente.ruc,
            "razon_social": cliente.razon_social,
            "nombre_comercial": cliente.nombre_comercial
        }
        return JsonResponse(data)
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_cliente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razon_social = data.get('razon_social')
            nombre_comercial = data.get('nombre_comercial')
            ruc = data.get('ruc')
            if not razon_social or not nombre_comercial:
                return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

            cliente = Cliente.objects.create(
                razon_social=razon_social,
                nombre_comercial=nombre_comercial,
                ruc=ruc
            )

            return JsonResponse({'message': 'Cliente creado correctamente', 'id': cliente.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_cliente(request, id):
    try:
        data = json.loads(request.body)

        try:
            cliente = Cliente.objects.get(pk=id)
        except Cliente.DoesNotExist:
            return JsonResponse(
                {'error': 'Cliente no encontrado'},
                status=404
            )

        cliente.razon_social = data.get('razon_social', cliente.razon_social)
        cliente.nombre_comercial = data.get('nombre_comercial', cliente.nombre_comercial)
        cliente.ruc = data.get('ruc', cliente.ruc)

        cliente.save()

        return JsonResponse({
            'message': 'Cliente actualizado correctamente',
            'id': cliente.id,
            "ruc": cliente.ruc
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_cliente(request, id):
    try:
        cliente = Cliente.objects.get(pk=id)
        cliente.delete()
        return JsonResponse({'message': 'Cliente eliminado correctamente'}, status=200)
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

            