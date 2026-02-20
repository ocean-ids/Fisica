from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import Horario, PatronHorario

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_horarios(request):
    data = []
    for h in Horario.objects.select_related('patronHorario').all():
        data.append({
            'id': h.id,
            'hora_ingreso': h.hora_ingreso,
            'hora_salida': h.hora_salida,
            'patronHorario': {
                'id': h.patronHorario.id,
                'codigo': h.patronHorario.codigo,
                'secuencia': h.patronHorario.secuencia,
            } if h.patronHorario else None,
        })
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_horario(request):
    try:
        data = json.loads(request.body)
        print(f"📥 Datos recibidos para crear horario: {data}")

        if not all(k in data for k in ('hora_ingreso', 'hora_salida')):
            return JsonResponse({'error': 'Faltan campos requeridos (hora_ingreso, hora_salida)'}, status=400)

        patron_obj = None
        patron_id = data.get('patron_id')
        if patron_id:
            patron_obj = PatronHorario.objects.filter(id=patron_id).first()
            if patron_obj is None:
                return JsonResponse({'error': 'PatronHorario no encontrado'}, status=404)
        
        horario = Horario.objects.create(
            hora_ingreso=data.get('hora_ingreso'),
            hora_salida=data.get('hora_salida'),
            patronHorario=patron_obj,
        )

        return JsonResponse({
            'message':'Horario creado exitosamente',
            'id': horario.id,
            'horario':{
                'id': horario.id,
                'hora_ingreso': str(horario.hora_ingreso),
                'hora_salida': str(horario.hora_salida),
                'patronHorario': {
                    'id': horario.patronHorario.id,
                    'codigo': horario.patronHorario.codigo,
                    'secuencia': horario.patronHorario.secuencia
                } if horario.patronHorario else None,
            }
        }, status=201)
    except Exception as e:
        print(f"❌ Error al crear horario: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_horario(request, id):
    try:
        horario = Horario.objects.get(id=id)
        data = json.loads(request.body)

        horario.hora_ingreso = data.get('hora_ingreso', horario.hora_ingreso)
        horario.hora_salida = data.get('hora_salida', horario.hora_salida)
        if 'patron_id' in data:
            pid = data.get('patron_id')
            if pid:
                patron_obj = PatronHorario.objects.filter(id=pid).first()
                if patron_obj is None:
                    return JsonResponse({'error': 'PatronHorario no encontrado'}, status=404)
                horario.patronHorario = patron_obj
            else:
                horario.patronHorario = None
        horario.save()

        return JsonResponse({
            'message': 'Horario actualizado exitosamente',
            'horario': {
                'id': horario.id,
                'hora_ingreso': str(horario.hora_ingreso),
                'hora_salida': str(horario.hora_salida),
                'patronHorario': {
                    'id': horario.patronHorario.id,
                    'codigo': horario.patronHorario.codigo,
                    'secuencia': horario.patronHorario.secuencia
                } if horario.patronHorario else None,
            }
        }, status=200)
    except Horario.DoesNotExist:
        return JsonResponse({'error': 'Horario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_horario(request, id):
    try:
        horario = Horario.objects.get(id=id)
        horario.delete()
        return JsonResponse({'message': 'Horario eliminado exitosamente'}, status=200)
    except Horario.DoesNotExist:
        return JsonResponse({'error': 'Horario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_patrones(request):
    patrones = PatronHorario.objects.all().values('id', 'codigo', 'secuencia')
    return JsonResponse(list(patrones), safe=False)

def _validate_patron_payload(data):
    if not all(k in data for k in ('codigo', 'secuencia')):
        raise ValueError('Faltan codigo y secuencia')
    seq = data.get('secuencia')
    if not isinstance(seq, list) or not seq:
        raise ValueError('secuencia debe ser lista no vacía')
    allowed = {"D", "N", "F", "-"}
    cleaned = []
    for token in seq:
        t = str(token).strip().upper()
        if t not in allowed:
            raise ValueError(f'Símbolo no permitido: {token}')
        cleaned.append(t)
    return cleaned

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_patron(request):
    try:
        data = json.loads(request.body)
        secuencia = _validate_patron_payload(data)
        patron = PatronHorario.objects.create(
            codigo=data.get('codigo'),
            secuencia=secuencia,
        )
        return JsonResponse({'message': 'Patron creado exitosamente', 'patron': {
            'id': patron.id, 'codigo': patron.codigo, 'secuencia': patron.secuencia,
        }}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_patron(request, id):
    try:
        patron = PatronHorario.objects.get(id=id)
        data = json.loads(request.body)
        if 'secuencia' in data:
            patron.secuencia = _validate_patron_payload(data)
        if 'codigo' in data:
            patron.codigo = data.get('codigo', patron.codigo)
        patron.save()
        return JsonResponse({'message': 'Patron actualizado exitosamente', 'patron': {
            'id': patron.id, 'codigo': patron.codigo, 'secuencia': patron.secuencia,
        }}, status=200)
    except PatronHorario.DoesNotExist:
        return JsonResponse({'error': 'Patron no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_patron(request, id):
    try:
        patron = PatronHorario.objects.get(id=id)
        patron.delete()
        return JsonResponse({'message': 'Patron eliminado exitosamente'}, status=200)
    except PatronHorario.DoesNotExist:
        return JsonResponse({'error': 'Patron no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

