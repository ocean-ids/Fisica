"""Servicios Adicionales: formulario FR-REPORTE DE PUESTO ADICIONAL.

Cada registro es un pedido de guardias adicionales para un cliente: C (cantidad de guardias), H (horas), Horario
(ingreso y salida), Solicitado por, Recibido por, Medio y Precio. Se llena desde la asistencia (al guardar una
fila como ADICIONAL se abre el formulario ya prellenado con el cliente y el horario de ese registro) o con
"Nuevo registro" en el módulo.

Permisos: ver = view_servicioadicional; crear = add_servicioadicional; editar = change_servicioadicional;
el PRECIO solo lo pone quien tiene editar_precio_servicioadicional (Consola no lo pone).
"""
import datetime
import unicodedata
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Asignacion, Cliente, Instalacion, SacafrancoFila, ServicioAdicional

VER = 'CoreFisica.view_servicioadicional'
CREAR = 'CoreFisica.add_servicioadicional'
EDITAR = 'CoreFisica.change_servicioadicional'
PRECIO = 'CoreFisica.editar_precio_servicioadicional'
MAX_DIAS = 366   # rango máximo que se puede pedir de una vez

# Encabezado del formato FR (como la hoja impresa).
FR_TITULO = 'FR-REPORTE DE PUESTO ADICIONAL'
FR_VERSION = '.03'
FR_FECHA_APROBACION = ''
_DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
          'noviembre', 'diciembre']


def _fecha(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _hora(v):
    """'07:00' / '7:30' -> time; vacío -> None; inválido -> False."""
    v = str(v or '').strip()
    if not v:
        return None
    try:
        h, m = v.split(':')[:2]
        return datetime.time(int(h), int(m))
    except (ValueError, TypeError):
        return False


def _decimal(v, defecto=None):
    if v in (None, ''):
        return defecto
    try:
        return Decimal(str(v).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return False


def _norm(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _nombre_usuario(u):
    if not u:
        return ''
    return f"{u.first_name} {u.last_name}".strip() or u.get_username()


def _cliente_texto(sa):
    """Columna CLIENTE del formato: la instalación (donde se pone el adicional) o, si no hay, el cliente."""
    if sa.instalacion_id and sa.instalacion:
        return sa.instalacion.nombre or ''
    return (getattr(sa.cliente, 'nombre_comercial', '') or '') if sa.cliente_id else ''


def _hhmm(t):
    return t.strftime('%H:%M') if t else ''


def _horario(sa):
    return f"{_hhmm(sa.hora_ingreso)} - {_hhmm(sa.hora_salida)}" if (sa.hora_ingreso or sa.hora_salida) else ''


def _serializar(sa):
    return {
        'id': sa.id,
        'fecha': sa.fecha.isoformat(),
        'turno': sa.turno,
        'cliente_id': sa.cliente_id,
        'cliente': (getattr(sa.cliente, 'nombre_comercial', '') or '') if sa.cliente_id else '',
        'instalacion_id': sa.instalacion_id,
        'instalacion': (getattr(sa.instalacion, 'nombre', '') or '') if sa.instalacion_id else '',
        'cliente_texto': _cliente_texto(sa),
        'cantidad': sa.cantidad,
        'horas': float(sa.horas or 0),
        'hora_ingreso': _hhmm(sa.hora_ingreso),
        'hora_salida': _hhmm(sa.hora_salida),
        'horario': _horario(sa),
        'solicitado_por': sa.solicitado_por,
        'recibido_por': sa.recibido_por,
        'medio': sa.medio,
        'precio': float(sa.precio) if sa.precio is not None else None,
        'asignacion_id': sa.asignacion_id,
        'sacafranco_fila_id': sa.sacafranco_fila_id,
        'creado_por': _nombre_usuario(sa.creado_por),
        'modificado_por': _nombre_usuario(sa.modificado_por),
        'modificado_en': sa.modificado_en.isoformat() if sa.modificado_en else None,
    }


_SELECT = ('cliente', 'instalacion', 'creado_por', 'modificado_por')


def _rango(request):
    """(desde, hasta, error) a partir de ?desde=&hasta= (o ?fecha=)."""
    fecha = _fecha(request.GET.get('fecha'))
    desde = _fecha(request.GET.get('desde')) or fecha
    hasta = _fecha(request.GET.get('hasta')) or fecha or desde
    if not desde or not hasta:
        return None, None, 'Indica la fecha o el rango (desde / hasta).'
    if hasta < desde:
        desde, hasta = hasta, desde
    if (hasta - desde).days > MAX_DIAS:
        return None, None, f'El rango no puede pasar de {MAX_DIAS} días.'
    return desde, hasta, None


def _filas(request):
    """(filas serializadas, desde, error). Filtros: fechas, ?turno=Diurno|Nocturno (sin turno = ambos) y ?q=."""
    desde, hasta, error = _rango(request)
    if error:
        return None, None, error
    qs = ServicioAdicional.objects.select_related(*_SELECT).filter(fecha__gte=desde, fecha__lte=hasta)
    turno = request.GET.get('turno')
    if turno in ('Diurno', 'Nocturno'):
        qs = qs.filter(turno=turno)
    filas = [_serializar(sa) for sa in qs.order_by('fecha', 'turno', 'id')]
    tokens = _norm(request.GET.get('q')).split()
    if tokens:
        claves = ('cliente_texto', 'cliente', 'solicitado_por', 'recibido_por', 'medio', 'horario')
        filas = [f for f in filas
                 if all(t in _norm(' '.join(str(f.get(k) or '') for k in claves)) for t in tokens)]
    return filas, desde, None


def _aplicar(sa, data, user):
    """Copia los datos del formulario al registro. Devuelve un mensaje de error o None."""
    if 'fecha' in data:
        f = _fecha(data.get('fecha'))
        if not f:
            return 'Fecha inválida.'
        sa.fecha = f
    if 'turno' in data:
        if data.get('turno') not in ('Diurno', 'Nocturno'):
            return 'El turno debe ser Diurno o Nocturno.'
        sa.turno = data.get('turno')
    if 'instalacion_id' in data:
        iid = data.get('instalacion_id')
        sa.instalacion = Instalacion.objects.select_related('cliente').filter(id=iid).first() if iid else None
        if sa.instalacion and not data.get('cliente_id'):
            sa.cliente = sa.instalacion.cliente
    if 'cliente_id' in data and data.get('cliente_id'):
        sa.cliente = Cliente.objects.filter(id=data.get('cliente_id')).first()
    if not sa.cliente_id and not sa.instalacion_id:
        return 'Elige el cliente.'
    if 'cantidad' in data:
        try:
            c = int(data.get('cantidad'))
        except (TypeError, ValueError):
            return 'La cantidad de guardias (C) debe ser un número.'
        if c < 1:
            return 'La cantidad de guardias (C) debe ser al menos 1.'
        sa.cantidad = c
    if 'horas' in data:
        h = _decimal(data.get('horas'), Decimal(0))
        if h is False or h < 0 or h > 48:
            return 'Las horas (H) deben estar entre 0 y 48.'
        sa.horas = h
    for campo in ('hora_ingreso', 'hora_salida'):
        if campo in data:
            t = _hora(data.get(campo))
            if t is False:
                return 'La hora de ingreso y de salida deben tener el formato HH:MM.'
            setattr(sa, campo, t)
    for campo in ('solicitado_por', 'recibido_por', 'medio'):
        if campo in data:
            setattr(sa, campo, str(data.get(campo) or '').strip().upper()[:150])
    # PRECIO: solo con su permiso (Consola no lo pone). Sin permiso, se ignora.
    if 'precio' in data and user.has_perm(PRECIO):
        p = _decimal(data.get('precio'))
        if p is False or (p is not None and p < 0):
            return 'Precio inválido.'
        sa.precio = p
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_servicios_adicionales(request):
    if not request.user.has_perm(VER):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    filas, _desde, error = _filas(request)
    if error:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    return Response(filas)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def catalogo_servicios_adicionales(request):
    """Clientes e instalaciones activas para el formulario."""
    u = request.user
    if not (u.has_perm(VER) or u.has_perm(CREAR) or u.has_perm(EDITAR)):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    clientes = [{'id': c.id, 'nombre': c.nombre_comercial or c.razon_social or ''}
                for c in Cliente.objects.order_by('nombre_comercial')]
    instalaciones = [{'id': i.id, 'nombre': i.nombre or '', 'cliente_id': i.cliente_id, 'codigo': i.codigo or ''}
                     for i in Instalacion.objects.filter(activo=True).order_by('nombre')]
    return Response({'clientes': clientes, 'instalaciones': instalaciones, 'puede_precio': u.has_perm(PRECIO)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prellenar_servicio_adicional(request):
    """Datos para abrir el formulario desde la asistencia: el registro que ya existe para esa fila, fecha y turno,
    o los datos por defecto (cliente e instalación de esa fila). ?fecha=&turno=&asignacion_id= | sacafranco_fila_id="""
    if not (request.user.has_perm(CREAR) or request.user.has_perm(EDITAR)):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    fecha = _fecha(request.GET.get('fecha'))
    turno = request.GET.get('turno') if request.GET.get('turno') in ('Diurno', 'Nocturno') else 'Diurno'
    if not fecha:
        return Response({'error': 'Fecha inválida.'}, status=status.HTTP_400_BAD_REQUEST)
    asig_id = request.GET.get('asignacion_id') or None
    saca_id = request.GET.get('sacafranco_fila_id') or None
    origen = {'asignacion_id': asig_id} if asig_id else ({'sacafranco_fila_id': saca_id} if saca_id else None)
    if not origen:
        return Response({'error': 'Falta la fila de la asistencia.'}, status=status.HTTP_400_BAD_REQUEST)
    existente = (ServicioAdicional.objects.select_related(*_SELECT)
                 .filter(fecha=fecha, turno=turno, **origen).order_by('-id').first())
    if existente:
        return Response({'existe': True, 'registro': _serializar(existente)})
    cliente_id = instalacion_id = None
    if asig_id:
        a = Asignacion.objects.filter(id=asig_id).values('cliente_id', 'instalacion_id').first()
        if a:
            cliente_id, instalacion_id = a['cliente_id'], a['instalacion_id']
    else:
        from .reporte_asistencia_views import _sacafranco_token_for_date
        from .asignacion_semanal_views import _parse_sacafranco_token
        if SacafrancoFila.objects.filter(id=saca_id).exists():
            code = _parse_sacafranco_token(_sacafranco_token_for_date(int(saca_id), fecha))[2]
            inst = Instalacion.objects.filter(codigo__iexact=code).first() if code and code != 'BASE' else None
            if inst:
                cliente_id, instalacion_id = inst.cliente_id, inst.id
    return Response({'existe': False, 'registro': {
        'fecha': fecha.isoformat(), 'turno': turno, 'cliente_id': cliente_id, 'instalacion_id': instalacion_id,
        'cantidad': 1, 'asignacion_id': int(asig_id) if asig_id else None,
        'sacafranco_fila_id': int(saca_id) if saca_id else None,
        'recibido_por': _nombre_usuario(request.user).upper(),
    }})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_servicio_adicional(request):
    if not request.user.has_perm(CREAR):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    data = request.data
    if not data.get('fecha') or not data.get('turno'):
        return Response({'error': 'Falta la fecha o el turno.'}, status=status.HTTP_400_BAD_REQUEST)
    sa = ServicioAdicional(creado_por=request.user, modificado_por=request.user)
    if data.get('asignacion_id'):
        sa.asignacion = Asignacion.objects.filter(id=data.get('asignacion_id')).first()
    elif data.get('sacafranco_fila_id'):
        sa.sacafranco_fila = SacafrancoFila.objects.filter(id=data.get('sacafranco_fila_id')).first()
    error = _aplicar(sa, data, request.user)
    if error:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    # Una fila de la asistencia tiene UN servicio adicional por fecha y turno: si ya existe, no se duplica.
    origen = ({'asignacion_id': sa.asignacion_id} if sa.asignacion_id
              else ({'sacafranco_fila_id': sa.sacafranco_fila_id} if sa.sacafranco_fila_id else None))
    if origen and ServicioAdicional.objects.filter(fecha=sa.fecha, turno=sa.turno, **origen).exists():
        return Response({'error': 'Esta fila ya tiene su servicio adicional en esa fecha y turno; edítalo.'},
                        status=status.HTTP_409_CONFLICT)
    sa.save()
    return Response(_serializar(sa), status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def actualizar_servicio_adicional(request, id):
    # Quien solo tiene el permiso del PRECIO también puede guardar (solo cambia el precio).
    puede_editar = request.user.has_perm(EDITAR)
    if not (puede_editar or request.user.has_perm(PRECIO)):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    sa = ServicioAdicional.objects.select_related(*_SELECT).filter(id=id).first()
    if not sa:
        return Response({'error': 'No encontrado'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data if puede_editar else {k: v for k, v in request.data.items() if k == 'precio'}
    error = _aplicar(sa, data, request.user)
    if error:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    sa.modificado_por = request.user
    sa.save()
    return Response(_serializar(sa))


def _fecha_larga(f):
    return f"{_DIAS[f.weekday()]}, {f.day} de {_MESES[f.month - 1]} de {f.year}"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_servicios_adicionales_excel(request):
    """Excel en el formato FR-REPORTE DE PUESTO ADICIONAL: una pestaña por día, con el TURNO DIURNO y el TURNO
    NOCTURNO (Cliente, C, H, Horario, Solicitado por, Recibido por, Medio, Precio) y las firmas. Respeta las fechas
    y la búsqueda (?q=)."""
    if not request.user.has_perm(VER):
        return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from .reporte_asistencia_views import _find_logo_path

    filas, desde, error = _filas(request)
    if error:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    por_dia = {}
    for f in filas:
        por_dia.setdefault(f['fecha'], []).append(f)
    # Sin registros: la hoja del primer día, vacía (para llenarla a mano). Con registros: un día por pestaña.
    dias = sorted(por_dia) or [desde.isoformat()]

    delgado = Side(style='thin', color='000000')
    borde = Border(left=delgado, right=delgado, top=delgado, bottom=delgado)
    centro = Alignment(horizontal='center', vertical='center', wrap_text=True)
    negrita = Font(bold=True)
    gris = PatternFill('solid', fgColor='D9D9D9')
    anchos = {1: 46, 2: 6, 3: 6, 4: 16, 5: 26, 6: 26, 7: 16, 8: 12}
    encabezados = ['CLIENTE', 'C', 'H', 'HORARIO', 'SOLICITADO POR', 'RECIBIDO POR', 'MEDIO', 'PRECIO']
    min_filas = 10    # renglones por turno, como la hoja impresa (los vacíos sirven para llenar a mano)
    logo = _find_logo_path()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for dia in dias:
        f_dia = datetime.date.fromisoformat(dia)
        ws = wb.create_sheet(f_dia.strftime('%d-%m-%Y'))
        for c, w in anchos.items():
            ws.column_dimensions[get_column_letter(c)].width = w
        # Encabezado: logo (A), título (B:F), versión y fecha de aprobación (G:H).
        for r in range(1, 4):
            ws.row_dimensions[r].height = 20
        ws.merge_cells('A1:A3')
        ws.merge_cells('B1:F3')
        t = ws.cell(1, 2, FR_TITULO)
        t.font = Font(bold=True, size=14)
        t.alignment = centro
        ws.cell(1, 7, 'Versión:')
        ws.cell(1, 8, FR_VERSION)
        ws.merge_cells('G2:G3')
        ws.merge_cells('H2:H3')
        ws.cell(2, 7, 'Fecha de aprobación:')
        ws.cell(2, 8, FR_FECHA_APROBACION)
        for r in range(1, 4):
            for c in range(1, 9):
                ws.cell(r, c).border = borde
                if c >= 7:
                    ws.cell(r, c).alignment = centro
        if logo:
            try:
                from openpyxl.drawing.image import Image as XLImage
                img = XLImage(str(logo))
                img.width, img.height = 130, 47
                ws.add_image(img, 'A1')
            except Exception:
                pass
        ws.cell(5, 1, 'FECHA:').font = negrita
        ws.merge_cells('B5:H5')
        ws.cell(5, 2, _fecha_larga(f_dia)).alignment = centro
        fila = 7
        for turno in ('Diurno', 'Nocturno'):
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=8)
            ws.cell(fila, 1, f'TURNO {turno.upper()}').font = negrita
            fila += 1
            for c, titulo in enumerate(encabezados, start=1):
                cell = ws.cell(fila, c, titulo)
                cell.font = negrita
                cell.fill = gris
                cell.alignment = centro
                cell.border = borde
            fila += 1
            regs = [r for r in por_dia.get(dia, []) if r['turno'] == turno]
            for i in range(max(min_filas, len(regs))):
                r = regs[i] if i < len(regs) else None
                valores = ([r['cliente_texto'], r['cantidad'], r['horas'], r['horario'], r['solicitado_por'],
                            r['recibido_por'], r['medio'], r['precio']] if r else [''] * 8)
                for c, v in enumerate(valores, start=1):
                    cell = ws.cell(fila, c, v)
                    cell.border = borde
                    cell.alignment = Alignment(horizontal='left' if c == 1 else 'center', vertical='center',
                                               wrap_text=True)
                    if c == 8 and v not in ('', None):
                        cell.number_format = '#,##0.00'
                fila += 1
            fila += 1
        fila += 1
        for col, texto in ((1, 'ELABORA:'), (5, 'REVISA:'), (7, 'AUTORIZA:')):
            ws.cell(fila, col, texto).font = negrita
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
    out = BytesIO()
    wb.save(out)
    resp = HttpResponse(out.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="servicios_adicionales.xlsx"'
    return resp
