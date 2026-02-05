from ..models import AsignacionSemanal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..serializers import AsignacionSemanalSerializer
from django.db import transaction
from datetime import datetime, date, timedelta

@api_view(['GET'])
def listar_asignacion_semanal(request):
    """Listar asignaciones semanales. Filtrar por week_start (YYYY-MM-DD) y opcionalmente por cliente."""
    week_start = request.GET.get('week_start')
    cliente_id = request.GET.get('cliente')

    qs = AsignacionSemanal.objects.select_related('puesto').all()
    if week_start:
        try:
            ws = datetime.fromisoformat(week_start).date()
            qs = qs.filter(week_start=ws)
        except Exception:
            return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if cliente_id:
        qs = qs.filter(puesto__instalacion__cliente_id=cliente_id)

    qs = qs.order_by('puesto_id')

    serializer = AsignacionSemanalSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def semanas_del_mes(request):
    """
    obtener parametros: mes 1-12, año(yyyy)
    Retorna: { weeks: ['YYYY-MM-DD', ...] }
    """

    mes = request.GET.get('mes')
    anio = request.GET.get('anio')

    if not mes or not anio:
        return Response({'error': 'mes y año invalidos son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        mes = int(mes)
        anio = int(anio)
        if not (1 <= mes <=12):
            raise ValueError
    except ValueError:
        return Response({'error': 'mes o anio inválidos'}, status=status.HTTP_400_BAD_REQUEST)

    first_day = date(anio, mes, 1)
    offset = (0 - first_day.weekday()) % 7
    current = first_day + timedelta(days=offset)

    weeks = []
    while current.month == mes:
        weeks.append(current.isoformat())
        current += timedelta(days=7)

    return Response({'weeks': weeks})



@api_view(['POST'])
def crear_o_actualizar_asignacion_semanal(request):
    """Crea o actualiza una fila semanal (unicidad por puesto+week_start)."""
    data = request.data
    puesto_id = data.get('puesto')
    week_start = data.get('week_start')
    if not puesto_id or not week_start:
        return Response({'error': 'Faltan campos puesto o week_start'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ws = datetime.fromisoformat(week_start).date()
    except Exception:
        return Response({'error': 'week_start inválida, formato YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            obj, created = AsignacionSemanal.objects.get_or_create(puesto_id=puesto_id, week_start=ws)
            # actualizar campos de días
            for d in ['mon','tue','wed','thu','fri','sat','sun']:
                if d in data:
                    setattr(obj, d, data.get(d) or '')
            obj.save()
            serializer = AsignacionSemanalSerializer(obj)
            return Response({'created': created, 'result': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def copiar_semana(request):
    """Copiar semana: payload {from_week, to_week, cliente (opcional)}"""
    payload = request.data
    from_week = payload.get('from_week')
    to_week = payload.get('to_week')
    cliente_id = payload.get('cliente')
    if not from_week or not to_week:
        return Response({'error': 'from_week y to_week son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        fw = datetime.fromisoformat(from_week).date()
        tw = datetime.fromisoformat(to_week).date()
    except Exception:
        return Response({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    qs = AsignacionSemanal.objects.filter(week_start=fw)
    if cliente_id:
        qs = qs.filter(puesto__instalacion__cliente_id=cliente_id)

    created = 0
    updated = 0
    with transaction.atomic():
        for row in qs:
            obj, was_created = AsignacionSemanal.objects.update_or_create(
                puesto=row.puesto,
                week_start=tw,
                defaults={
                    'mon': row.mon,
                    'tue': row.tue,
                    'wed': row.wed,
                    'thu': row.thu,
                    'fri': row.fri,
                    'sat': row.sat,
                    'sun': row.sun,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

    return Response({'created': created, 'updated': updated, 'copied_from': str(fw), 'copied_to': str(tw)})
