"""Vistas de ubicación: catálogos de provincias, cantones y zonas."""
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Provincia, Canton, Zona, Parroquia

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_provincias(request):
    if not request.user.has_perm('CoreFisica.view_provincia'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    provincias = Provincia.objects.all().order_by('nombre').values('id', 'nombre')
    return JsonResponse(list(provincias), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_cantones(request):
    if not request.user.has_perm('CoreFisica.view_canton'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    provincia_id = request.GET.get('provincia_id')
    qs = Canton.objects.select_related('provincia').all()
    if provincia_id:
        qs = qs.filter(provincia_id=provincia_id)
    cantones = qs.order_by('provincia__nombre', 'nombre').values('id', 'nombre', 'provincia_id', 'provincia__nombre')
    return JsonResponse(list(cantones), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_parroquias(request):
    # Mismo permiso que cantones (catálogo de ubicación en cascada).
    if not request.user.has_perm('CoreFisica.view_canton'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    canton_id = request.GET.get('canton_id')
    qs = Parroquia.objects.all()
    if canton_id:
        qs = qs.filter(canton_id=canton_id)
    parroquias = qs.order_by('nombre').values('id', 'nombre', 'canton_id')
    return JsonResponse(list(parroquias), safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_zonas(request):
    if not request.user.has_perm('CoreFisica.view_zona'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    instalacion_id = request.GET.get('instalacion_id')
    if not instalacion_id:
        return JsonResponse({'error': 'instalacion_id es requerido'}, status=400)
    qs = Zona.objects.filter(instalacion_id=instalacion_id).order_by('titulo')
    zonas = qs.values('id', 'titulo', 'instalacion_id')
    return JsonResponse(list(zonas), safe=False)