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

    es_agrupacion = bool(data.get('es_agrupacion'))
    # ids de nominativos EXISTENTES a agrupar en esta zona (solo si es_agrupacion).
    nominativo_ids = data.get('nominativo_ids') or []
    if not isinstance(nominativo_ids, list):
        nominativo_ids = []

    from django.db import transaction
    with transaction.atomic():
        zona = ZonaOperativa.objects.create(
            numero=numero, nombre=nombre or f'Zona {numero}', es_agrupacion=es_agrupacion,
        )
        movidos = 0
        if es_agrupacion and nominativo_ids:
            # Mover nominativos existentes a esta zona guardando su zona ORIGINAL.
            # No aplica la regla "una letra = una zona" (es agrupacion) y el codigo no
            # cambia, asi que no requiere validacion. Al borrar la zona, vuelven.
            for nom in Nominativo.objects.filter(id__in=nominativo_ids).exclude(zona_id=zona.id):
                # Solo guardar zona_anterior si viene de una zona NORMAL (no encadenar
                # agrupaciones): asi al borrar vuelve a su zona real.
                if not nom.zona.es_agrupacion:
                    nom.zona_anterior = nom.zona
                nom.zona = zona
                nom.save(update_fields=['zona', 'zona_anterior'])
                movidos += 1

    data_out = ZonaOperativaSerializer(zona).data
    data_out['nominativos_movidos'] = movidos
    return JsonResponse(data_out, status=201)


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

    # Zona de AGRUPACION: al borrarla, cada nominativo vuelve a su zona anterior.
    if zona.es_agrupacion:
        from django.db import transaction
        noms = list(zona.nominativos.select_related('zona_anterior').all())
        sin_anterior = [nom for nom in noms if not nom.zona_anterior_id]
        if sin_anterior:
            return JsonResponse(
                {'error': f'No se puede borrar: {len(sin_anterior)} nominativo(s) no tienen '
                          'zona anterior a la cual volver. Muévalos manualmente primero.'},
                status=400,
            )
        with transaction.atomic():
            for nom in noms:
                nom.zona = nom.zona_anterior
                nom.zona_anterior = None
                nom.save(update_fields=['zona', 'zona_anterior'])
            zona.delete()
        return JsonResponse({
            'message': f'Zona de agrupación eliminada; {len(noms)} nominativo(s) volvieron a su zona.',
            'restaurados': len(noms),
        })

    # Zona NORMAL: no se borra si tiene nominativos.
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
    2) El CODIGO (letra+numero) debe ser UNICO por instalacion: NO se permite repetir,
       ni siquiera en el mismo cliente. Si ya existe otro nominativo con ese codigo => error.
    """
    # 1) La letra no puede estar en otra zona. NO aplica si la zona destino es de
    #    AGRUPACION (mezcla letras a proposito), y se IGNORAN los nominativos que ya
    #    estan en zonas de agrupacion (son temporales, no definen la zona de la letra).
    zona_dest = ZonaOperativa.objects.filter(id=zona_id).first()
    if not (zona_dest and zona_dest.es_agrupacion):
        otra_zona = (Nominativo.objects.filter(letra=letra)
                     .exclude(zona_id=zona_id)
                     .exclude(zona__es_agrupacion=True)
                     .select_related('zona'))
        if excluir_id:
            otra_zona = otra_zona.exclude(id=excluir_id)
        z = otra_zona.first()
        if z:
            return (f"La letra {letra} ya pertenece a la {z.zona.nombre}. "
                    "Una letra solo puede estar en una zona.")

    # 2) Codigo UNICO: no se permite ningun otro nominativo con el mismo letra+numero.
    dup = Nominativo.objects.filter(letra=letra, numero=numero).select_related('instalacion', 'instalacion__cliente')
    if excluir_id:
        dup = dup.exclude(id=excluir_id)
    o = dup.first()
    if o:
        detalle = ''
        if o.instalacion_id:
            cli = getattr(o.instalacion, 'cliente', None)
            detalle = f" (ya lo usa {o.instalacion.nombre} - {getattr(cli, 'nombre_comercial', '')})"
        return f"El código {letra}{numero} ya existe{detalle}. El código debe ser único por instalación."
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

    # Reclamar huerfanos: nominativos LIBRES (sin instalacion) con ese mismo codigo no
    # aportan nada y solo tapan el numero. Se borran para que el codigo quede disponible.
    Nominativo.objects.filter(letra=letra, numero=numero, instalacion__isnull=True).delete()

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
