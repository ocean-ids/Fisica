"""Archivos subidos (/media/) con DATOS PERSONALES protegidos.

Las fotos de personas (`personas/`) y los certificados (`certificados/`) ya no se entregan a cualquiera que tenga
el enlace: el enlace que manda el servidor lleva una FIRMA (`?firma=...`) que solo él puede generar, y sin esa firma
el archivo solo se entrega a quien llega con sesión (token JWT). Así nadie puede descargar los archivos adivinando
o recorriendo nombres.

Las pantallas no cambian: ya usan el enlace que les manda el servidor (ahora con la firma). Las fotos de los
USUARIOS del sistema (`user_photos/`) siguen como antes.
"""
import mimetypes
import posixpath

from django.conf import settings
from django.core.signing import Signer
from django.http import Http404
from django.utils.crypto import constant_time_compare
from django.views.static import serve

# Carpetas de /media/ que llevan datos personales de los empleados.
CARPETAS_PROTEGIDAS = ('personas/', 'certificados/')

_firmador = Signer(salt='CoreFisica.media_protegida')


def firma_de(nombre):
    """Firma del archivo (por su ruta dentro de /media/)."""
    return _firmador.signature(nombre)


def es_protegido(nombre):
    return (nombre or '').lstrip('/').startswith(CARPETAS_PROTEGIDAS)


def url_media(request, archivo):
    """URL absoluta del archivo; si está en una carpeta protegida, con su firma."""
    if not archivo:
        return None
    try:
        url = archivo.url
    except Exception:
        return None
    if es_protegido(archivo.name):
        url = f"{url}{'&' if '?' in url else '?'}firma={firma_de(archivo.name)}"
    try:
        return request.build_absolute_uri(url) if request is not None else url
    except Exception:
        return url


def _tiene_sesion(request):
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        return JWTAuthentication().authenticate(request) is not None
    except Exception:
        return False


def servir_media(request, path):
    """Entrega un archivo de /media/. Los protegidos exigen la firma correcta o una sesión válida."""
    ruta = posixpath.normpath(path).lstrip('/')
    if es_protegido(ruta):
        firma = request.GET.get('firma') or ''
        valida = bool(firma) and constant_time_compare(firma, firma_de(ruta))
        if not valida and not _tiene_sesion(request):
            raise Http404()
    resp = serve(request, path, document_root=settings.MEDIA_ROOT)
    resp['X-Content-Type-Options'] = 'nosniff'
    # Un certificado que no es imagen se DESCARGA (no se abre en el navegador dentro de la plataforma).
    if ruta.startswith('certificados/'):
        tipo = mimetypes.guess_type(ruta)[0] or ''
        if not tipo.startswith('image/'):
            resp['Content-Disposition'] = 'attachment'
    return resp
