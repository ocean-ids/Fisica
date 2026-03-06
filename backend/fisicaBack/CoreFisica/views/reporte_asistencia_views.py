from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Asignacion, Persona, ReporteAsistencia

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_asistencia(request):
    # filtros
    fecha = request.GET.get('fecha')
    cliente_id = request.GET.get('cliente_id')

    overrides = {
        r.asignacion_id: r
        for r in ReporteAsistencia.objects.select_related('asignacion', 'modificado_por')
    }

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
        override = overrides.get(asig.id) if asig else None

        cliente_nombre = getattr(asig.cliente, 'nombre_comercial', '') if asig else ''
        puesto_tipo = getattr(asig.puesto, 'tipo', '') if asig else ''
        horario_str = ''
        if asig and asig.horario:
            horario_str = f"{asig.horario.hora_ingreso.strftime('%H:%M')} - {asig.horario.hora_salida.strftime('%H:%M')}"
        nombre_apellidos = f"{p.nombres} {p.apellidos}".strip()

        modificado_por_nombre = ''
        if override and override.modificado_por:
            full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
            modificado_por_nombre = full_name or override.modificado_por.get_username()

        data.append({
            'asignacion_id': asig.id if asig else None,
            # Mostrar vacío si no hay override, para que el usuario ingrese su propio código
            'codigo': override.codigo if (asig and override and override.codigo) else '',
            'cliente': cliente_nombre,
            'puesto': puesto_tipo,
            'horario': horario_str,
            'nombre_apellidos': nombre_apellidos,
            'estado': (override.estado or 'TURNO') if (asig and override) else ('TURNO' if asig else ''),
            'descripcion': (override.descripcion or '') if override else '',
            'modificado_por': modificado_por_nombre,
            'modificado_en': override.modificado_en.isoformat() if (override and override.modificado_en) else None,
        })

    return JsonResponse(data, safe=False)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def insertar_reporte_asistencia(request, asignacion_id):
    override, _ = ReporteAsistencia.objects.get_or_create(asignacion_id=asignacion_id)
    for field in ['codigo', 'estado', 'descripcion']:
        if field in request.data:
            val = request.data.get(field) or None
            setattr(override, field, val)
    if request.user and request.user.is_authenticated:
        override.modificado_por = request.user
    override.modificado_en = timezone.now()
    override.save()
    modificado_por_nombre = ''
    if override.modificado_por:
        full_name = f"{override.modificado_por.first_name} {override.modificado_por.last_name}".strip()
        modificado_por_nombre = full_name or override.modificado_por.get_username()
    return JsonResponse({
        'codigo': override.codigo or '',
        'estado': override.estado or 'TURNO',
        'descripcion': override.descripcion or '',
        'modificado_por': modificado_por_nombre,
        'modificado_en': override.modificado_en.isoformat() if override.modificado_en else None,
    }, status=status.HTTP_200_OK)
    