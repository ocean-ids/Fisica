"""Endpoint de sincronizacion de empleados desde el ERP Powersai (Push).

El worker .NET del ERP hace POST a /api/v1/sync/empleado/ con el JSON del empleado.
- Autenticacion por API Key (Authorization: Bearer <SYNC_API_KEY>).
- Solo se sincroniza personal de Seguridad Fisica (filtro por unidad de negocio).
- Upsert por cedula en Persona (los reintentos no duplican).
- Responde 2xx (ok), 4xx (dato invalido, no reintentar), 5xx (error, reintentar).
"""
import datetime

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..models import Persona, Provincia, Canton, Cliente


def _fecha(v):
    if not v:
        return None
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _norm(v):
    return str(v or '').strip()


@api_view(['POST'])
@authentication_classes([])          # no usa JWT: se autentica por API Key
@permission_classes([AllowAny])
def sincronizar_empleado(request):
    # 1) API Key
    auth = request.headers.get('Authorization', '')
    token = auth[7:].strip() if auth.lower().startswith('bearer ') else ''
    api_key = getattr(settings, 'SYNC_API_KEY', '')
    if not api_key or token != api_key:
        return Response({'error': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data if isinstance(request.data, dict) else {}

    # 2) FILTRO: solo personal de Seguridad Fisica
    unidad = _norm(data.get('unidad_negocio')).upper()
    if unidad not in ('SF', 'SEGURIDAD FISICA'):
        return Response({'detail': 'Ignorado: no es Seguridad Fisica'}, status=status.HTTP_200_OK)

    cedula = _norm(data.get('cedula'))
    if not cedula:
        return Response({'error': 'cedula requerida'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 3) baja -> is_active
        evento = _norm(request.headers.get('X-Powersai-Event')).lower()
        estado = _norm(data.get('estado')).lower()
        is_active = not (evento == 'empleado.baja' or estado in ('baja', 'inactivo', 'inactiva', 'cesado'))

        # 4) sexo / estado_civil normalizados a las claves del modelo
        sx = _norm(data.get('sexo')).upper()
        sexo = 'MASCULINO' if sx.startswith('M') else ('FEMENINO' if sx.startswith('F') else '')
        ec = _norm(data.get('estado_civil')).upper()
        estado_civil = {'SOLTERO': 'SOLTERO', 'CASADO': 'CASADO'}.get(ec, '')

        # 5) provincia / canton (texto -> FK)
        prov = None
        if _norm(data.get('provincia')):
            prov = Provincia.objects.filter(nombre__iexact=_norm(data.get('provincia'))).first()
        canton = None
        if _norm(data.get('canton')):
            qs = Canton.objects.filter(nombre__iexact=_norm(data.get('canton')))
            if prov:
                qs = qs.filter(provincia=prov)
            canton = qs.first()

        # 6) cliente (texto -> FK por razon social, RUC o nombre comercial)
        cli = None
        cli_txt = _norm(data.get('cliente'))
        if cli_txt:
            cli = (Cliente.objects.filter(razon_social__iexact=cli_txt).first()
                   or Cliente.objects.filter(ruc=cli_txt).first()
                   or Cliente.objects.filter(nombre_comercial__iexact=cli_txt).first())

        # 7) Upsert por cedula
        defaults = {
            'nombres': _norm(data.get('nombres')),
            'apellidos': _norm(data.get('apellidos')),
            'is_active': is_active,
            'sexo': sexo,
            'estado_civil': estado_civil,
            'fecha_nacimiento': _fecha(data.get('fecha_nacimiento')),
            'lugar_nacimiento': _norm(data.get('lugar_nacimiento')),
            'direccion': _norm(data.get('direccion')),
            'telefono': _norm(data.get('telefono')),
            'conyuge': _norm(data.get('conyuge')),
            'nacionalidad': _norm(data.get('nacionalidad')),
            'parroquia': _norm(data.get('parroquia')),
            'cargo': _norm(data.get('cargo')),
            'departamento': _norm(data.get('departamento')),
            'seccion': _norm(data.get('seccion')),
            'fecha_ingreso': _fecha(data.get('fecha_ingreso')),
            'fecha_salida': _fecha(data.get('fecha_salida')),
            'correo_personal': _norm(data.get('correo_personal')),
            'codigo_erp': _norm(data.get('codigo_erp')),
            'centro_costo': _norm(data.get('centro_costo')),
            'unidad_negocio': _norm(data.get('unidad_negocio')),
            'tipo_empleado': _norm(data.get('tipo_empleado')).upper(),
            'forma_pago': _norm(data.get('forma_pago')),
            'numero_afiliacion': _norm(data.get('numero_afiliacion')),
            'numero_contrato': _norm(data.get('numero_contrato')),
            'actividad': _norm(data.get('actividad')),
            'perfil': _norm(data.get('perfil')),
            'fecha_pago_liquidacion': _fecha(data.get('fecha_pago_liquidacion')),
            'motivo_salida': _norm(data.get('motivo_salida')),
            'region': _norm(data.get('region')),
        }
        if prov is not None:
            defaults['provincia'] = prov
        if canton is not None:
            defaults['canton'] = canton
        if cli is not None:
            defaults['cliente'] = cli

        persona, creado = Persona.objects.update_or_create(cedula=cedula, defaults=defaults)
        return Response(
            {'cedula': cedula, 'id': persona.id, 'creado': creado},
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK
        )
    except Exception as e:
        # 5xx -> el worker reintenta
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
