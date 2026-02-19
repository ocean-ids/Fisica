from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
import json
from ..models import Instalacion, Puesto, PuestoHorario
from ..utils import parse_input
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    cantidad_guardias = data.get('cantidad_guardias', 1)
    tipo = data.get('tipo')
    horarios = data.get('horarios')
    horarios_text = data.get('horarios_text')

    try:
        instalacion = Instalacion.objects.get(id=instalacion_id)
    except Instalacion.DoesNotExist:
        return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
    puesto = Puesto.objects.create(
        nombre=data.get('nombre'),
        tipo=tipo,
        cantidad_guardias=cantidad_guardias,
        instalacion_id=instalacion.id
    )
    # crear horarios si vienen
    try:
        if horarios_text:
            parsed = parse_input(horarios_text)
            for r in parsed:
                turno_val = r.get('turno') or 'Diurno'
                PuestoHorario.objects.create(puesto=puesto, dia=r['dia'], horas=r.get('horas', 12), turno=turno_val)
        elif isinstance(horarios, list):
            for h in horarios:
                dia = h.get('dia')
                horas = h.get('horas')
                if dia and horas is not None:
                    turno_val = h.get('turno') or 'Diurno'
                    PuestoHorario.objects.create(puesto=puesto, dia=dia, horas=h.get('horas', 12), turno=turno_val)
    except Exception:
        pass
    # sincronizar resumen
    try:
        puesto.sync_from_horarios()
        puesto.save()
    except Exception:
        pass
    return JsonResponse({
        'message': 'Puesto creado',
        'puesto': {
            'id': puesto.id,
            'nombre': puesto.nombre,
            'tipo': puesto.tipo,
            'cantidad_guardias': puesto.cantidad_guardias,
            'turno': puesto.get_turno(),
            'turno_display': puesto.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in puesto.horarios.all()],
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
            'tipo': p.tipo,
            'cantidad_guardias': p.cantidad_guardias,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
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
            'tipo': p.tipo,
            'cantidad_guardias': p.cantidad_guardias,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
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
            'tipo': p.tipo,
            'cantidad_guardias': p.cantidad_guardias,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
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
        puesto.tipo = data.get('tipo', puesto.tipo)
        puesto.cantidad_guardias = data.get('cantidad_guardias', puesto.cantidad_guardias)
        # turno ya no se guarda a nivel de Puesto; se maneja por horario
        # actualizar horarios si vienen
        horarios = data.get('horarios')
        horarios_text = data.get('horarios_text')

        # aplicar cambios básicos
        puesto.save()
        try:
            if horarios_text:
                parsed = parse_input(horarios_text)
                puesto.horarios.all().delete()
                for r in parsed:
                    turno_val = r.get('turno') or 'Diurno'
                    PuestoHorario.objects.create(puesto=puesto, dia=r['dia'], horas=r['horas'], turno=turno_val)
            elif isinstance(horarios, list):
                puesto.horarios.all().delete()
                for h in horarios:
                    dia = h.get('dia')
                    horas = h.get('horas')
                    if dia and horas is not None:
                        turno_val = h.get('turno') or 'Diurno'
                        PuestoHorario.objects.create(puesto=puesto, dia=dia, horas=horas, turno=turno_val)
        except Exception:
            pass
        try:
            puesto.sync_from_horarios()
            puesto.save()
        except Exception:
            pass
        return JsonResponse({
            'message': 'Puesto actualizado correctamente',
            'puesto': {
                'id': puesto.id,
                'nombre': puesto.nombre,
                'tipo': puesto.tipo,
                'cantidad_guardias': puesto.cantidad_guardias,
                'turno': puesto.get_turno(),
                'turno_display': puesto.get_turno_display(),
                'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in puesto.horarios.all()],
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