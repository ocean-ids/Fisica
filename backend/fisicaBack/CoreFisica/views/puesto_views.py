from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
import json
from ..models import Instalacion, Puesto, PuestoHorario, Zona
from ..utils import parse_input
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    if not request.user.has_perm('CoreFisica.add_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    zona_id = data.get('zona_id') or data.get('zona')
    cantidad_puestos = data.get('cantidad_puestos', 1)
    tipo = data.get('tipo')
    horarios = data.get('horarios')
    horarios_text = data.get('horarios_text')

    try:
        instalacion = Instalacion.objects.get(id=instalacion_id)
    except Instalacion.DoesNotExist:
        return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

    # Validar zona pertenece a la instalación
    zona = None
    if zona_id:
        try:
            zona = Zona.objects.get(id=zona_id)
        except Zona.DoesNotExist:
            return JsonResponse({'error': 'Zona no encontrada'}, status=404)
        if zona.instalacion_id != instalacion.id:
            return JsonResponse({'error': 'La zona no pertenece a la instalación'}, status=400)
    try:
        cantidad_puestos = int(cantidad_puestos)
    except (TypeError, ValueError):
        cantidad_puestos = 1
    if cantidad_puestos < 1:
        cantidad_puestos = 1

    horarios_payload = []
    try:
        if horarios_text:
            parsed = parse_input(horarios_text)
            for r in parsed:
                horarios_payload.append({
                    'dia': r.get('dia'),
                    'horas': r.get('horas', 12),
                    'turno': r.get('turno') or 'Diurno'
                })
        elif isinstance(horarios, list):
            for h in horarios:
                dia = h.get('dia')
                horas = h.get('horas')
                if dia and horas is not None:
                    horarios_payload.append({
                        'dia': dia,
                        'horas': h.get('horas', 12),
                        'turno': h.get('turno') or 'Diurno'
                    })
    except Exception:
        horarios_payload = []

    puestos_creados = []
    for _ in range(cantidad_puestos):
        puesto = Puesto.objects.create(
            nombre=data.get('nombre'),
            tipo=tipo,
            cantidad_puestos=cantidad_puestos,
            instalacion_id=instalacion.id,
            zona=zona
        )

        for h in horarios_payload:
            if h.get('dia'):
                PuestoHorario.objects.create(
                    puesto=puesto,
                    dia=h['dia'],
                    horas=h.get('horas', 12),
                    turno=h.get('turno') or 'Diurno'
                )

        try:
            puesto.sync_from_horarios()
            puesto.save()
        except Exception:
            pass

        puestos_creados.append({
            'id': puesto.id,
            'nombre': puesto.nombre,
            'tipo': puesto.tipo,
            'cantidad_puestos': puesto.cantidad_puestos,
            'turno': puesto.get_turno(),
            'turno_display': puesto.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in puesto.horarios.all()],
            'instalacion_id': puesto.instalacion_id,
            'zona_id': puesto.zona_id,
            'resumen': puesto.resumen,
        })

    return JsonResponse({
        'message': 'Puesto creado',
        'cantidad_creada': len(puestos_creados),
        'puesto': puestos_creados[0] if puestos_creados else None,
        'puestos': puestos_creados
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos(request):
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    puestos_qs = Puesto.objects.all()
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo': p.tipo,
            'cantidad_puestos': p.cantidad_puestos,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
            'instalacion_id': p.instalacion_id,
            'zona_id': p.zona_id,
            'zona_titulo': getattr(p.zona, 'titulo', None),
            'resumen': p.resumen,
        })
    return JsonResponse(resultado, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_instalacion(request, instalacion_id):
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    puestos_qs = Puesto.objects.filter(instalacion_id=instalacion_id)
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo': p.tipo,
            'cantidad_puestos': p.cantidad_puestos,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
            'instalacion_id': p.instalacion_id,
            'zona_id': p.zona_id,
            'zona_titulo': getattr(p.zona, 'titulo', None),
            'resumen': p.resumen,
        })
    return JsonResponse(resultado, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos_por_cliente(request, cliente_id):
    if not request.user.has_perm('CoreFisica.view_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403
        )

    puestos_qs = Puesto.objects.filter(instalacion__cliente_id=cliente_id).select_related('instalacion', 'zona')
    resultado = []
    for p in puestos_qs:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo': p.tipo,
            'cantidad_puestos': p.cantidad_puestos,
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
            'instalacion_id': p.instalacion_id,
            'resumen': p.resumen,
            'instalacion__provincia': getattr(p.instalacion, 'provincia', None),
            'instalacion__ciudad': getattr(p.instalacion, 'ciudad', None),
            'instalacion_nombre': getattr(p.instalacion, 'nombre', None),
            'zona_id': p.zona_id,
            'zona_titulo': getattr(p.zona, 'titulo', None),
        })
    return JsonResponse(resultado, safe=False)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_puesto(request, id):
    if not request.user.has_perm('CoreFisica.change_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        data = json.loads(request.body)
        print('Payload recibido:', data)  
        puesto = Puesto.objects.get(id=id)

        instalacion_id = data.get('instalacion_id')
        zona_id = data.get('zona_id') or data.get('zona')
        if instalacion_id:
            if not Instalacion.objects.filter(id=instalacion_id).exists():
                return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
            puesto.instalacion_id = instalacion_id

        if zona_id:
            try:
                zona = Zona.objects.get(id=zona_id)
            except Zona.DoesNotExist:
                return JsonResponse({'error': 'Zona no encontrada'}, status=404)
            if instalacion_id and zona.instalacion_id != instalacion_id:
                return JsonResponse({'error': 'La zona no pertenece a la instalación'}, status=400)
            if not instalacion_id and zona.instalacion_id != puesto.instalacion_id:
                return JsonResponse({'error': 'La zona no pertenece a la instalación'}, status=400)
            puesto.zona = zona

        puesto.nombre = data.get('nombre', puesto.nombre)
        puesto.tipo = data.get('tipo', puesto.tipo)
        cantidad_puestos = data.get('cantidad_puestos', puesto.cantidad_puestos)
        try:
            cantidad_puestos = int(cantidad_puestos)
        except (TypeError, ValueError):
            cantidad_puestos = puesto.cantidad_puestos
        if cantidad_puestos < 1:
            cantidad_puestos = 1
        puesto.cantidad_puestos = cantidad_puestos
        # turno ya no se guarda a nivel de Puesto; se maneja por horario
        # actualizar horarios si vienen
        horarios = data.get('horarios')
        horarios_text = data.get('horarios_text')

        # aplicar cambios básicos
        puesto.save()
        horarios_payload = []
        try:
            if horarios_text:
                parsed = parse_input(horarios_text)
                puesto.horarios.all().delete()
                for r in parsed:
                    turno_val = r.get('turno') or 'Diurno'
                    PuestoHorario.objects.create(puesto=puesto, dia=r['dia'], horas=r['horas'], turno=turno_val)
                    horarios_payload.append({
                        'dia': r.get('dia'),
                        'horas': r.get('horas', 12),
                        'turno': turno_val
                    })
            elif isinstance(horarios, list):
                puesto.horarios.all().delete()
                for h in horarios:
                    dia = h.get('dia')
                    horas = h.get('horas')
                    if dia and horas is not None:
                        turno_val = h.get('turno') or 'Diurno'
                        PuestoHorario.objects.create(puesto=puesto, dia=dia, horas=horas, turno=turno_val)
                        horarios_payload.append({
                            'dia': dia,
                            'horas': horas,
                            'turno': turno_val
                        })
        except Exception:
            pass
        try:
            puesto.sync_from_horarios()
            puesto.save()
        except Exception:
            pass

        # crear puestos adicionales si la cantidad es mayor al grupo existente
        try:
            group_count = Puesto.objects.filter(
                nombre=puesto.nombre,
                instalacion_id=puesto.instalacion_id,
                zona_id=puesto.zona_id,
                tipo=puesto.tipo
            ).count()
            faltantes = max(cantidad_puestos - group_count, 0)
            for _ in range(faltantes):
                extra = Puesto.objects.create(
                    nombre=puesto.nombre,
                    tipo=puesto.tipo,
                    cantidad_puestos=cantidad_puestos,
                    instalacion_id=puesto.instalacion_id,
                    zona=puesto.zona
                )
                for h in horarios_payload:
                    if h.get('dia'):
                        PuestoHorario.objects.create(
                            puesto=extra,
                            dia=h['dia'],
                            horas=h.get('horas', 12),
                            turno=h.get('turno') or 'Diurno'
                        )
                try:
                    extra.sync_from_horarios()
                    extra.save()
                except Exception:
                    pass
        except Exception:
            pass
        return JsonResponse({
            'message': 'Puesto actualizado correctamente',
            'puesto': {
                'id': puesto.id,
                'nombre': puesto.nombre,
                'tipo': puesto.tipo,
                'cantidad_puestos': puesto.cantidad_puestos,
                'turno': puesto.get_turno(),
                'turno_display': puesto.get_turno_display(),
                'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in puesto.horarios.all()],
                'instalacion_id': puesto.instalacion_id,
                'zona_id': puesto.zona_id,
            }
        }, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_puesto(request, id):
    if not request.user.has_perm('CoreFisica.delete_puesto'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    try:
        puesto = Puesto.objects.get(id=id)
        puesto.delete()
        return JsonResponse({'message': 'Puesto Eliminado Correctamente'}, status=200)
    except Puesto.DoesNotExist:
        return JsonResponse({'error': 'Puesto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)