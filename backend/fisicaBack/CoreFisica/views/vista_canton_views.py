"""Vistas compartidas (guardadas en BD): agrupaciones por cantones, por empresa o por tipo de persona."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import VistaCanton


def _serialize(v):
    return {
        'id': str(v.id),
        'nombre': v.nombre,
        'tipo': v.tipo or 'canton',
        'cantonIds': v.cantones or [],
        'clienteIds': v.clientes or [],
        'instalacionIds': getattr(v, 'instalaciones', None) or [],
        'tipos': v.tipos or [],
    }


def _int_list(values):
    out = []
    for x in values or []:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vistas_cantones(request):
    """Vistas compartidas (globales) por cantones o por empresas/clientes.

    GET  -> lista todas las vistas.
    POST -> sincroniza la lista completa (upsert + prune): actualiza las que traen
            id existente, crea las nuevas y elimina las que ya no estén. Devuelve
            la lista final con ids estables.
    """
    if request.method == 'GET':
        return Response([_serialize(v) for v in VistaCanton.objects.all()])

    payload = request.data.get('views', []) if isinstance(request.data, dict) else []
    if not isinstance(payload, list):
        payload = []

    kept_ids = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get('nombre') or '').strip()
        tipo = str(item.get('tipo') or 'canton').strip().lower()
        if tipo not in ('canton', 'cliente', 'persona_tipo'):
            tipo = 'canton'
        cantones = _int_list(item.get('cantonIds'))
        clientes = _int_list(item.get('clienteIds'))
        instalaciones = _int_list(item.get('instalacionIds'))
        tipos = [str(t).strip().upper() for t in (item.get('tipos') or []) if str(t).strip()]

        # Validación por tipo: cantones agrupa 2+, empresas 1+, tipo-persona 1+.
        if not nombre:
            continue
        if tipo == 'canton' and len(cantones) < 2:
            continue
        if tipo == 'cliente' and len(clientes) < 1:
            continue
        if tipo == 'persona_tipo' and len(tipos) < 1:
            continue

        raw_id = str(item.get('id') or '')
        obj = VistaCanton.objects.filter(id=int(raw_id)).first() if raw_id.isdigit() else None
        # Las instalaciones solo aplican a vistas de empresa.
        if tipo != 'cliente':
            instalaciones = []
        if obj:
            obj.nombre = nombre
            obj.tipo = tipo
            obj.cantones = cantones
            obj.clientes = clientes
            obj.instalaciones = instalaciones
            obj.tipos = tipos
            obj.save(update_fields=['nombre', 'tipo', 'cantones', 'clientes', 'instalaciones', 'tipos'])
        else:
            obj = VistaCanton.objects.create(
                nombre=nombre, tipo=tipo, cantones=cantones, clientes=clientes,
                instalaciones=instalaciones, tipos=tipos
            )
        kept_ids.append(obj.id)

    # Salvaguarda: solo se hace prune (borrado de las no enviadas) si efectivamente
    # llegaron vistas válidas. Un payload vacío NO borra todo (evita perder vistas
    # si el cliente sincroniza con una lista vacía por error o sin haber cargado).
    if kept_ids:
        VistaCanton.objects.exclude(id__in=kept_ids).delete()

    return Response({'views': [_serialize(v) for v in VistaCanton.objects.all()]})
