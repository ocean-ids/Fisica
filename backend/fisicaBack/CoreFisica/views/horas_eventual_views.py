"""Módulo EVENTUALES: horas trabajadas por eventuales en un cliente/instalación/puesto.

- Solo se registran personas de tipo EVENTUAL.
- El banco es de solo lectura: sale de los datos de la persona (EmpleadoOtrosDatos). Si la
  persona no lo tiene cargado, se muestra vacío.
- Valor calculado: tarifa "Eventuales" (módulo Tarifas de Pago) del tramo que incluye
  horas trabajadas + horas adicionales. Sin tramo para esas horas -> 0.
"""
import datetime
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import HorasEventual, Persona, Cliente, Instalacion, Puesto, TarifaPago

# Tipo de servicio de Tarifas de Pago con el que se valoran las horas de eventuales.
TIPO_SERVICIO_EVENTUAL = 'Eventuales'


def _banco(persona):
    """Banco de la persona (EmpleadoOtrosDatos); vacío si no lo tiene."""
    try:
        return (persona.otros_datos.banco or '') if persona else ''
    except Exception:
        return ''


def _tarifas_eventual():
    return TarifaPago.objects.filter(tipo_servicio__iexact=TIPO_SERVICIO_EVENTUAL).order_by('horas_min')


def _valor_calculado(horas_totales):
    """Valor del tramo de la tarifa "Eventuales" que incluye las horas; 0 si no hay tramo."""
    if not horas_totales:
        return Decimal('0')
    t = _tarifas_eventual().filter(horas_min__lte=horas_totales, horas_max__gte=horas_totales).first()
    return t.valor if t else Decimal('0')


def _nombre_persona(p):
    return f"{p.apellidos or ''} {p.nombres or ''}".strip() if p else ''


def _serialize(h):
    return {
        'id': h.id,
        'fecha': h.fecha.isoformat() if h.fecha else None,
        'persona_id': h.persona_id,
        'persona': _nombre_persona(h.persona),
        'cedula': getattr(h.persona, 'cedula', '') or '',
        'banco': _banco(h.persona),
        'cliente_id': h.cliente_id,
        'cliente': getattr(h.cliente, 'nombre_comercial', '') or '',
        'instalacion_id': h.instalacion_id,
        'instalacion': getattr(h.instalacion, 'nombre', '') or '',
        'puesto_id': h.puesto_id,
        'puesto': getattr(h.puesto, 'nombre', '') or '',
        'horas': h.horas,
        'horas_adicionales': h.horas_adicionales or 0,
        'valor_calculado': float(h.valor_calculado or 0),
    }


def _parse_fecha(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10]) if v else None
    except (TypeError, ValueError):
        return None


def _int(v):
    try:
        return int(v) if v not in (None, '', 'null') else None
    except (TypeError, ValueError):
        return None


def _entero(v):
    """Entero estricto (7 o '7' sí; 7.5 no). Vacío -> None."""
    if v in (None, '', 'null'):
        return None
    try:
        f = float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None


def _validar(data):
    """Valida y resuelve los datos del registro. Devuelve (campos, error)."""
    fecha = _parse_fecha(data.get('fecha'))
    if not fecha:
        return None, 'La fecha es obligatoria.'

    persona = Persona.objects.filter(id=_int(data.get('persona_id'))).first()
    if not persona:
        return None, 'Selecciona el eventual.'
    if (persona.tipo or '').upper() != 'EVENTUAL':
        return None, 'La persona seleccionada no es EVENTUAL.'

    cliente = Cliente.objects.filter(id=_int(data.get('cliente_id'))).first()
    if not cliente:
        return None, 'Selecciona el cliente.'

    instalacion = Instalacion.objects.filter(id=_int(data.get('instalacion_id'))).first()
    if not instalacion:
        return None, 'Selecciona la instalación.'
    if instalacion.cliente_id != cliente.id:
        return None, 'La instalación no pertenece al cliente seleccionado.'

    puesto = None
    puesto_id = _int(data.get('puesto_id'))
    if puesto_id:
        puesto = Puesto.objects.filter(id=puesto_id).first()
        if not puesto:
            return None, 'El puesto no existe.'
        if puesto.instalacion_id != instalacion.id:
            return None, 'El puesto no pertenece a la instalación seleccionada.'

    horas = _entero(data.get('horas'))
    if horas is None or horas < 1 or horas > 24:
        return None, 'Las horas trabajadas deben ser un número entero de 1 a 24.'
    raw_adic = data.get('horas_adicionales')
    adicionales = 0 if raw_adic in (None, '', 'null') else _entero(raw_adic)
    if adicionales is None or adicionales < 0 or adicionales > 24:
        return None, 'Las horas adicionales deben ser un número entero de 0 a 24.'

    return {
        'fecha': fecha, 'persona': persona, 'cliente': cliente,
        'instalacion': instalacion, 'puesto': puesto,
        'horas': horas, 'horas_adicionales': adicionales,
        'valor_calculado': _valor_calculado(horas + adicionales),
    }, None


_SELECT = ('persona', 'persona__otros_datos', 'cliente', 'instalacion', 'puesto')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_horas_eventual(request):
    """Lista de registros. Filtros opcionales: ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD."""
    if not request.user.has_perm('CoreFisica.view_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    qs = HorasEventual.objects.select_related(*_SELECT)
    desde = _parse_fecha(request.GET.get('desde'))
    hasta = _parse_fecha(request.GET.get('hasta'))
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    return Response([_serialize(h) for h in qs])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def catalogo_horas_eventual(request):
    """Datos para los selectores del formulario (se filtran en pantalla al escribir)."""
    if not request.user.has_perm('CoreFisica.view_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    clientes = [
        {'id': c.id, 'nombre': c.nombre_comercial or c.razon_social or ''}
        for c in Cliente.objects.order_by('nombre_comercial')
    ]
    instalaciones = [
        {'id': i.id, 'nombre': i.nombre or '', 'cliente_id': i.cliente_id}
        for i in Instalacion.objects.filter(activo=True).order_by('nombre')
    ]
    puestos = [
        {'id': p.id, 'nombre': p.nombre or '', 'instalacion_id': p.instalacion_id}
        for p in Puesto.objects.filter(activo=True).order_by('nombre')
    ]
    eventuales = [
        {'id': p.id, 'nombre': _nombre_persona(p), 'cedula': p.cedula or '', 'banco': _banco(p)}
        for p in (Persona.objects.filter(tipo='EVENTUAL', is_active=True)
                  .select_related('otros_datos').order_by('apellidos', 'nombres'))
    ]
    # Tramos de la tarifa "Eventuales": el formulario muestra el valor mientras se escribe.
    tarifas = [
        {'horas_min': t.horas_min, 'horas_max': t.horas_max, 'valor': float(t.valor)}
        for t in _tarifas_eventual()
    ]
    return Response({
        'clientes': clientes, 'instalaciones': instalaciones,
        'puestos': puestos, 'eventuales': eventuales, 'tarifas': tarifas,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_horas_eventual(request):
    if not request.user.has_perm('CoreFisica.add_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    campos, err = _validar(request.data)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
    h = HorasEventual.objects.create(creado_por=request.user, **campos)
    h = HorasEventual.objects.select_related(*_SELECT).get(id=h.id)
    return Response(_serialize(h), status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_horas_eventual(request, id):
    if not request.user.has_perm('CoreFisica.change_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    h = HorasEventual.objects.filter(id=id).first()
    if not h:
        return Response({'error': 'Registro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    campos, err = _validar(request.data)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
    for k, v in campos.items():
        setattr(h, k, v)
    h.save()
    h = HorasEventual.objects.select_related(*_SELECT).get(id=h.id)
    return Response(_serialize(h))


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_horas_eventual(request, id):
    if not request.user.has_perm('CoreFisica.delete_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    h = HorasEventual.objects.filter(id=id).first()
    if not h:
        return Response({'error': 'Registro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    h.delete()
    return Response({'ok': True})
