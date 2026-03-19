from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from django.db.models import Q
from ..models import Instalacion, Provincia, Canton, Zona
from ..serializers import InstalacionSerializer


def resolve_canton_id(canton_token, provincia_token=None):
    """Resuelve un canton_id numérico a partir de un token que puede ser id o nombre."""
    if not canton_token:
        return None
    try:
        return int(canton_token)
    except Exception:
        pass

    provincia_obj = None
    if provincia_token:
        try:
            provincia_obj = Provincia.objects.filter(pk=int(provincia_token)).first()
        except Exception:
            provincia_obj = Provincia.objects.filter(nombre__iexact=str(provincia_token)).first()

    qs = Canton.objects.all()
    if provincia_obj:
        qs = qs.filter(provincia=provincia_obj)

    canton_obj = qs.filter(nombre__iexact=str(canton_token)).first()
    if canton_obj:
        return canton_obj.id
    return None


def get_or_create_provincia(provincia_token):
    """Devuelve o crea Provincia a partir de id o nombre."""
    if not provincia_token:
        return None
    try:
        provincia_obj = Provincia.objects.filter(pk=int(provincia_token)).first()
        if provincia_obj:
            return provincia_obj
    except Exception:
        pass
    provincia_obj = Provincia.objects.filter(nombre__iexact=str(provincia_token)).first()
    if provincia_obj:
        return provincia_obj
    return Provincia.objects.create(nombre=str(provincia_token).strip())


def get_or_create_canton(canton_token, provincia_token=None):
    """Devuelve o crea Canton (y Provincia si falta) a partir de id o nombre."""
    if not canton_token:
        return None
    try:
        canton_obj = Canton.objects.filter(pk=int(canton_token)).first()
        if canton_obj:
            return canton_obj
    except Exception:
        pass

    provincia_obj = get_or_create_provincia(provincia_token) if provincia_token else None

    qs = Canton.objects.all()
    if provincia_obj:
        qs = qs.filter(provincia=provincia_obj)
    canton_obj = qs.filter(nombre__iexact=str(canton_token)).first()
    if canton_obj:
        return canton_obj
    if provincia_obj:
        return Canton.objects.create(nombre=str(canton_token).strip(), provincia=provincia_obj)
    return None


def ensure_default_zonas(instalacion: Instalacion):
    """Garantiza que haya solo una Zona 1 por instalación cuando no se especifica otra.

    Si no hay zonas, crea Zona 1. Si hay más de una, deja la primera y elimina el resto.
    """
    zonas_qs = instalacion.zonas.order_by('id')
    count = zonas_qs.count()
    if count == 0:
        Zona.objects.create(instalacion=instalacion, titulo='Zona 1')
        return
    if count > 1:
        keep = zonas_qs.first()
        zonas_qs.exclude(id=keep.id).delete()


def set_instalacion_zona(instalacion: Instalacion, zona_token):
    """Selecciona/crea una zona según el token (id o título) y elimina el resto.

    - Si zona_token es numérico y existe, conserva esa y borra otras.
    - Si es texto, crea/usa esa Zona para la instalación y borra otras.
    - Si no viene nada, delega en ensure_default_zonas (Zona 1).
    """
    if not zona_token:
        ensure_default_zonas(instalacion)
        return

    try:
        zona_id = int(zona_token)
        zona = Zona.objects.filter(id=zona_id, instalacion=instalacion).first()
        if not zona:
            # Si el id no corresponde, cae a crear por título
            raise ValueError()
    except Exception:
        titulo = str(zona_token).strip() or 'Zona 1'
        zona, _ = Zona.objects.get_or_create(instalacion=instalacion, titulo=titulo)

    # Eliminar zonas distintas a la seleccionada
    instalacion.zonas.exclude(id=zona.id).delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_instalaciones(request):
    q = (request.GET.get('q') or '').strip()
    cliente_id = request.GET.get('cliente_id')
    cliente = (request.GET.get('cliente') or '').strip()
    provincia_id = request.GET.get('provincia_id')
    canton_id = request.GET.get('canton_id')
    zona_token = request.GET.get('zona_id') or request.GET.get('zona_titulo')

    qs = Instalacion.objects.select_related('cliente', 'canton', 'canton__provincia').prefetch_related('zonas').all()

    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    elif cliente:
        qs = qs.filter(
            Q(cliente__nombre_comercial__icontains=cliente) |
            Q(cliente__razon_social__icontains=cliente)
        )

    if provincia_id:
        qs = qs.filter(canton__provincia_id=provincia_id)

    if canton_id:
        qs = qs.filter(canton_id=canton_id)

    if zona_token:
        try:
            zona_id = int(zona_token)
            qs = qs.filter(zonas__id=zona_id)
        except Exception:
            qs = qs.filter(zonas__titulo__iexact=str(zona_token).strip())

    qs = qs.distinct().order_by('cliente__nombre_comercial', 'nombre', 'id')


    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(codigo__icontains=q) |
            Q(cliente__nombre_comercial__icontains=q) |
            Q(cliente__razon_social__icontains=q) |
            Q(canton__nombre__icontains=q) |
            Q(canton__provincia__nombre__icontains=q) |
            Q(direccion__icontains=q) |
            Q(zonas__titulo__icontains=q)
        )

    instalaciones = []
    for inst in qs:
        instalaciones.append({
            'id': inst.id,
            'codigo': inst.codigo or '',
            'nombre': inst.nombre or '',
            'cliente_id': inst.cliente_id,
            'cliente_nombre': getattr(inst.cliente, 'nombre_comercial', ''),
            'canton_id': inst.canton_id,
            'canton_nombre': getattr(inst.canton, 'nombre', ''),
            'provincia_id': getattr(getattr(inst.canton, 'provincia', None), 'id', None),
            'provincia_nombre': getattr(getattr(inst.canton, 'provincia', None), 'nombre', ''),
            'direccion': inst.direccion or '',
            'zonas': [
                {
                    'id': z.id,
                    'titulo': z.titulo,
                }
                for z in inst.zonas.all()
            ],
        })
    return JsonResponse(instalaciones, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_instalacion(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # soportar `cliente_id` desde frontend
    if 'cliente_id' in data and 'cliente' not in data:
        data['cliente'] = data.pop('cliente_id')

    # Intentar resolver/crear provincia y cantón desde tokens (id o nombre)
    provincia_token = data.get('provincia_id') or data.get('provincia')
    canton_token = data.get('canton_id') or data.get('canton')
    provincia_obj = get_or_create_provincia(provincia_token)
    canton_obj = get_or_create_canton(canton_token, provincia_obj.id if provincia_obj else provincia_token)
    if canton_obj:
        data['canton'] = canton_obj.id
    data.pop('canton_id', None)
    data.pop('provincia_id', None)

    # extraer zona antes de validar serializer para evitar campos no permitidos
    zona_token = data.get('zona_id') or data.get('zona_titulo')
    data.pop('zona_id', None)
    data.pop('zona_titulo', None)

    serializer = InstalacionSerializer(data=data)
    if serializer.is_valid():
        instalacion = serializer.save()
        set_instalacion_zona(instalacion, zona_token)
        return JsonResponse({'message': 'Instalación creada', 'id': instalacion.id})
    else:
        return JsonResponse({'error': 'Datos inválidos', 'details': serializer.errors}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_instalacion(request, id):
    try:
        data = json.loads(request.body)

        try:
            instalacion = Instalacion.objects.get(id=id)
        except Instalacion.DoesNotExist:
            return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

        # soportar `cliente_id` desde frontend
        if 'cliente_id' in data and 'cliente' not in data:
            data['cliente'] = data.pop('cliente_id')

        # Intentar resolver/crear provincia y cantón desde tokens (id o nombre)
        provincia_token = data.get('provincia_id') or data.get('provincia')
        canton_token = data.get('canton_id') or data.get('canton')
        provincia_obj = get_or_create_provincia(provincia_token)
        canton_obj = get_or_create_canton(canton_token, provincia_obj.id if provincia_obj else provincia_token)
        if canton_obj:
            data['canton'] = canton_obj.id
        data.pop('canton_id', None)
        data.pop('provincia_id', None)

        # extraer zona antes de validar serializer para evitar campos no permitidos
        zona_token = data.get('zona_id') or data.get('zona_titulo')
        data.pop('zona_id', None)
        data.pop('zona_titulo', None)

        serializer = InstalacionSerializer(instalacion, data=data, partial=True)
        if serializer.is_valid():
            instalacion = serializer.save()
            set_instalacion_zona(instalacion, zona_token)
            return JsonResponse({'message': 'Instalación actualizada', 'id': instalacion.id})
        else:
            return JsonResponse({'error': 'Datos inválidos', 'details': serializer.errors}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_instalacion(request, id):
    try:
        instalacion = Instalacion.objects.get(id=id)
        instalacion.delete()
        return JsonResponse({'message':'Instalación eliminada correctamente'}, status=200)
    except Instalacion.DoesNotExist:
        return JsonResponse({'error':'Instalación no encontrada'}, status=404)
    