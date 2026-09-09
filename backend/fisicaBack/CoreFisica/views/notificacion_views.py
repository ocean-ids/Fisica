"""Notificaciones de validación de eventuales (para el usuario validador)."""
import re
from django.http import JsonResponse
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import NotificacionEventual


def _serialize_notificacion(n):
    p = n.persona
    return {
        'id': n.id,
        'mensaje': n.mensaje,
        'leida': n.leida,
        'resuelta': n.resuelta,
        'creada_en': n.creada_en.isoformat() if n.creada_en else None,
        'creada_por': (n.creada_por.get_username() if n.creada_por else None),
        'persona': {
            'id': p.id if p else None,
            'cedula': p.cedula if p else '',
            'nombres': p.nombres if p else '',
            'apellidos': p.apellidos if p else '',
            'tipo': p.tipo if p else '',
            'validado': p.validado if p else None,
        } if p else None,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_notificaciones_eventual(request):
    """Notificaciones pendientes (no resueltas) del usuario en sesión."""
    qs = (NotificacionEventual.objects
          .select_related('persona', 'creada_por')
          .filter(destinatario=request.user, resuelta=False))
    items = [_serialize_notificacion(n) for n in qs]
    return JsonResponse({'results': items, 'total': len(items)}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirmar_notificacion_eventual(request, pk):
    """Aplica las correcciones (si vienen), marca el eventual como validado
    y cierra la notificación. El body puede traer: cedula, nombres, apellidos, tipo."""
    n = (NotificacionEventual.objects
         .select_related('persona')
         .filter(pk=pk, destinatario=request.user)
         .first())
    if not n:
        return JsonResponse({'error': 'Notificación no encontrada'}, status=404)

    data = request.data or {}
    p = n.persona
    if p:
        # Correcciones opcionales de los datos básicos.
        if 'nombres' in data and data.get('nombres') is not None:
            p.nombres = str(data.get('nombres')).strip().upper()
        if 'apellidos' in data and data.get('apellidos') is not None:
            p.apellidos = str(data.get('apellidos')).strip().upper()
        if data.get('tipo'):
            p.tipo = str(data.get('tipo')).strip()
        if data.get('cedula'):
            nueva = str(data.get('cedula')).strip()
            if not re.match(r'^\d{1,10}$', nueva):
                return JsonResponse({'error': 'Cédula inválida: sólo dígitos, máximo 10'}, status=400)
            p.cedula = nueva
        p.validado = True
        try:
            p.save()
        except IntegrityError:
            return JsonResponse({'error': 'Cédula ya registrada'}, status=400)

    n.leida = True
    n.resuelta = True
    n.save(update_fields=['leida', 'resuelta'])
    return JsonResponse({'message': 'Eventual validado'}, status=200)
