from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Provincia, Canton, Zona

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_provincias(request):
    provincias = Provincia.objects.all().order_by('nombre').values('id', 'nombre')
    return JsonResponse(list(provincias), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_cantones(request):
    provincia_id = request.GET.get('provincia_id')
    qs = Canton.objects.select_related('provincia').all()
    if provincia_id:
        qs = qs.filter(provincia_id=provincia_id)
    cantones = qs.order_by('provincia__nombre', 'nombre').values('id', 'nombre', 'provincia_id', 'provincia__nombre')
    return JsonResponse(list(cantones), safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_zonas(request):
    instalacion_id = request.GET.get('instalacion_id')
    if not instalacion_id:
        return JsonResponse({'error': 'instalacion_id es requerido'}, status=400)
    qs = Zona.objects.filter(instalacion_id=instalacion_id).order_by('orden', 'codigo')
    zonas = qs.values('id', 'codigo', 'titulo', 'instalacion_id')
    return JsonResponse(list(zonas), safe=False)