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


def _nombre_cliente(h):
    return (getattr(h.cliente, 'nombre_comercial', '') or '') if h.cliente_id else (h.cliente_texto or '')


def _nombre_instalacion(h):
    return (getattr(h.instalacion, 'nombre', '') or '') if h.instalacion_id else (h.instalacion_texto or '')


def _nombre_puesto(h):
    return (getattr(h.puesto, 'nombre', '') or '') if h.puesto_id else (h.puesto_texto or '')


def _texto(v, largo=200):
    return str(v or '').strip()[:largo]


def _nombre_usuario(u):
    """Nombre completo del usuario (o su username)."""
    if not u:
        return ''
    return (f"{u.first_name or ''} {u.last_name or ''}".strip()) or u.get_username()


def _nombre_persona(p):
    return f"{p.apellidos or ''} {p.nombres or ''}".strip() if p else ''


def _serialize(h):
    banco, tipo_cuenta, numero_cuenta = _cuenta(h.persona) if h.persona else ('', '', '')
    return {
        'id': h.id,
        'fecha': h.fecha.isoformat() if h.fecha else None,
        'persona_id': h.persona_id,
        'persona': _nombre_persona(h.persona),
        'cedula': getattr(h.persona, 'cedula', '') or '',
        'banco': _banco(h.persona),
        # Datos bancarios (mismos nombres que el archivo del banco).
        'banco_codigo': CODIGO_BANCO.get(banco, ''),
        'tipo_cuenta': tipo_cuenta,
        'numero_cuenta': numero_cuenta,
        'cliente_id': h.cliente_id,
        'cliente': _nombre_cliente(h),
        'instalacion_id': h.instalacion_id,
        'instalacion': _nombre_instalacion(h),
        'puesto_id': h.puesto_id,
        'puesto': _nombre_puesto(h),
        # True = escrito a mano (no está en la lista del sistema).
        'cliente_libre': not h.cliente_id and bool(h.cliente_texto),
        'instalacion_libre': not h.instalacion_id and bool(h.instalacion_texto),
        'puesto_libre': not h.puesto_id and bool(h.puesto_texto),
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

    # Cliente: de la lista (cliente_id) o escrito a mano (cliente_texto). No se crea en el sistema.
    cliente, cliente_texto = None, ''
    cliente_id = _int(data.get('cliente_id'))
    if cliente_id:
        cliente = Cliente.objects.filter(id=cliente_id).first()
        if not cliente:
            return None, 'El cliente no existe.'
    else:
        cliente_texto = _texto(data.get('cliente_texto'))
        if not cliente_texto:
            return None, 'Indica el cliente.'

    # Instalación: de la lista (solo si el cliente es de la lista) o escrita a mano.
    instalacion, instalacion_texto = None, ''
    instalacion_id = _int(data.get('instalacion_id'))
    if instalacion_id:
        instalacion = Instalacion.objects.filter(id=instalacion_id).first()
        if not instalacion:
            return None, 'La instalación no existe.'
        if not cliente or instalacion.cliente_id != cliente.id:
            return None, 'La instalación no pertenece al cliente seleccionado.'
    else:
        instalacion_texto = _texto(data.get('instalacion_texto'))
        if not instalacion_texto:
            return None, 'Indica la instalación.'

    # Puesto (obligatorio): de la lista (solo si la instalación es de la lista) o escrito a mano.
    puesto, puesto_texto = None, ''
    puesto_id = _int(data.get('puesto_id'))
    if puesto_id:
        puesto = Puesto.objects.filter(id=puesto_id).first()
        if not puesto:
            return None, 'El puesto no existe.'
        if not instalacion or puesto.instalacion_id != instalacion.id:
            return None, 'El puesto no pertenece a la instalación seleccionada.'
    else:
        puesto_texto = _texto(data.get('puesto_texto'))
        if not puesto_texto:
            return None, 'Indica el nombre del puesto.'

    solicitadas = _entero(data.get('horas_solicitadas'))
    if solicitadas is None or solicitadas < 0 or solicitadas > 24:
        return None, 'Las horas solicitadas deben ser un número entero de 0 a 24.'
    horas = _entero(data.get('horas'))
    if horas is None or horas < 1 or horas > 24:
        return None, 'Las horas trabajadas deben ser un número entero de 1 a 24.'
    # Horas adicionales: las escritas en el formulario; si vienen vacías, trabajadas - solicitadas.
    raw_adic = data.get('horas_adicionales')
    if raw_adic in (None, '', 'null'):
        adicionales = max(0, horas - solicitadas)
    else:
        adicionales = _entero(raw_adic)
        if adicionales is None or adicionales < 0 or adicionales > 24:
            return None, 'Las horas adicionales deben ser un número entero de 0 a 24.'

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
        'fecha': fecha, 'persona': persona,
        'cliente': cliente, 'cliente_texto': cliente_texto,
        'instalacion': instalacion, 'instalacion_texto': instalacion_texto,
        'puesto': puesto, 'puesto_texto': puesto_texto,
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
        cliente=_nombre_cliente(h),
        instalacion=_nombre_instalacion(h),
        puesto=_nombre_puesto(h),
        horas_solicitadas=h.horas_solicitadas,
        horas=h.horas,
        horas_adicionales=h.horas_adicionales,
        rango_horas=h.rango_horas,
        valor_calculado=h.valor_calculado,
        bonificacion=h.bonificacion,
    )


# Campos que se comparan entre versiones para mostrar "qué cambió".
_CAMPOS_HISTORIAL = [
    ('fecha_servicio', 'Creado'),
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
    def _ev(p):
        banco, tipo_cuenta, numero_cuenta = _cuenta(p)
        return {'id': p.id, 'nombre': _nombre_persona(p), 'cedula': p.cedula or '', 'banco': _banco(p),
                'banco_codigo': CODIGO_BANCO.get(banco, ''), 'tipo_cuenta': tipo_cuenta,
                'numero_cuenta': numero_cuenta, 'tipo': p.tipo or ''}
    eventuales = [
        _ev(p)
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


# Código del banco (como en el archivo del banco): 10 PICHINCHA, 17 GUAYAQUIL, 36 PRODUBANCO.
CODIGO_BANCO = {'PICHINCHA': '10', 'GUAYAQUIL': '17', 'PRODUBANCO': '36'}


def _cuenta(persona):
    """(banco, tipo de cuenta, número) de los datos de la persona; vacío si no los tiene."""
    try:
        od = persona.otros_datos
    except Exception:
        return '', '', ''
    numero = (od.numero_cuenta or '').strip()
    tipo = (od.tipo_cuenta or '').strip().upper()
    if not numero and (od.cuenta_ahorros or '').strip():
        numero, tipo = od.cuenta_ahorros.strip(), 'AHORROS'
    elif not numero and (od.cuenta_corriente or '').strip():
        numero, tipo = od.cuenta_corriente.strip(), 'CORRIENTE'
    return (od.banco or '').strip(), tipo, numero


def _norm_busqueda(s):
    import unicodedata
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_excel_horas_eventual(request):
    """Descargable Excel de Eventuales: datos bancarios de cada eventual del día (una fila por
    persona): NombreCompleto, identificacion, Banco (código), TipoCuentaBancaria,
    NumeroCuentaBancaria, BancoNombre y Creado (fecha del servicio).
    Filtros: ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD (o ?fecha=) y ?q= (búsqueda de la pantalla)."""
    if not request.user.has_perm('CoreFisica.view_horaseventual'):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    import io
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse

    fecha = _parse_fecha(request.GET.get('fecha'))
    desde = _parse_fecha(request.GET.get('desde')) or fecha
    hasta = _parse_fecha(request.GET.get('hasta')) or fecha
    qs = HorasEventual.objects.select_related(*_SELECT).order_by('fecha', 'id')
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    registros = list(qs)
    filas = [_serialize(h) for h in registros]

    # Misma búsqueda que la pantalla: cada palabra debe estar en el registro.
    tokens = _norm_busqueda(request.GET.get('q')).split()
    if tokens:
        def _ok(f):
            txt = _norm_busqueda(' '.join(str(f.get(k) or '') for k in
                                          ('persona', 'cedula', 'banco', 'cliente', 'instalacion', 'puesto')))
            return all(t in txt for t in tokens)
        filas = [f for f in filas if _ok(f)]
    ids_ok = {f['id'] for f in filas}

    # Una fila por EVENTUAL (sus datos bancarios), en el orden en que se registraron.
    personas = {}
    for h in registros:
        if h.id in ids_ok and h.persona_id and h.persona_id not in personas:
            personas[h.persona_id] = h
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'EVENTUALES'
    columnas = [
        # Mismos nombres y orden que el archivo del banco.
        ('NombreCompleto', 38), ('identificacion', 14), ('Banco', 8), ('TipoCuentaBancaria', 20),
        ('NumeroCuentaBancaria', 22), ('BancoNombre', 18), ('Creado', 18),
    ]
    borde = Border(*(Side(style='thin', color='999999'),) * 4)
    for c, (titulo, ancho) in enumerate(columnas, start=1):
        cell = ws.cell(1, c, titulo)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E78')
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = borde
        ws.column_dimensions[get_column_letter(c)].width = ancho
    fila = 2
    for h in personas.values():
        banco, tipo, numero = _cuenta(h.persona)
        # Creado = fecha del servicio.
        creado = h.fecha.strftime('%d/%m/%Y') if h.fecha else ''
        valores = [_nombre_persona(h.persona), h.persona.cedula or '', CODIGO_BANCO.get(banco, ''),
                   tipo, numero, banco, creado]
        for c, v in enumerate(valores, start=1):
            cell = ws.cell(fila, c, v)
            cell.border = borde
            # Cédula, código y cuenta como TEXTO (conservan los ceros a la izquierda).
            if c in (2, 3, 5):
                cell.number_format = '@'
        fila += 1
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{max(1, fila - 1)}"

    buf = io.BytesIO()
    wb.save(buf)
    if desde and hasta and desde != hasta:
        nombre = f"EVENTUALES {desde.strftime('%d-%m-%Y')} AL {hasta.strftime('%d-%m-%Y')}.xlsx"
    elif desde or hasta:
        nombre = f"EVENTUALES {(desde or hasta).strftime('%d-%m-%Y')}.xlsx"
    else:
        nombre = 'EVENTUALES.xlsx'
    resp = HttpResponse(buf.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return resp
