from ..models import AsignacionCalendario
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
def listar_asignacion_calendario(request):
    asignaciones = AsignacionCalendario.objects.all()
    data = []
    for asignacion in asignaciones:
        data.append({
            'id': asignacion.id,
            'asignacion': asignacion.asignacion.id,
            'fecha': asignacion.fecha,
            'turno': asignacion.turno,
            'dia_numero': asignacion.dia_numero
        })

    return Response(data)


@api_view(['POST'])
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