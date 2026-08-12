"""Vistas de Instalaciones: CRUD, resolución de provincia/cantón y zonas por instalación."""
import re
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from django.db.models import Q
from ..models import Instalacion, Provincia, Canton, Zona
from ..serializers import InstalacionSerializer
from ..utils import _strip_accents

_NOM_COD_RE = re.compile(r'^([A-Z]{1,3})\s*0*(\d+)$')


def codigo_conflicto_cliente(codigo, cliente_id, excluir_instalacion_id=None):
    """Devuelve un mensaje si el codigo (letra+numero) ya pertenece a un nominativo de
    OTRO cliente. Sirve para BLOQUEAR el guardado de la instalacion (no se debe poner el
    codigo de un cliente en una instalacion de otro cliente). Si no hay conflicto, None.
    """
    from ..models import Nominativo
    m = _NOM_COD_RE.match(str(codigo or '').strip().upper())
    if not m or not cliente_id:
        return None
    letra, numero = m.group(1), int(m.group(2))
    qs = Nominativo.objects.filter(letra=letra, numero=numero).select_related('instalacion', 'instalacion__cliente', 'zona')
    if excluir_instalacion_id:
        qs = qs.exclude(instalacion_id=excluir_instalacion_id)
    for o in qs:
        o_cli = getattr(o.instalacion, 'cliente_id', None) if o.instalacion_id else None
        if o_cli and int(o_cli) != int(cliente_id):
            cli_nom = getattr(o.instalacion.cliente, 'nombre_comercial', '') if o.instalacion.cliente else ''
            zona_nom = getattr(o.zona, 'nombre', '') if o.zona_id else ''
            return (f"El código {letra}{numero} ya pertenece al cliente '{cli_nom}' ({zona_nom}). "
                    "No se puede asignar a una instalación de otro cliente.")
    return None


def sync_nominativo_desde_codigo(instalacion):
    """Best-effort: crea/actualiza el Nominativo de la instalacion a partir de su codigo
    (letra+numero). La letra determina la zona (una letra vive en una sola zona).

    NUNCA lanza excepcion ni bloquea el guardado de la instalacion: si no se puede
    (codigo invalido, letra nueva sin zona, o conflicto de codigo con otro cliente),
    devuelve un mensaje de aviso (str) para mostrar al usuario. Si quedo ok, devuelve None.
    """
    try:
        from ..models import Nominativo
        from .nominativo_views import _validar_nominativo

        cod = str(getattr(instalacion, 'codigo', '') or '').strip().upper()
        nom_existente = Nominativo.objects.filter(instalacion=instalacion).first()

        m = _NOM_COD_RE.match(cod)
        if not m:
            return 'La instalación no tiene un código válido (letra+número); no se creó su nominativo.'
        letra, numero = m.group(1), int(m.group(2))

        # La zona sale de la letra (una letra = una zona). Si la letra ya existe, se usa esa zona.
        zona = None
        otro_de_letra = Nominativo.objects.filter(letra=letra).exclude(
            id=nom_existente.id if nom_existente else 0
        ).select_related('zona').first()
        if otro_de_letra:
            zona = otro_de_letra.zona
        elif nom_existente:
            zona = nom_existente.zona
        if not zona:
            return (f'La letra {letra} es nueva (aún no tiene zona). Asígnala en el panel '
                    '"Zonas y Nominativos" para que la instalación entre en una zona.')

        err = _validar_nominativo(letra, numero, zona.id, instalacion,
                                  excluir_id=nom_existente.id if nom_existente else None)
        if err:
            return err  # queda pendiente; no se crea/actualiza, pero la instalacion SI se guarda

        if nom_existente:
            changed = False
            if (nom_existente.letra, nom_existente.numero) != (letra, numero):
                nom_existente.letra, nom_existente.numero = letra, numero
                changed = True
            if nom_existente.zona_id != zona.id:
                nom_existente.zona = zona
                changed = True
            if changed:
                nom_existente.save()
        else:
            Nominativo.objects.create(zona=zona, letra=letra, numero=numero, instalacion=instalacion)
        return None
    except Exception:
        # Nunca romper el guardado de la instalacion por el nominativo.
        return 'No se pudo crear el nominativo automáticamente; revísalo en el panel "Zonas y Nominativos".'


def resolve_canton_id(canton_token, provincia_token=None):
    """Resuelve un canton_id numérico a partir de un token que puede ser id o nombre."""
    if not canton_token:
        return None
    try:
        return int(canton_token)
    except Exception:
        pass

    provincia_obj = None
    if provincia_token:
        try:
            provincia_obj = Provincia.objects.filter(pk=int(provincia_token)).first()
        except Exception:
            provincia_obj = Provincia.objects.filter(nombre__iexact=str(provincia_token)).first()

    qs = Canton.objects.all()
    if provincia_obj:
        qs = qs.filter(provincia=provincia_obj)

    canton_obj = qs.filter(nombre__iexact=str(canton_token)).first()
    if canton_obj:
        return canton_obj.id
    return None


def get_or_create_provincia(provincia_token):
    """Devuelve o crea Provincia a partir de id o nombre (sin duplicar por acentos/mayúsculas)."""
    from ..utils import buscar_o_crear_provincia
    return buscar_o_crear_provincia(provincia_token, Provincia)


def get_or_create_canton(canton_token, provincia_token=None):
    """Devuelve o crea Canton (y Provincia si falta) a partir de id o nombre."""
    if not canton_token:
        return None
    try:
        canton_obj = Canton.objects.filter(pk=int(canton_token)).first()
        if canton_obj:
            return canton_obj
    except Exception:
        pass

    provincia_obj = get_or_create_provincia(provincia_token) if provincia_token else None

    qs = Canton.objects.all()
    if provincia_obj:
        qs = qs.filter(provincia=provincia_obj)
    nombre = str(canton_token).strip()
    canton_obj = qs.filter(nombre__iexact=nombre).first()
    if canton_obj:
        return canton_obj
    if provincia_obj:
        return Canton.objects.create(nombre=nombre.upper(), provincia=provincia_obj)
    return None


def ensure_default_zonas(instalacion: Instalacion):
    """Garantiza que haya solo una Zona 1 por instalación cuando no se especifica otra.

    Si no hay zonas, crea Zona 1. Si hay más de una, deja la primera y elimina el resto.
    """
    zonas_qs = instalacion.zonas.order_by('id')
    count = zonas_qs.count()
    if count == 0:
        Zona.objects.create(instalacion=instalacion, titulo='Zona 1')
        return
    if count > 1:
        keep = zonas_qs.first()
        zonas_qs.exclude(id=keep.id).delete()


def set_instalacion_zona(instalacion: Instalacion, zona_token):
    """Selecciona/crea una zona según el token (id o título) y elimina el resto.

    - Si zona_token es numérico y existe, conserva esa y borra otras.
    - Si es texto, crea/usa esa Zona para la instalación y borra otras.
    - Si viene '__none__', elimina todas las zonas.
    - Si no viene nada, delega en ensure_default_zonas (Zona 1).
    """
    if zona_token == '__none__':
        instalacion.zonas.all().delete()
        return
    if not zona_token:
        ensure_default_zonas(instalacion)
        return

    try:
        zona_id = int(zona_token)
        zona = Zona.objects.filter(id=zona_id, instalacion=instalacion).first()
        if not zona:
            # Si el id no corresponde, cae a crear por título
            raise ValueError()
    except Exception:
        titulo = str(zona_token).strip() or 'Zona 1'
        zona, _ = Zona.objects.get_or_create(instalacion=instalacion, titulo=titulo)

    # Eliminar zonas distintas a la seleccionada
    instalacion.zonas.exclude(id=zona.id).delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_instalaciones(request):
    # si el usuario no tiene permiso para ver instalaciones, devolver error 403
    if not request.user.has_perm('CoreFisica.view_instalacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    q = (request.GET.get('q') or '').strip()
    cliente_id = request.GET.get('cliente_id')
    cliente = (request.GET.get('cliente') or '').strip()
    provincia_id = request.GET.get('provincia_id')
    canton_id = request.GET.get('canton_id')
    zona_token = request.GET.get('zona_id') or request.GET.get('zona_titulo')

    qs = Instalacion.objects.select_related('cliente', 'canton', 'canton__provincia').prefetch_related('zonas').all()

    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    elif cliente:
        qs = qs.filter(
            Q(cliente__nombre_comercial__icontains=cliente) |
            Q(cliente__razon_social__icontains=cliente)
        )

    if provincia_id:
        qs = qs.filter(canton__provincia_id=provincia_id)

    if canton_id:
        qs = qs.filter(canton_id=canton_id)

    if zona_token:
        try:
            zona_id = int(zona_token)
            qs = qs.filter(zonas__id=zona_id)
        except Exception:
            qs = qs.filter(zonas__titulo__iexact=str(zona_token).strip())

    qs = qs.distinct().order_by('cliente__nombre_comercial', 'nombre', 'id')


    if q:
        qn = _strip_accents(q)
        qs = qs.filter(
            Q(nombre__unaccent__icontains=qn) |
            Q(codigo__unaccent__icontains=qn) |
            Q(cliente__nombre_comercial__unaccent__icontains=qn) |
            Q(cliente__razon_social__unaccent__icontains=qn) |
            Q(canton__nombre__unaccent__icontains=qn) |
            Q(canton__provincia__nombre__unaccent__icontains=qn) |
            Q(direccion__unaccent__icontains=qn) |
            Q(zonas__titulo__unaccent__icontains=qn)
        )

    instalaciones = []
    for inst in qs:
        instalaciones.append({
            'id': inst.id,
            'codigo': inst.codigo or '',
            'nombre': inst.nombre or '',
            'cliente_id': inst.cliente_id,
            'cliente_nombre': getattr(inst.cliente, 'nombre_comercial', ''),
            'canton_id': inst.canton_id,
            'canton_nombre': getattr(inst.canton, 'nombre', ''),
            'provincia_id': getattr(getattr(inst.canton, 'provincia', None), 'id', None),
            'provincia_nombre': getattr(getattr(inst.canton, 'provincia', None), 'nombre', ''),
            'direccion': inst.direccion or '',
            'sector': inst.sector or '',
            'activo': inst.activo,
            'zonas': [
                {
                    'id': z.id,
                    'titulo': z.titulo,
                }
                for z in inst.zonas.all()
            ],
        })
    return JsonResponse(instalaciones, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_instalacion(request):
    #si el usuario no tiene permiso para crear instalaciones, devolver error 403
    if not request.user.has_perm('CoreFisica.add_instalacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    #data es un diccionario con los campos codigo, nombre, cliente_id, canton_id, direccion para crear una nueva instalación
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # soportar `cliente_id` desde frontend
    if 'cliente_id' in data and 'cliente' not in data:
        data['cliente'] = data.pop('cliente_id')

    if 'codigo' in data and data.get('codigo'):
        data['codigo'] = str(data.get('codigo')).strip().upper()
    if 'nombre' in data and data.get('nombre'):
        data['nombre'] = str(data.get('nombre')).strip().upper()
    if 'direccion' in data and data.get('direccion'):
        data['direccion'] = str(data.get('direccion')).strip().upper()
    if 'sector' in data and data.get('sector'):
        data['sector'] = str(data.get('sector')).strip().upper()

    # Intentar resolver/crear provincia y cantón desde tokens (id o nombre)
    provincia_token = data.get('provincia_id') or data.get('provincia')
    canton_token = data.get('canton_id') or data.get('canton')
    provincia_obj = get_or_create_provincia(provincia_token)
    canton_obj = get_or_create_canton(canton_token, provincia_obj.id if provincia_obj else provincia_token)
    if canton_obj:
        data['canton'] = canton_obj.id
    data.pop('canton_id', None)
    data.pop('provincia_id', None)

    # extraer zona antes de validar serializer para evitar campos no permitidos
    zona_token = None
    if 'zona_id' in data and data.get('zona_id') in [None, '', 'null']:
        zona_token = '__none__'
    elif 'zona_titulo' in data and str(data.get('zona_titulo') or '').strip() == '':
        zona_token = '__none__'
    else:
        zona_token = data.get('zona_id') or data.get('zona_titulo')
    data.pop('zona_id', None)
    data.pop('zona_titulo', None)

    # BLOQUEO: no permitir el codigo (nominativo) de otro cliente.
    _conf = codigo_conflicto_cliente(data.get('codigo'), data.get('cliente'))
    if _conf:
        return JsonResponse({'error': _conf}, status=400)

    serializer = InstalacionSerializer(data=data)
    if serializer.is_valid():
        instalacion = serializer.save()
        set_instalacion_zona(instalacion, zona_token)
        aviso = sync_nominativo_desde_codigo(instalacion)
        return JsonResponse({'message': 'Instalación creada', 'id': instalacion.id, 'nominativo_aviso': aviso})
    else:
        return JsonResponse({'error': 'Datos inválidos', 'details': serializer.errors}, status=400)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_instalacion(request, id):
    #si el usuario no tiene permiso para actualizar instalaciones, devolver error 403
    if not request.user.has_perm('CoreFisica.change_instalacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        data = json.loads(request.body)

        try:
            instalacion = Instalacion.objects.get(id=id)
        except Instalacion.DoesNotExist:
            return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

        # soportar `cliente_id` desde frontend
        if 'cliente_id' in data and 'cliente' not in data:
            data['cliente'] = data.pop('cliente_id')

        if 'codigo' in data and data.get('codigo'):
            data['codigo'] = str(data.get('codigo')).strip().upper()
        if 'nombre' in data and data.get('nombre'):
            data['nombre'] = str(data.get('nombre')).strip().upper()
        if 'direccion' in data and data.get('direccion'):
            data['direccion'] = str(data.get('direccion')).strip().upper()

        # Intentar resolver/crear provincia y cantón desde tokens (id o nombre)
        provincia_token = data.get('provincia_id') or data.get('provincia')
        canton_token = data.get('canton_id') or data.get('canton')
        provincia_obj = get_or_create_provincia(provincia_token)
        canton_obj = get_or_create_canton(canton_token, provincia_obj.id if provincia_obj else provincia_token)
        if canton_obj:
            data['canton'] = canton_obj.id
        data.pop('canton_id', None)
        data.pop('provincia_id', None)

        # extraer zona antes de validar serializer para evitar campos no permitidos
        zona_token = None
        if 'zona_id' in data and data.get('zona_id') in [None, '', 'null']:
            zona_token = '__none__'
        elif 'zona_titulo' in data and str(data.get('zona_titulo') or '').strip() == '':
            zona_token = '__none__'
        else:
            zona_token = data.get('zona_id') or data.get('zona_titulo')
        data.pop('zona_id', None)
        data.pop('zona_titulo', None)

        # BLOQUEO: no permitir el codigo (nominativo) de otro cliente.
        _cli = data.get('cliente') or instalacion.cliente_id
        _cod = data.get('codigo', instalacion.codigo)
        _conf = codigo_conflicto_cliente(_cod, _cli, excluir_instalacion_id=instalacion.id)
        if _conf:
            return JsonResponse({'error': _conf}, status=400)

        serializer = InstalacionSerializer(instalacion, data=data, partial=True)
        if serializer.is_valid():
            instalacion = serializer.save()
            set_instalacion_zona(instalacion, zona_token)
            aviso = sync_nominativo_desde_codigo(instalacion)
            return JsonResponse({'message': 'Instalación actualizada', 'id': instalacion.id, 'nominativo_aviso': aviso})
        else:
            return JsonResponse({'error': 'Datos inválidos', 'details': serializer.errors}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cerrar_instalacion(request, id):
    """Cierra (deshabilita) una instalacion en cascada, SIN borrar nada:
      - instalacion.activo = False
      - sus puestos.activo = False
      - sus asignaciones ACTIVO -> INACTIVO (las personas quedan libres)
      - libera su nominativo (se borra -> el codigo queda reutilizable)
    Es reversible con reabrir_instalacion. Conserva historial (reportes/meses pasados)."""
    if not request.user.has_perm('CoreFisica.change_instalacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    from ..models import Puesto, Asignacion, Nominativo
    from django.db import transaction

    inst = Instalacion.objects.filter(id=id).first()
    if not inst:
        return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

    with transaction.atomic():
        inst.activo = False
        inst.save(update_fields=['activo'])
        puestos = Puesto.objects.filter(instalacion=inst, activo=True).count()
        Puesto.objects.filter(instalacion=inst).update(activo=False)
        asigs = Asignacion.objects.filter(instalacion=inst, estado='ACTIVO').count()
        Asignacion.objects.filter(instalacion=inst, estado='ACTIVO').update(estado='INACTIVO')
        libre = Nominativo.objects.filter(instalacion=inst).delete()[0]

    return JsonResponse({
        'message': 'Instalación cerrada',
        'puestos_desactivados': puestos,
        'asignaciones_desactivadas': asigs,
        'nominativo_liberado': bool(libre),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reabrir_instalacion(request, id):
    """Reabre una instalacion: la reactiva, reactiva sus puestos y vuelve a crear su
    nominativo desde el codigo (si el codigo sigue libre). NO reactiva las asignaciones
    (las personas se reasignan o se re-importan)."""
    if not request.user.has_perm('CoreFisica.change_instalacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    from ..models import Puesto
    from django.db import transaction

    inst = Instalacion.objects.filter(id=id).first()
    if not inst:
        return JsonResponse({'error': 'Instalación no encontrada'}, status=404)

    aviso = None
    with transaction.atomic():
        inst.activo = True
        inst.save(update_fields=['activo'])
        Puesto.objects.filter(instalacion=inst).update(activo=True)
        aviso = sync_nominativo_desde_codigo(inst)

    return JsonResponse({'message': 'Instalación reabierta', 'nominativo_aviso': aviso})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_instalacion(request, id):
    #si el usuario no tiene permiso para eliminar instalaciones, devolver error 403
    if not request.user.has_perm('CoreFisica.delete_instalacion'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    # intentar eliminar la instalacion con el id dado, si no existe devolver error 404
    try:
        instalacion = Instalacion.objects.get(id=id)
        # Borrar su nominativo primero (si no, con SET_NULL quedaria "libre" huerfano
        # tapando el codigo). Asi el codigo queda realmente disponible.
        from ..models import Nominativo
        Nominativo.objects.filter(instalacion=instalacion).delete()
        instalacion.delete()
        return JsonResponse({'message':'Instalación eliminada correctamente'}, status=200)
    except Instalacion.DoesNotExist:
        return JsonResponse({'error':'Instalación no encontrada'}, status=404)
    