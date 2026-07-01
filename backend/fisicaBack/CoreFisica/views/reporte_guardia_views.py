from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..models import ReporteGuardia
from ..serializers import ReporteGuardiaSerializer

TURNOS = ('Diurno', 'Nocturno')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_reporte_guardia(request):
    """Filas del reporte por ?fecha=YYYY-MM-DD&turno=Diurno|Nocturno (opcional ?seccion=)."""
    qs = ReporteGuardia.objects.select_related('persona_ref')
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    seccion = request.GET.get('seccion')
    if fecha:
        qs = qs.filter(fecha=fecha)
    if turno in TURNOS:
        qs = qs.filter(turno=turno)
    if seccion:
        qs = qs.filter(seccion=seccion)
    return Response(ReporteGuardiaSerializer(qs, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_reporte_guardia(request, id):
    fila = get_object_or_404(ReporteGuardia, id=id)
    s = ReporteGuardiaSerializer(fila, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def actualizar_reporte_guardia(request, id):
    fila = get_object_or_404(ReporteGuardia, id=id)
    s = ReporteGuardiaSerializer(fila, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_reporte_guardia(request, id):
    fila = get_object_or_404(ReporteGuardia, id=id)
    fila.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)