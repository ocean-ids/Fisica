from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
import json
from ..models import Instalacion, Puesto
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    cantidad_guardias = data.get('cantidad_guardias', 1)
    horas_trabajo = data.get('horas_trabajo')
    turno_in = data.get('turno', 'Diurno')
    # aceptar solo los valores exactos 'Diurno' o 'Nocturno'
    if not isinstance(turno_in, str):
        return JsonResponse({'error': 'Valor de turno inválido'}, status=400)
    t = turno_in.strip()
    if t not in ('Diurno', 'Nocturno'):
        return JsonResponse({'error': "Valor de turno inválido: use 'Diurno' o 'Nocturno'"}, status=400)
    turno = t
    dias = data.get('dias', [])

    instalacion = Instalacion.objects.get(id=instalacion_id)
    puesto = Puesto.objects.create(
        nombre=data.get('nombre'),
        cantidad_guardias=cantidad_guardias,
        horas_trabajo=horas_trabajo,
        turno=turno,  
        dias=dias,
        instalacion_id=instalacion.id
    )
    return JsonResponse({
        'message': 'Puesto creado',
        'puesto': {
            'id': puesto.id,
            'nombre': puesto.nombre,
            'cantidad_guardias': puesto.cantidad_guardias,
            'horas_trabajo': puesto.horas_trabajo,
            'turno': puesto.turno,
            'turno_display': puesto.get_turno_display(),
            'dias': puesto.dias,
            'instalacion_id': puesto.instalacion_id,
            'resumen': puesto.resumen,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos(request):
    puestos_qs = Puesto.objects.all()
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'cantidad_guardias': p.cantidad_guardias,
            'horas_trabajo': p.horas_trabajo,
            'turno': p.turno,
            'turno_display': p.get_turno_display(),
            'dias': p.dias,
            'instalacion_id': p.instalacion_id,
            'resumen': p.resumen,
        })
    return JsonResponse(resultado, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_instalacion(request, instalacion_id):
    puestos_qs = Puesto.objects.filter(instalacion_id=instalacion_id)
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'cantidad_guardias': p.cantidad_guardias,
            'horas_trabajo': p.horas_trabajo,
            'turno': p.turno,
            'turno_display': p.get_turno_display(),
            'dias': p.dias,
            'instalacion_id': p.instalacion_id,
            'resumen': p.resumen,
        })
    return JsonResponse(resultado, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_cliente(request, cliente_id):
    puestos_qs = Puesto.objects.filter(instalacion__cliente_id=cliente_id).select_related('instalacion')
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'cantidad_guardias': p.cantidad_guardias,
            'horas_trabajo': p.horas_trabajo,
            'turno': p.turno,
            'turno_display': p.get_turno_display(),
            'dias': p.dias,
            'instalacion_id': p.instalacion_id,
            'resumen': p.resumen,
            'instalacion__provincia': getattr(p.instalacion, 'provincia', None),
            'instalacion__ciudad': getattr(p.instalacion, 'ciudad', None),
            'instalacion_nombre': getattr(p.instalacion, 'nombre', None),
        })
    return JsonResponse(resultado, safe=False)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_puesto(request, id):
    try:
        data = json.loads(request.body)
        print('Payload recibido:', data)  
        puesto = Puesto.objects.get(id=id)

        instalacion_id = data.get('instalacion_id')
        if instalacion_id:
            if not Instalacion.objects.filter(id=instalacion_id).exists():
                return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
            puesto.instalacion_id = instalacion_id

        puesto.nombre = data.get('nombre', puesto.nombre)
        puesto.cantidad_guardias = data.get('cantidad_guardias', puesto.cantidad_guardias)
        puesto.horas_trabajo = data.get('horas_trabajo', puesto.horas_trabajo)
        turno_in = data.get('turno')
        if turno_in is not None:
            if not isinstance(turno_in, str):
                return JsonResponse({'error': 'Valor de turno inválido'}, status=400)
            t = turno_in.strip()
            if t not in ('Diurno', 'Nocturno'):
                return JsonResponse({'error': "Valor de turno inválido: use 'Diurno' o 'Nocturno'"}, status=400)
            puesto.turno = t
        puesto.dias = data.get('dias', puesto.dias)

        puesto.save()
        return JsonResponse({
            'message': 'Puesto actualizado correctamente',
            'puesto': {
                'id': puesto.id,
                'nombre': puesto.nombre,
                'cantidad_guardias': puesto.cantidad_guardias,
                'horas_trabajo': puesto.horas_trabajo,
                'turno': puesto.turno,
                'turno_display': puesto.get_turno_display(),
                'dias': puesto.dias,
                'instalacion_id': puesto.instalacion_id,
            }
        }, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_puesto(request, id):
        try:
            puesto = Puesto.objects.get(id=id)
            puesto.delete()
            return JsonResponse({'message': 'Puesto Eliminado Correctamente'}, status=200)
        except Puesto.DoesNotExist:
            return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)