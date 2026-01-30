from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from ..models import Asignacion
from ..serializers import AsignacionSerializer
import openpyxl


@api_view(['GET'])
def obtener_asignaciones(request, mes=None, anio=None):
    if mes and anio:
        asignaciones = Asignacion.objects.filter(
            mes=mes,
            anio=anio,
            estado='ACTIVO'
        ).select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario')
    else:
        asignaciones = Asignacion.objects.filter(
            estado='ACTIVO'
        ).select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario')
    
    serializer = AsignacionSerializer(asignaciones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def asignar_servicio(request):
    print(f"📥 Datos recibidos: {request.data}")
    serializer = AsignacionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    print(f"❌ Errores de validación: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def editar_servicio(request, id):
    try:
        asignacion = Asignacion.objects.get(id=id)
    except Asignacion.DoesNotExist:
        return Response({'error': 'Asinación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AsignacionSerializer(asignacion, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def guardar_orden_asignacion(request):
    ordenes = request.data.get('ordenes', [])

    for item in ordenes:
        try:
            asignacion = Asignacion.objects.get(id=item['id'])
            asignacion.orden = item['orden']
            asignacion.save()
        except Asignacion.DoesNotExist:
            continue
    return Response({'mensaje': 'Orden actualizado correctamente'})

@api_view(['DELETE'])
def eliminar_asignacion(request, id):
    try:
        asignar = Asignacion.objects.get(id=id)
        asignar.delete()
        return Response({'mensaje': 'Asignación eliminada correctamente'}, status=status.HTTP_204_NO_CONTENT)
    except Asignacion.DoesNotExist:
        return Response({'error': 'Asignacion no encontrada'}, status=status.HTTP_404_NOT_FOUND)


def exportar_asignaciones_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asignaciones"

    
    ws.append(['Horario', 'Código Cliente', 'Cliente', 'Nombre Puesto', 'Cantidad de Guardias', 'Horas de Trabajo', 'Cédula', 'Persona'])

    for asignacion in Asignacion.objects.all():
        ws.append([
            f"{asignacion.horario.hora_ingreso} - {asignacion.horario.hora_salida}",
            asignacion.cliente.codigo,  
            asignacion.cliente.nombre_comercial,
            asignacion.puesto.nombre,
            asignacion.puesto.cantidad_guardias,
            asignacion.puesto.horas_trabajo,
            asignacion.persona.cedula,
            f"{asignacion.persona.apellidos} {asignacion.persona.nombres}"
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reporte_asignaciones.xlsx'
    wb.save(response)
    return response