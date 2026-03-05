from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import ReporteAsistencia

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_asistencia(request):
    
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')

    qs = ReporteAsistencia.objects.select_related(
        'cliente', 'instalacion', 'puesto', 'horario', 'persona'
    )

    if fecha:
        qs = qs.filter(fecha=fecha)
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)

    data = []
    for r in qs.order_by('-fecha', '-created_at'):
        data.append({
            'codigo': r.codigo,
            'cliente': getattr(r.cliente, 'nombre_comercial', ''),
            'puesto': r.puesto_tipo or getattr(getattr(r.puesto, 'tipo', None), 'strip', lambda: '')(),
            'horario': (
                f"{r.horario.hora_ingreso.strftime('%H:%M')} - {r.horario.hora_salida.strftime('%H:%M')}"
                if r.horario else ''
            ),
            'nombre_apellidos': f"{getattr(r.persona, 'nombres', '')} {getattr(r.persona, 'apellidos', '')}".strip(),
            'estado': r.estado,
            'descripcion': r.descripcion or '',
            'fecha': r.fecha.isoformat() if r.fecha else '',
        })
    return JsonResponse(data, safe=False)