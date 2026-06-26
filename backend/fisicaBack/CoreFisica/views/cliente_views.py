"""Vistas de Clientes: CRUD y búsqueda (insensible a acentos) de clientes."""
from django.http import JsonResponse
from django.db.models import Q
from django.db import IntegrityError
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
import datetime
from decimal import Decimal, InvalidOperation
from ..models import Cliente, Provincia, Canton
from ..utils import _strip_accents


ALLOWED_SIZES = {choice[0] for choice in Cliente.SIZE_CHOICES}


# ===== Campos del ERP (Mantenimiento de Clientes) =====
_CLI_CHAR = [
    'codigo_erp', 'estado', 'tipo_id', 'tipo_cliente', 'sexo', 'estado_civil',
    'parroquia', 'ciudad', 'direccion_comercial', 'sector',
    'telefono', 'telefono2', 'fax', 'email', 'email_adicional',
    'copia_correo_1', 'copia_correo_2', 'copia_correo_3', 'copia_correo_4', 'copia_correo_5',
    'vendedor', 'rep_legal', 'cod_agrupacion', 'valoracion_custodias', 'tipo_precio',
    'forma_pago', 'origen_ingreso', 'zona', 'cuenta_contable', 'cod_area', 'cod_rol',
    'observaciones',
]
_CLI_DEC = ['desc_vta', 'cupo', 'valor_puesto']
_CLI_INT = ['plazo_max']
_CLI_BOOL = ['control_cupo', 'requiere_correo', 'controla_factura_reverso', 'paga_iva']
_CLI_DATE = ['ultima_venta']


def _cli_dec(v):
    try:
        return Decimal(str(v if v not in (None, '') else 0))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _cli_date(v):
    if not v:
        return None
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _aplicar_campos_cliente(cliente, data):
    """Aplica los campos del ERP al cliente (solo los que vengan en el payload)."""
    for f in _CLI_CHAR:
        if f in data:
            setattr(cliente, f, str(data.get(f) or '').strip())
    for f in _CLI_DEC:
        if f in data:
            setattr(cliente, f, _cli_dec(data.get(f)))
    for f in _CLI_INT:
        if f in data:
            try:
                setattr(cliente, f, int(data.get(f) or 0))
            except (ValueError, TypeError):
                setattr(cliente, f, 0)
    for f in _CLI_BOOL:
        if f in data:
            setattr(cliente, f, bool(data.get(f)))
    for f in _CLI_DATE:
        if f in data:
            setattr(cliente, f, _cli_date(data.get(f)))
    if 'provincia' in data:
        pid = data.get('provincia')
        cliente.provincia = Provincia.objects.filter(id=pid).first() if pid else None
    if 'canton' in data:
        cid = data.get('canton')
        cliente.canton = Canton.objects.filter(id=cid).first() if cid else None


def _serialize_cliente_full(c):
    data = {
        'id': c.id,
        'ruc': c.ruc,
        'razon_social': c.razon_social,
        'nombre_comercial': c.nombre_comercial,
        'size': c.size,
        'fecha_ingreso': c.fecha_ingreso.isoformat() if c.fecha_ingreso else None,
        'fecha_retiro': c.fecha_retiro.isoformat() if c.fecha_retiro else None,
        'ultima_venta': c.ultima_venta.isoformat() if c.ultima_venta else None,
        'provincia': c.provincia_id,
        'provincia_nombre': getattr(c.provincia, 'nombre', None),
        'canton': c.canton_id,
        'canton_nombre': getattr(c.canton, 'nombre', None),
        'plazo_max': c.plazo_max,
        'desc_vta': str(c.desc_vta),
        'cupo': str(c.cupo),
        'valor_puesto': str(c.valor_puesto),
        'control_cupo': c.control_cupo,
        'requiere_correo': c.requiere_correo,
        'controla_factura_reverso': c.controla_factura_reverso,
        'paga_iva': c.paga_iva,
    }
    for f in _CLI_CHAR:
        data[f] = getattr(c, f, '') or ''
    return data


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
        cliente = Cliente.objects.select_related('provincia', 'canton').get(pk=id)
        return JsonResponse(_serialize_cliente_full(cliente))
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
                cliente = Cliente(
                    razon_social=razon_social,
                    nombre_comercial=nombre_comercial,
                    ruc=ruc,
                    size=size,
                    fecha_ingreso=fecha_ingreso,
                    fecha_retiro=fecha_retiro
                )
                _aplicar_campos_cliente(cliente, data)   # campos del ERP
                cliente.save()
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

        _aplicar_campos_cliente(cliente, data)   # campos del ERP

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

            