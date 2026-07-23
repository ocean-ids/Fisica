from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Sum, F, Case, When, DecimalField

from ..models import ReporteGuardia, ReportePago, TarifaPago
from ..serializers import ReportePagoSerializer, TarifaPagoSerializer

TURNOS = ('Diurno', 'Nocturno')

# Secciones del Reporte de Guardia que generan un pago (alguien cubrió un turno).
SECCIONES_PAGABLES = ('DOBLADAS', 'ADICIONALES', 'ADELANTOS', 'APOYO')

# Tipo de servicio sugerido según el tipo de la persona (el usuario puede cambiarlo).
TIPO_SERVICIO_POR_PERSONA = {
    'FIJOS': 'Guardias fijos',
    'RETEN': 'Guardias fijos',
    'CUSTODIO': 'Guardias fijos',
    'OPERADOR CENTRO CONTROL': 'Guardias fijos',
    'EVENTUAL': 'Eventuales',
    'SUPERVISOR EVENTUAL': 'Supervisores eventuales',
    'SUPERVISOR ZONAL': 'Horas extras supervisor fijo',
    'SUPERVISOR MOTORIZADO': 'Horas extras supervisor fijo',
    'SUPERVISOR DE ACOMPAÑAMIENTO': 'Horas extras supervisor fijo',
    'SUPERVISOR CENTRO CONTROL': 'Horas extras supervisor fijo',
}


def _tipo_servicio_sugerido(persona):
    if not persona:
        return ''
    return TIPO_SERVICIO_POR_PERSONA.get((getattr(persona, 'tipo', '') or '').upper(), '')


def _datos_bancarios(persona):
    """(banco, tipo_cuenta, numero_cuenta, cedula) desde la persona y sus 'Otros Datos'."""
    banco = tipo_cuenta = numero_cuenta = cedula = ''
    if persona:
        cedula = getattr(persona, 'cedula', '') or ''
        od = getattr(persona, 'otros_datos', None)   # EmpleadoOtrosDatos (pestaña bancaria)
        if od:
            banco = od.banco or ''
            if (od.cuenta_ahorros or '').strip():
                tipo_cuenta = 'Ahorros'
                numero_cuenta = od.cuenta_ahorros
            elif (od.cuenta_corriente or '').strip():
                tipo_cuenta = 'Corriente'
                numero_cuenta = od.cuenta_corriente
    return banco, tipo_cuenta, numero_cuenta, cedula


def _calcular_valor(tipo_servicio, horas):
    """Valor de la tarifa cuya banda [horas_min, horas_max] incluye 'horas'."""
    if not tipo_servicio or not horas:
        return Decimal('0')
    t = TarifaPago.objects.filter(
        tipo_servicio=tipo_servicio, horas_min__lte=horas, horas_max__gte=horas
    ).first()
    return t.valor if t else Decimal('0')


def _sync_pagos(fecha, turno):
    """Crea/actualiza los pagos (auto) a partir de las filas pagables del Reporte
    de Guardia de esa fecha/turno. Conserva lo escrito a mano (tipo_servicio, horas,
    valor_total, referencia). Idempotente."""
    guardias = list(
        ReporteGuardia.objects.select_related('persona_ref', 'persona_ref__otros_datos').filter(
            fecha=fecha, turno=turno, seccion__in=SECCIONES_PAGABLES,
        )
    )
    # Solo filas con persona (ref o nombre).
    guardias = [g for g in guardias if (g.persona_ref_id or (g.persona_nombre or '').strip())]
    vig_ids = {g.id for g in guardias}

    # Borrar pagos auto cuya fila de guardia ya no aplica.
    ReportePago.objects.filter(fecha=fecha, turno=turno, auto=True).exclude(
        reporte_guardia_ref_id__in=vig_ids
    ).delete()

    existentes = {
        p.reporte_guardia_ref_id: p
        for p in ReportePago.objects.filter(fecha=fecha, turno=turno, auto=True)
    }
    for g in guardias:
        banco, tipo_cuenta, numero_cuenta, cedula = _datos_bancarios(g.persona_ref)
        p = existentes.get(g.id)
        if p:
            # Refrescar los datos que vienen de guardia/persona; NO tocar lo manual.
            cambios = []
            desired = {
                'cliente': g.cliente, 'puesto': g.puesto, 'persona_nombre': g.persona_nombre,
                'seccion': g.seccion, 'cedula': cedula, 'banco': banco,
                'tipo_cuenta': tipo_cuenta, 'numero_cuenta': numero_cuenta,
            }
            for f, v in desired.items():
                if getattr(p, f) != v:
                    setattr(p, f, v)
                    cambios.append(f)
            if p.persona_ref_id != g.persona_ref_id:
                p.persona_ref_id = g.persona_ref_id
                cambios.append('persona_ref')
            # Sugerir el tipo solo si aún está vacío (no pisar lo elegido a mano).
            if not (p.tipo_servicio or '').strip():
                sug = _tipo_servicio_sugerido(g.persona_ref)
                if sug:
                    p.tipo_servicio = sug
                    cambios.append('tipo_servicio')
            if cambios:
                p.save(update_fields=cambios)
        else:
            ReportePago.objects.create(
                fecha=fecha, turno=turno, seccion=g.seccion,
                reporte_guardia_ref=g, persona_ref=g.persona_ref,
                cliente=g.cliente, puesto=g.puesto, persona_nombre=g.persona_nombre,
                cedula=cedula, banco=banco, tipo_cuenta=tipo_cuenta, numero_cuenta=numero_cuenta,
                tipo_servicio=_tipo_servicio_sugerido(g.persona_ref),   # sugerencia; editable
                auto=True,
            )


# ---------------------------------------------------------------- Reporte de pagos

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_reporte_pago(request):
    """Pagos por ?fecha=YYYY-MM-DD&turno=Diurno|Nocturno. Sincroniza desde guardia."""
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    if fecha and turno in TURNOS:
        _sync_pagos(fecha, turno)
    qs = ReportePago.objects.select_related('persona_ref')
    if fecha:
        qs = qs.filter(fecha=fecha)
    if turno in TURNOS:
        qs = qs.filter(turno=turno)
    return Response(ReportePagoSerializer(qs, many=True).data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def actualizar_reporte_pago(request, id):
    """Actualiza tipo_servicio/horas/valor_total/referencia. Recalcula valor_calculado.
    El valor definitivo se refleja en el 'valor' de la fila de Reporte de Guardia."""
    p = get_object_or_404(ReportePago, id=id)
    s = ReportePagoSerializer(p, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    p = s.save()
    nuevo = _calcular_valor(p.tipo_servicio, p.horas)
    if p.valor_calculado != nuevo:
        p.valor_calculado = nuevo
        p.save(update_fields=['valor_calculado'])
    # Valor definitivo (total si > 0, si no el calculado) -> 'valor' de la fila de guardia.
    if p.reporte_guardia_ref_id:
        efectivo = p.valor_total if (p.valor_total or 0) > 0 else p.valor_calculado
        ReporteGuardia.objects.filter(id=p.reporte_guardia_ref_id).update(valor=efectivo or 0)
    return Response(ReportePagoSerializer(p).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumen_mensual_reporte_pago(request):
    """Resumen del mes (?mes=&anio=): total general, total por tipo de servicio y
    total por persona. Suma el valor DEFINITIVO (valor_total si > 0, si no el
    valor_calculado). Antes de sumar, sincroniza los pagos de cada fecha/turno del
    mes que tenga guardia pagable, para que el total esté completo aunque no se haya
    abierto cada día en la vista diaria."""
    try:
        mes = int(request.GET.get('mes'))
        anio = int(request.GET.get('anio'))
        if not (1 <= mes <= 12):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'mes/anio inválidos'}, status=status.HTTP_400_BAD_REQUEST)

    # Asegurar que existan los pagos del mes.
    fechas_turnos = ReporteGuardia.objects.filter(
        fecha__year=anio, fecha__month=mes, seccion__in=SECCIONES_PAGABLES
    ).values_list('fecha', 'turno').distinct()
    for fecha, turno in fechas_turnos:
        if fecha and turno in TURNOS:
            _sync_pagos(fecha, turno)

    efectivo = Case(
        When(valor_total__gt=0, then=F('valor_total')),
        default=F('valor_calculado'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    qs = ReportePago.objects.filter(fecha__year=anio, fecha__month=mes)
    # Filtro opcional por un tipo de servicio específico.
    tipo_filtro = (request.GET.get('tipo_servicio') or '').strip()
    if tipo_filtro:
        qs = qs.filter(tipo_servicio=tipo_filtro)
    qs = qs.annotate(_efectivo=efectivo)

    por_tipo = [
        {'tipo_servicio': (r['tipo_servicio'] or '(sin tipo)'), 'total': float(r['total'] or 0)}
        for r in qs.values('tipo_servicio').annotate(total=Sum('_efectivo')).order_by('-total')
    ]
    por_persona = [
        {
            'persona_id': r['persona_ref_id'],
            'persona_nombre': r['persona_nombre'] or '',
            'cedula': r['cedula'] or '',
            'total': float(r['total'] or 0),
        }
        for r in qs.values('persona_ref_id', 'persona_nombre', 'cedula')
                   .annotate(total=Sum('_efectivo')).order_by('persona_nombre')
    ]
    total_general = float(qs.aggregate(t=Sum('_efectivo'))['t'] or 0)

    return Response({
        'mes': mes, 'anio': anio,
        'total_general': total_general,
        'por_tipo_servicio': por_tipo,
        'por_persona': por_persona,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_persona_mes_reporte_pago(request):
    """Pagos de UNA persona en el mes (?mes=&anio=&persona_id=), para el desglose
    del resumen mensual. Devuelve las filas de ReportePago ordenadas por fecha/turno."""
    try:
        mes = int(request.GET.get('mes'))
        anio = int(request.GET.get('anio'))
        persona_id = int(request.GET.get('persona_id'))
        if not (1 <= mes <= 12):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'mes/anio/persona_id inválidos'}, status=status.HTTP_400_BAD_REQUEST)

    qs = ReportePago.objects.select_related('persona_ref').filter(
        fecha__year=anio, fecha__month=mes, persona_ref_id=persona_id
    )
    tipo_filtro = (request.GET.get('tipo_servicio') or '').strip()
    if tipo_filtro:
        qs = qs.filter(tipo_servicio=tipo_filtro)
    qs = qs.order_by('fecha', 'turno')
    return Response(ReportePagoSerializer(qs, many=True).data)


# ---------------------------------------------------------------- Tarifas (editor)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_tarifas(request):
    return Response(TarifaPagoSerializer(TarifaPago.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_tipos_servicio(request):
    """Tipos de servicio distintos (para el desplegable), en orden."""
    tipos = []
    for t in TarifaPago.objects.order_by('orden', 'tipo_servicio').values_list('tipo_servicio', flat=True):
        if t not in tipos:
            tipos.append(t)
    return Response(tipos)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_tarifa(request):
    s = TarifaPagoSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def actualizar_tarifa(request, id):
    t = get_object_or_404(TarifaPago, id=id)
    s = TarifaPagoSerializer(t, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_tarifa(request, id):
    get_object_or_404(TarifaPago, id=id).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
