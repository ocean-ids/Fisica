"""Módulo EVENTUALES: horas trabajadas por eventuales en un cliente/instalación/puesto.

- Solo se registran personas de tipo EVENTUAL.
- El banco es de solo lectura: sale de los datos de la persona (EmpleadoOtrosDatos). Si la
  persona no lo tiene cargado, se muestra vacío.
- Horas adicionales = horas trabajadas - horas solicitadas (mínimo 0), calculadas al guardar.
- Rango de horas: tramo de la tarifa "Eventuales" (Tarifas de Pago) que incluye las HORAS
  TRABAJADAS; se marca solo y el usuario lo puede cambiar.
- Valor calculado: por defecto, valor del rango + bonificación. Se puede corregir a mano.
- Bonificación: monto opcional (el bono que se le quiera dar).
"""
import datetime
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import HorasEventual, HorasEventualHistorial, Persona, Cliente, Instalacion, Puesto, TarifaPago

# Tipo de servicio de Tarifas de Pago con el que se valoran las horas adicionales.
TIPO_SERVICIO_EVENTUAL = 'Eventuales'


def _banco(persona):
    """Banco de la persona (EmpleadoOtrosDatos); vacío si no lo tiene."""
    try:
        return (persona.otros_datos.banco or '') if persona else ''
    except Exception:
        return ''


def _tarifas_eventual():
    return TarifaPago.objects.filter(tipo_servicio__iexact=TIPO_SERVICIO_EVENTUAL).order_by('horas_min')


def _tramo_por_horas(horas):
    """Tramo (TarifaPago) de la tarifa "Eventuales" que incluye esas horas; None si no hay."""
    if not horas:
        return None
    return _tarifas_eventual().filter(horas_min__lte=horas, horas_max__gte=horas).first()


def _rango_txt(t):
    return f"{t.horas_min}-{t.horas_max} h" if t else ''


def _horas_tarifa(solicitadas, trabajadas):
    """Horas con las que se busca el tramo de la tarifa: las HORAS TRABAJADAS
    (ej. 11 trabajadas -> tramo 10-12; 8 trabajadas -> tramo 7-9)."""
    return trabajadas or 0


def _decimal(v):
    """Decimal con 2 decimales (acepta coma). Vacío -> None; inválido -> excepción."""
    if v in (None, '', 'null'):
        return None
    return Decimal(str(v).replace(',', '.')).quantize(Decimal('0.01'))


def _nombre_usuario(u):
    """Nombre completo del usuario (o su username)."""
    if not u:
        return ''
    return (f"{u.first_name or ''} {u.last_name or ''}".strip()) or u.get_username()


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
        'horas_solicitadas': h.horas_solicitadas or 0,
        'horas': h.horas,
        'horas_adicionales': h.horas_adicionales or 0,
        'rango_horas': h.rango_horas or '',
        'valor_calculado': float(h.valor_calculado or 0),
        'valor_manual': bool(h.valor_manual),
        'bonificacion': float(h.bonificacion) if h.bonificacion is not None else None,
        # Auditoría: quién lo creó y quién lo modificó por última vez.
        'creado_por': _nombre_usuario(h.creado_por),
        'creado_en': h.creado_en.isoformat() if h.creado_en else None,
        'modificado_por': _nombre_usuario(h.modificado_por or h.creado_por),
        'modificado_en': h.actualizado_en.isoformat() if h.actualizado_en else None,
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

    solicitadas = _entero(data.get('horas_solicitadas'))
    if solicitadas is None or solicitadas < 0 or solicitadas > 24:
        return None, 'Las horas solicitadas deben ser un número entero de 0 a 24.'
    horas = _entero(data.get('horas'))
    if horas is None or horas < 1 or horas > 24:
        return None, 'Las horas trabajadas deben ser un número entero de 1 a 24.'
    # Horas adicionales: se calculan (no se aceptan del formulario).
    adicionales = max(0, horas - solicitadas)

    # Bonificación: opcional.
    try:
        bonificacion = _decimal(data.get('bonificacion'))
    except Exception:
        return None, 'La bonificación no es válida.'
    if bonificacion is not None and bonificacion < 0:
        return None, 'La bonificación no puede ser negativa.'

    # Rango de horas (tramo de la tarifa): el elegido en el formulario; si no viene, se marca
    # solo según las horas trabajadas.
    tarifa_id = _int(data.get('tarifa_id'))
    if tarifa_id:
        tramo = _tarifas_eventual().filter(id=tarifa_id).first()
        if not tramo:
            return None, 'El rango de horas no es válido.'
    else:
        tramo = _tramo_por_horas(_horas_tarifa(solicitadas, horas))

    # Valor calculado: por defecto = valor del rango + bonificación. Si el usuario lo corrigió
    # a mano (valor_manual), se guarda lo que escribió.
    manual = str(data.get('valor_manual')).strip().lower() in ('1', 'true', 'si', 'yes', 'on')
    try:
        valor = _decimal(data.get('valor_calculado'))
    except Exception:
        return None, 'El valor calculado no es válido.'
    if not manual or valor is None:
        manual = False
        valor = (tramo.valor if tramo else Decimal('0')) + (bonificacion or Decimal('0'))
    if valor < 0:
        return None, 'El valor calculado no puede ser negativo.'

    return {
        'fecha': fecha, 'persona': persona, 'cliente': cliente,
        'instalacion': instalacion, 'puesto': puesto,
        'horas_solicitadas': solicitadas, 'horas': horas, 'horas_adicionales': adicionales,
        'rango_horas': _rango_txt(tramo),
        'valor_calculado': valor, 'valor_manual': manual, 'bonificacion': bonificacion,
    }, None


_SELECT = ('persona', 'persona__otros_datos', 'cliente', 'instalacion', 'puesto',
           'creado_por', 'modificado_por')


def _guardar_historial(h, accion, user):
    """Copia de los valores del registro en este momento (para el historial)."""
    HorasEventualHistorial.objects.create(
        registro=h,
        accion=accion,
        usuario=user if (user and user.is_authenticated) else None,
        usuario_nombre=_nombre_usuario(user) if (user and user.is_authenticated) else 'sistema',
        fecha_servicio=h.fecha,
        persona=_nombre_persona(h.persona),
        cliente=getattr(h.cliente, 'nombre_comercial', '') or '',
        instalacion=getattr(h.instalacion, 'nombre', '') or '',
        puesto=getattr(h.puesto, 'nombre', '') or '',
        horas_solicitadas=h.horas_solicitadas,
        horas=h.horas,
        horas_adicionales=h.horas_adicionales,
        rango_horas=h.rango_horas,
        valor_calculado=h.valor_calculado,
        bonificacion=h.bonificacion,
    )


# Campos que se comparan entre versiones para mostrar "qué cambió".
_CAMPOS_HISTORIAL = [
    ('fecha_servicio', 'Fecha del servicio'),
    ('cliente', 'Cliente'),
    ('instalacion', 'Instalación'),
    ('puesto', 'Nombre del puesto'),
    ('persona', 'Eventual'),
    ('horas_solicitadas', 'Horas solicitadas'),
    ('horas', 'Horas trabajadas'),
    ('horas_adicionales', 'Horas adicionales'),
    ('rango_horas', 'Rango de horas'),
    ('valor_calculado', 'Valor calculado'),
    ('bonificacion', 'Bonificación'),
]


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
        {'id': p.id, 'nombre': _nombre_persona(p), 'cedula': p.cedula or '', 'banco': _banco(p),
         'tipo': p.tipo or ''}
        for p in (Persona.objects.filter(tipo='EVENTUAL', is_active=True)
                  .select_related('otros_datos').order_by('apellidos', 'nombres'))
    ]
    # Tramos de la tarifa "Eventuales": el formulario propone el valor mientras se escribe.
    tarifas = [
        {'id': t.id, 'horas_min': t.horas_min, 'horas_max': t.horas_max, 'valor': float(t.valor)}
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
    h = HorasEventual.objects.create(creado_por=request.user, modificado_por=request.user, **campos)
    h = HorasEventual.objects.select_related(*_SELECT).get(id=h.id)
    _guardar_historial(h, 'CREADO', request.user)
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
    h.modificado_por = request.user
    h.save()
    h = HorasEventual.objects.select_related(*_SELECT).get(id=h.id)
    _guardar_historial(h, 'MODIFICADO', request.user)
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_horas_eventual(request, id):
    """Historial del registro: quién lo creó y quién lo modificó, con los valores de cada
    versión y qué campos cambiaron respecto a la anterior. Más reciente primero."""
    if not request.user.has_perm('CoreFisica.view_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    if not HorasEventual.objects.filter(id=id).exists():
        return Response({'error': 'Registro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    versiones = list(HorasEventualHistorial.objects.filter(registro_id=id).select_related('usuario'))
    out = []
    anterior = None
    for v in versiones:
        cambios = []
        if anterior is not None:
            cambios = [label for campo, label in _CAMPOS_HISTORIAL
                       if getattr(v, campo) != getattr(anterior, campo)]
        out.append({
            'id': v.id,
            'accion': v.accion,
            'accion_label': v.get_accion_display(),
            'usuario': _nombre_usuario(v.usuario) or v.usuario_nombre,
            'fecha_hora': v.creado_en.isoformat() if v.creado_en else None,
            'fecha_servicio': v.fecha_servicio.isoformat() if v.fecha_servicio else None,
            'persona': v.persona,
            'cliente': v.cliente,
            'instalacion': v.instalacion,
            'puesto': v.puesto,
            'horas_solicitadas': v.horas_solicitadas,
            'horas': v.horas,
            'horas_adicionales': v.horas_adicionales,
            'rango_horas': v.rango_horas or '',
            'valor_calculado': float(v.valor_calculado) if v.valor_calculado is not None else None,
            'bonificacion': float(v.bonificacion) if v.bonificacion is not None else None,
            'cambios': cambios,
        })
        anterior = v
    out.reverse()
    return Response(out)
