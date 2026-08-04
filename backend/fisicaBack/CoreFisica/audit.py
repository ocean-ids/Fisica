"""Contexto de auditoría por request.

Las señales (post_save/post_delete) no tienen acceso al request, así que el
middleware guarda el request actual en un almacenamiento thread-local que las
señales luego leen.

Nota DRF + JWT: con SimpleJWT el usuario se autentica DENTRO de la vista (no en
el middleware de Django). DRF sincroniza `request.user` al request subyacente al
autenticar, por eso guardamos el *request* y leemos `request.user` en el momento
de la señal (ya autenticado), no al inicio del middleware.
"""
import contextlib
import threading

_local = threading.local()


def _current_request():
    return getattr(_local, 'request', None)


def audit_is_suppressed():
    """True si la auditoría fila-por-fila está desactivada en este hilo."""
    return getattr(_local, 'suppress_audit', False)


@contextlib.contextmanager
def suppress_audit():
    """Desactiva la auditoría post_save/post_delete dentro del bloque (por hilo).

    Se usa en importaciones masivas: generar un AuditLog + str(instance) por cada
    fila guardada multiplica las consultas y no aporta (el import lleva su propio
    resumen). Al ser thread-local, no afecta a otras peticiones concurrentes.
    """
    prev = getattr(_local, 'suppress_audit', False)
    _local.suppress_audit = True
    try:
        yield
    finally:
        _local.suppress_audit = prev


def get_current_user():
    request = _current_request()
    if request is None:
        return None
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return None


def get_current_ip():
    request = _current_request()
    if request is None:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AuditUserMiddleware:
    """Guarda el request actual en thread-local para que las señales lean el usuario/IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None
