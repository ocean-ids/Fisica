"""Vistas de Clientes: CRUD y búsqueda (insensible a acentos) de clientes."""
from django.http import JsonResponse
from django.db.models import Q
from django.db import IntegrityError
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Cliente
from ..utils import _strip_accents


ALLOWED_SIZES = {choice[0] for choice in Cliente.SIZE_CHOICES}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_clientes(request):
    if not request.user.has_perm('CoreFisica.view_cliente'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    q = request.GET.get('q', '').strip()
    size = request.GET.get('size', '').strip()

    qs = Cliente.objects.all()

    if q:
        qn = _strip_accents(q)
        qs = qs.filter(
            Q(ruc__icontains=q) |
            Q(razon_social__unaccent__icontains=qn) |
            Q(nombre_comercial__unaccent__icontains=qn)
        )

    if size:
        qs = qs.filter(size=size)

    qs = qs.values(
        'id',
        'razon_social',
        'nombre_comercial',
        'ruc',
        'size',
        'fecha_ingreso',
        'fecha_retiro'
    ).order_by('nombre_comercial')
    try:
        count = qs.count()
    except Exception:
        count = len(list(qs))
    print(f"[DEBUG] obtener_clientes: returning {count} clientes")
    
    first = qs.first()
    if first:
        print(f"[DEBUG] first cliente sample: {first}")
    return JsonResponse(list(qs), safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_cliente_id(request, id):
    if not request.user.has_perm('CoreFisica.view_cliente'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        cliente = Cliente.objects.get(pk=id)
        data = {
            "id": cliente.id,
            "ruc": cliente.ruc,
            "razon_social": cliente.razon_social,
            "nombre_comercial": cliente.nombre_comercial,
            "size": cliente.size,
            "fecha_ingreso": cliente.fecha_ingreso.isoformat() if cliente.fecha_ingreso else None,
            "fecha_retiro": cliente.fecha_retiro.isoformat() if cliente.fecha_retiro else None,
        }
        return JsonResponse(data)
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_cliente(request):
    if not request.user.has_perm('CoreFisica.add_cliente'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razon_social = data.get('razon_social')
            nombre_comercial = data.get('nombre_comercial')
            ruc = data.get('ruc')
            if razon_social:
                razon_social = str(razon_social).strip().upper()
            if nombre_comercial:
                nombre_comercial = str(nombre_comercial).strip().upper()
            # RUC vacío -> NULL (la columna es unique; '' chocaría con otros sin RUC)
            ruc = str(ruc).strip() if ruc is not None else ''
            ruc = ruc or None
            size = data.get('size', 'MEDIANO')
            fecha_ingreso = parse_date(data.get('fecha_ingreso')) if data.get('fecha_ingreso') else None
            fecha_retiro = parse_date(data.get('fecha_retiro')) if data.get('fecha_retiro') else None

            if not razon_social or not nombre_comercial:
                return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

            if size not in ALLOWED_SIZES:
                return JsonResponse({'error': 'Tamaño no válido. Use PEQUENO, MEDIANO o GRANDE.'}, status=400)

            try:
                cliente = Cliente.objects.create(
                    razon_social=razon_social,
                    nombre_comercial=nombre_comercial,
                    ruc=ruc,
                    size=size,
                    fecha_ingreso=fecha_ingreso,
                    fecha_retiro=fecha_retiro
                )
            except IntegrityError:
                return JsonResponse({'error': f'Ya existe un cliente con el RUC {ruc}'}, status=400)

            return JsonResponse({'message': 'Cliente creado correctamente', 'id': cliente.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_cliente(request, id):
    if not request.user.has_perm('CoreFisica.change_cliente'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        data = json.loads(request.body)

        try:
            cliente = Cliente.objects.get(pk=id)
        except Cliente.DoesNotExist:
            return JsonResponse(
                {'error': 'Cliente no encontrado'},
                status=404
            )

        if 'razon_social' in data:
            razon_social = data.get('razon_social')
            cliente.razon_social = str(razon_social).strip().upper() if razon_social else ''
        if 'nombre_comercial' in data:
            nombre_comercial = data.get('nombre_comercial')
            cliente.nombre_comercial = str(nombre_comercial).strip().upper() if nombre_comercial else ''
        if 'ruc' in data:
            ruc = data.get('ruc')
            ruc = str(ruc).strip() if ruc is not None else ''
            cliente.ruc = ruc or None  # RUC vacío -> NULL (columna unique)
        size = data.get('size', cliente.size)

        if size not in ALLOWED_SIZES:
            return JsonResponse({'error': 'Tamaño no válido. Use PEQUENO, MEDIANO o GRANDE.'}, status=400)

        if 'fecha_ingreso' in data:
            cliente.fecha_ingreso = parse_date(data.get('fecha_ingreso')) if data.get('fecha_ingreso') else None

        if 'fecha_retiro' in data:
            cliente.fecha_retiro = parse_date(data.get('fecha_retiro')) if data.get('fecha_retiro') else None

        cliente.size = size

        try:
            cliente.save()
        except IntegrityError:
            return JsonResponse({'error': f'Ya existe un cliente con el RUC {cliente.ruc}'}, status=400)

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
    if not request.user.has_perm('CoreFisica.delete_cliente'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        cliente = Cliente.objects.get(pk=id)
        cliente.delete()
        return JsonResponse({'message': 'Cliente eliminado correctamente'}, status=200)
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

            