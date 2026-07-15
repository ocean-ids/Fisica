import datetime
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..models import ReporteGuardia, Asignacion
from ..serializers import ReporteGuardiaSerializer

TURNOS = ('Diurno', 'Nocturno')

# Campos de contenido que el usuario puede editar a mano en el reporte de guardia.
EDITABLE_CONTENT_FIELDS = (
    'cliente', 'puesto', 'persona_nombre', 'proviene', 'valor', 'tipo',
    'autorizacion', 'motivo', 'fecha_evento',
)


def _sync_no_cubiertos(fecha, turno):
    """Refleja en NO_CUBIERTOS los puestos (asignaciones) SIN persona para esa
    fecha/turno. Conserva la autorizacion/motivo escritos a mano. Idempotente:
    crea/actualiza una fila auto por asignacion vacante y borra las que ya no aplican."""
    try:
        fecha_obj = fecha if isinstance(fecha, datetime.date) else datetime.date.fromisoformat(str(fecha))
    except (TypeError, ValueError):
        return
    if turno not in TURNOS:
        return

    from .reporte_asistencia_views import _calendar_dnf_for_date

    mes, anio = fecha_obj.month, fecha_obj.year
    month_start = fecha_obj.replace(day=1)
    if mes == 12:
        month_end = datetime.date(anio + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        month_end = datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)

    # Vacantes: asignaciones ACTIVAS sin persona, puesto abierto, que aplican al mes.
    vac = Asignacion.objects.select_related('cliente', 'puesto').prefetch_related('puesto__horarios').filter(
        estado='ACTIVO', persona__isnull=True, puesto__activo=True
    ).filter(
        Q(mes=mes, anio=anio) |
        (Q(recurring=True) & Q(start_date__lte=month_end) & (Q(end_date__isnull=True) | Q(end_date__gte=month_start)))
    )

    dnf = _calendar_dnf_for_date(fecha_obj)      # {asignacion_id: 'D'|'N'|'F'}
    turno_letter = 'D' if turno == 'Diurno' else 'N'
    dia = fecha_obj.weekday() + 1                 # 1=Lunes ... 7=Domingo

    def _aplica(a):
        letra = dnf.get(a.id)
        if letra in ('D', 'N'):
            return letra == turno_letter          # el calendario manda si existe
        if letra == 'F':
            return False
        # Sin calendario: derivar el turno del horario del puesto ese dia.
        turnos = set()
        horarios = a.puesto.horarios.all() if a.puesto else []
        for h in horarios:
            if getattr(h, 'dia', None) != dia:
                continue
            t = (getattr(h, 'turno', '') or '').strip().lower()
            if t.startswith('d'):
                turnos.add('Diurno')
            elif t.startswith('n'):
                turnos.add('Nocturno')
            else:
                turnos.update({'Diurno', 'Nocturno'})   # 24h / ambos
        return turno in turnos

    vigentes = [a for a in vac if _aplica(a)]
    vigentes_ids = {a.id for a in vigentes}

    # Borrar filas auto que ya no aplican (cubiertas, cerradas o fuera de turno).
    ReporteGuardia.objects.filter(
        fecha=fecha_obj, turno=turno, seccion='NO_CUBIERTOS', auto=True
    ).exclude(asignacion_ref_id__in=vigentes_ids).delete()

    # Upsert por asignacion (conserva autorizacion/motivo escritos a mano).
    existentes = {
        r.asignacion_ref_id: r
        for r in ReporteGuardia.objects.filter(
            fecha=fecha_obj, turno=turno, seccion='NO_CUBIERTOS', auto=True
        )
    }
    for a in vigentes:
        cliente = getattr(a.cliente, 'nombre_comercial', '') or ''
        puesto = getattr(a.puesto, 'nombre', '') or ''
        row = existentes.get(a.id)
        if row:
            ov = row.overrides or {}
            cambios = []
            # No pisar los campos que el usuario editó a mano.
            if 'cliente' not in ov and row.cliente != cliente:
                row.cliente = cliente
                cambios.append('cliente')
            if 'puesto' not in ov and row.puesto != puesto:
                row.puesto = puesto
                cambios.append('puesto')
            if cambios:
                row.save(update_fields=cambios)
        else:
            ReporteGuardia.objects.create(
                fecha=fecha_obj, turno=turno, seccion='NO_CUBIERTOS',
                cliente=cliente, puesto=puesto, auto=True, asignacion_ref=a,
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_reporte_guardia(request):
    """Filas del reporte por ?fecha=YYYY-MM-DD&turno=Diurno|Nocturno (opcional ?seccion=)."""
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    seccion = request.GET.get('seccion')
    # Mantener NO_CUBIERTOS al dia con las vacantes de esa fecha/turno.
    if fecha and turno in TURNOS:
        _sync_no_cubiertos(fecha, turno)
    qs = ReporteGuardia.objects.select_related('persona_ref')
    if fecha:
        qs = qs.filter(fecha=fecha)
    if turno in TURNOS:
        qs = qs.filter(turno=turno)
    if seccion:
        qs = qs.filter(seccion=seccion)
    return Response(ReporteGuardiaSerializer(qs, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_reporte_guardia(request):
    """Crea una fila manual del reporte (p. ej. APOYO). No se sincroniza con nada;
    solo existe en el reporte de guardia."""
    s = ReporteGuardiaSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    s.save(auto=False)   # manual: nunca lo toca la sincronizacion automatica
    return Response(s.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def actualizar_reporte_guardia(request, id):
    fila = get_object_or_404(ReporteGuardia, id=id)
    s = ReporteGuardiaSerializer(fila, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    fila = s.save()
    # En filas auto (generadas desde asistencia), registrar los campos editados a
    # mano para conservarlos cuando la fila se regenere. Las manuales (APOYO) no se
    # regeneran, así que no hace falta.
    if fila.auto:
        ov = dict(fila.overrides or {})
        for campo in request.data:
            if campo in EDITABLE_CONTENT_FIELDS:
                ov[campo] = request.data.get(campo)
        if ov != (fila.overrides or {}):
            fila.overrides = ov
            fila.save(update_fields=['overrides'])
    return Response(ReporteGuardiaSerializer(fila).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_reporte_guardia(request, id):
    fila = get_object_or_404(ReporteGuardia, id=id)
    fila.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)