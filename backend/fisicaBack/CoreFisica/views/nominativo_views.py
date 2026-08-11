"""Vistas CRUD de Zonas operativas y Nominativos (letra + numero).

Reglas:
- Zona: numero unico. No se puede borrar una zona que tenga nominativos.
- Nominativo: el mismo codigo (letra+numero) PUEDE repetirse en varias instalaciones
  SIEMPRE que sean del MISMO cliente; en cliente distinto es conflicto (se rechaza).
"""
import json

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..models import ZonaOperativa, Nominativo, Instalacion
from ..serializers import ZonaOperativaSerializer, NominativoSerializer


def _set_codigo_instalacion(instalacion, codigo):
    """Escribe (o limpia con '') el codigo de la instalacion para mantenerlo sincronizado
    con su nominativo. El codigo de la instalacion es lo que usan import/sacafranco/reportes."""
    if not instalacion:
        return
    nuevo = codigo or ''
    if (instalacion.codigo or '') != nuevo:
        instalacion.codigo = nuevo
        instalacion.save(update_fields=['codigo'])


# ----------------------------- ZONAS -----------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_zonas_operativas(request):
    if not request.user.has_perm('CoreFisica.view_zonaoperativa'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    qs = ZonaOperativa.objects.all().order_by('numero')
    return JsonResponse(ZonaOperativaSerializer(qs, many=True).data, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_zona_operativa(request):
    if not request.user.has_perm('CoreFisica.add_zonaoperativa'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    numero = data.get('numero')
    nombre = str(data.get('nombre') or '').strip()
    if numero in (None, ''):
        return JsonResponse({'error': 'El número de zona es obligatorio'}, status=400)
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'El número de zona debe ser un entero'}, status=400)
    if ZonaOperativa.objects.filter(numero=numero).exists():
        return JsonResponse({'error': f'Ya existe la Zona {numero}'}, status=400)

    zona = ZonaOperativa.objects.create(numero=numero, nombre=nombre or f'Zona {numero}')
    return JsonResponse(ZonaOperativaSerializer(zona).data, status=201)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_zona_operativa(request, id):
    if not request.user.has_perm('CoreFisica.change_zonaoperativa'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    zona = ZonaOperativa.objects.filter(id=id).first()
    if not zona:
        return JsonResponse({'error': 'Zona no encontrada'}, status=404)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if 'numero' in data and data.get('numero') not in (None, ''):
        try:
            numero = int(data.get('numero'))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'El número de zona debe ser un entero'}, status=400)
        if ZonaOperativa.objects.filter(numero=numero).exclude(id=zona.id).exists():
            return JsonResponse({'error': f'Ya existe la Zona {numero}'}, status=400)
        zona.numero = numero
    if 'nombre' in data:
        zona.nombre = str(data.get('nombre') or '').strip()
    zona.save()
    return JsonResponse(ZonaOperativaSerializer(zona).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_zona_operativa(request, id):
    if not request.user.has_perm('CoreFisica.delete_zonaoperativa'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    zona = ZonaOperativa.objects.filter(id=id).first()
    if not zona:
        return JsonResponse({'error': 'Zona no encontrada'}, status=404)
    n = zona.nominativos.count()
    if n:
        return JsonResponse(
            {'error': f'No se puede borrar: la zona tiene {n} nominativo(s). Muévalos o bórrelos primero.'},
            status=400,
        )
    zona.delete()
    return JsonResponse({'message': 'Zona eliminada'})


# --------------------------- NOMINATIVOS ---------------------------

def _validar_nominativo(letra, numero, zona_id, instalacion, excluir_id=None):
    """Valida las reglas del nominativo. Devuelve un mensaje de error o None.

    1) Una LETRA solo puede estar en UNA zona (si la letra ya existe en otra zona, error).
    2) El CODIGO (letra+numero) solo se puede repetir en instalaciones del MISMO cliente
       (ambas con instalacion). En cualquier otro caso (cliente distinto, o alguna sin
       instalacion) => ya existe / conflicto.
    """
    # 1) La letra no puede estar en otra zona.
    otra_zona = Nominativo.objects.filter(letra=letra).exclude(zona_id=zona_id).select_related('zona')
    if excluir_id:
        otra_zona = otra_zona.exclude(id=excluir_id)
    z = otra_zona.first()
    if z:
        return (f"La letra {letra} ya pertenece a la {z.zona.nombre}. "
                "Una letra solo puede estar en una zona.")

    # 2) Codigo duplicado / cliente.
    mismos = Nominativo.objects.filter(letra=letra, numero=numero).select_related('instalacion', 'instalacion__cliente')
    if excluir_id:
        mismos = mismos.exclude(id=excluir_id)
    new_cli = getattr(instalacion, 'cliente_id', None) if instalacion else None
    for o in mismos:
        o_cli = getattr(o.instalacion, 'cliente_id', None) if o.instalacion_id else None
        if o_cli and new_cli and o_cli == new_cli:
            continue  # mismo cliente, distinta instalacion -> permitido
        if o_cli and new_cli and o_cli != new_cli:
            return (f"El código {letra}{numero} ya pertenece a otro cliente "
                    f"({getattr(o.instalacion.cliente, 'nombre_comercial', '')}). "
                    "Solo se puede repetir en instalaciones del mismo cliente.")
        # alguno sin instalacion (libre) o el nuevo sin instalacion -> ya existe
        return f"El código {letra}{numero} ya existe."
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_nominativos(request):
    if not request.user.has_perm('CoreFisica.view_nominativo'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    qs = Nominativo.objects.select_related('zona', 'instalacion', 'instalacion__cliente').all()
    zona_id = request.GET.get('zona_id')
    if zona_id:
        qs = qs.filter(zona_id=zona_id)
    q = (request.GET.get('q') or '').strip().upper()
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(letra__icontains=q) |
            Q(instalacion__nombre__icontains=q) |
            Q(instalacion__codigo__icontains=q) |
            Q(instalacion__cliente__nombre_comercial__icontains=q)
        )
    qs = qs.order_by('letra', 'numero')
    return JsonResponse(NominativoSerializer(qs, many=True).data, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_nominativo(request):
    if not request.user.has_perm('CoreFisica.add_nominativo'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    zona_id = data.get('zona')
    letra = str(data.get('letra') or '').strip().upper()
    numero = data.get('numero')
    instalacion_id = data.get('instalacion')

    if not zona_id:
        return JsonResponse({'error': 'La zona es obligatoria'}, status=400)
    if not letra:
        return JsonResponse({'error': 'La letra es obligatoria'}, status=400)
    if numero in (None, ''):
        return JsonResponse({'error': 'El número es obligatorio'}, status=400)
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'El número debe ser un entero'}, status=400)

    zona = ZonaOperativa.objects.filter(id=zona_id).first()
    if not zona:
        return JsonResponse({'error': 'Zona no encontrada'}, status=404)

    instalacion = None
    if instalacion_id:
        instalacion = Instalacion.objects.filter(id=instalacion_id).first()
        if not instalacion:
            return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
        if hasattr(instalacion, 'nominativo'):
            return JsonResponse({'error': 'Esa instalación ya tiene un nominativo asignado'}, status=400)

    err = _validar_nominativo(letra, numero, zona.id, instalacion)
    if err:
        return JsonResponse({'error': err}, status=400)

    nom = Nominativo.objects.create(zona=zona, letra=letra, numero=numero, instalacion=instalacion)
    # Escribir el codigo en la instalacion (fuente de verdad para import/sacafranco/reportes).
    _set_codigo_instalacion(instalacion, f"{letra}{numero}")
    nom = Nominativo.objects.select_related('zona', 'instalacion', 'instalacion__cliente').get(id=nom.id)
    return JsonResponse(NominativoSerializer(nom).data, status=201)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_nominativo(request, id):
    if not request.user.has_perm('CoreFisica.change_nominativo'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    nom = Nominativo.objects.filter(id=id).first()
    if not nom:
        return JsonResponse({'error': 'Nominativo no encontrado'}, status=404)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    old_inst = nom.instalacion  # para limpiar su codigo si el nominativo se mueve de instalacion

    if 'zona' in data and data.get('zona'):
        zona = ZonaOperativa.objects.filter(id=data.get('zona')).first()
        if not zona:
            return JsonResponse({'error': 'Zona no encontrada'}, status=404)
        nom.zona = zona
    if 'letra' in data:
        nom.letra = str(data.get('letra') or '').strip().upper()
    if 'numero' in data and data.get('numero') not in (None, ''):
        try:
            nom.numero = int(data.get('numero'))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'El número debe ser un entero'}, status=400)

    if 'instalacion' in data:
        instalacion_id = data.get('instalacion')
        if instalacion_id:
            instalacion = Instalacion.objects.filter(id=instalacion_id).first()
            if not instalacion:
                return JsonResponse({'error': 'Instalación no encontrada'}, status=404)
            otro = getattr(instalacion, 'nominativo', None)
            if otro and otro.id != nom.id:
                return JsonResponse({'error': 'Esa instalación ya tiene un nominativo asignado'}, status=400)
            nom.instalacion = instalacion
        else:
            nom.instalacion = None

    err = _validar_nominativo(nom.letra, nom.numero, nom.zona_id, nom.instalacion, excluir_id=nom.id)
    if err:
        return JsonResponse({'error': err}, status=400)

    nom.save()
    # Sincronizar codigos de instalacion: si el nominativo se movio de instalacion,
    # la vieja pierde su codigo; la actual queda con letra+numero.
    if old_inst and (not nom.instalacion_id or nom.instalacion_id != old_inst.id):
        _set_codigo_instalacion(old_inst, '')
    if nom.instalacion:
        _set_codigo_instalacion(nom.instalacion, f"{nom.letra}{nom.numero}")
    nom = Nominativo.objects.select_related('zona', 'instalacion', 'instalacion__cliente').get(id=nom.id)
    return JsonResponse(NominativoSerializer(nom).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_nominativo(request, id):
    if not request.user.has_perm('CoreFisica.delete_nominativo'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    nom = Nominativo.objects.filter(id=id).first()
    if not nom:
        return JsonResponse({'error': 'Nominativo no encontrado'}, status=404)
    inst = nom.instalacion
    nom.delete()
    # Al borrar el nominativo, la instalacion queda sin codigo (SIN ZONA).
    _set_codigo_instalacion(inst, '')
    return JsonResponse({'message': 'Nominativo eliminado'})
