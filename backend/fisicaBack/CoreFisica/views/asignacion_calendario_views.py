from ..models import AsignacionCalendario
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_asignacion_calendario(request):
   
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    asignacion_id = request.GET.get('asignacion_id')

    asignaciones = AsignacionCalendario.objects.all()
    if fecha:
        asignaciones = asignaciones.filter(fecha=fecha)
    if turno:
        asignaciones = asignaciones.filter(turno=turno)
    if asignacion_id:
        asignaciones = asignaciones.filter(asignacion_id=asignacion_id)

   
    asignaciones = asignaciones.order_by('fecha')

   
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        if page < 1 or page_size < 1:
            raise ValueError
    except ValueError:
        return Response({"error": "Parámetros de paginación inválidos"}, status=status.HTTP_400_BAD_REQUEST)

    start = (page - 1) * page_size
    end = start + page_size

    asignaciones_list = list(asignaciones)
    asignaciones_paginadas = asignaciones_list[start:end]
    data = []
    for asignacion in asignaciones_paginadas:
        data.append({
            'id': asignacion.id,
            'asignacion': asignacion.asignacion.id,
            'fecha': asignacion.fecha,
            'turno': asignacion.turno,
            'dia_numero': asignacion.dia_numero
        })

    return Response({
        "results": data,
        "page": page,
        "page_size": page_size,
        "total": len(asignaciones_list)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_asignacion_calendario(request):
    datos = request.data

    if not datos.get("asignacion_id") or not datos.get("fecha") or not datos.get("turno"):
        return Response({"error": "Faltan datos requeridos"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        nueva = AsignacionCalendario.objects.create(
            asignacion_id=datos.get("asignacion_id"),
            fecha=datos.get("fecha"),
            turno=datos.get("turno"),
            dia_numero=datos.get("dia_numero")
        )
        return Response({"id": nueva.id, "mensaje": "Creado"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)