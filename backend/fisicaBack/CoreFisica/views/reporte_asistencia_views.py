from django.http import JsonResponse
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_asistencia(request):
    # filtros
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')

    # traer asignaciones filtradas por fecha/cliente (si se envían)
    asig_qs = Asignacion.objects.select_related(
        'cliente', 'instalacion', 'puesto', 'horario', 'persona'
    ).filter(persona__is_active=True)

    if fecha:
        # incluir asignaciones sin fecha para no ocultar registros históricos
        asig_qs = asig_qs.filter(Q(fecha=fecha) | Q(fecha__isnull=True))
    if cliente_id:
        asig_qs = asig_qs.filter(cliente_id=cliente_id)

    # indexar por persona_id (una por persona; si hubiera varias, tomamos la primera)
    asig_map = {}
    for a in asig_qs.order_by('id'):
        asig_map.setdefault(a.persona_id, a)

    data = []
    personas = Persona.objects.filter(is_active=True).order_by('apellidos', 'nombres')
    for p in personas:
        asig = asig_map.get(p.id)
        cliente_nombre = getattr(asig.cliente, 'nombre_comercial', '') if asig else ''
        puesto_tipo = getattr(asig.puesto, 'tipo', '') if asig else ''
        horario_str = ''
        if asig and asig.horario:
            horario_str = f"{asig.horario.hora_ingreso.strftime('%H:%M')} - {asig.horario.hora_salida.strftime('%H:%M')}"
        nombre_apellidos = f"{p.nombres} {p.apellidos}".strip()

        data.append({
            'codigo': f"RA-{asig.id}" if asig else '',
            'cliente': cliente_nombre,
            'puesto': puesto_tipo,
            'horario': horario_str,
            'nombre_apellidos': nombre_apellidos,
            'estado': 'TURNO' if asig else '',
            'descripcion': '',
        })

    return JsonResponse(data, safe=False)