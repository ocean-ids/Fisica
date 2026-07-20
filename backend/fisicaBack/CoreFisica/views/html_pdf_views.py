"""Endpoint HTML -> PDF (consumido por Power Automate).

POST /api/v1/html-a-pdf/
- Autenticacion por API Key: header Authorization: Bearer <PDF_API_KEY>.
- Body JSON:
    {
      "html": "<html>...</html>",     (obligatorio)
      "formato": "Letter" | "A4",      (opcional, default Letter)
      "horizontal": true | false,      (opcional, default false)
      "margen": "15mm"                 (opcional, margen uniforme)
    }
- Respuesta JSON: { "exito": true, "pdf_base64": "JVBERi0..." }

Usa WeasyPrint (HTML + CSS, sin JavaScript). El import es perezoso para que la
app arranque aunque WeasyPrint / sus librerias del SO no esten instaladas.
"""
import base64
import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample

log = logging.getLogger("html2pdf")

# Tamano maximo del HTML aceptado (anti-abuso): 10 MB.
MAX_HTML_BYTES = 10 * 1024 * 1024


class PdfApiKeyAuthentication(BaseAuthentication):
    """Autentica por API Key: header 'Authorization: Bearer <PDF_API_KEY>'.
    Sirve para que Swagger muestre el candado (Authorize) y envíe el header.
    La validación real también está en la vista para conservar la respuesta
    { "exito": false, "error": "No autorizado" }."""
    def authenticate(self, request):
        auth = request.headers.get('Authorization', '')
        if not auth.lower().startswith('bearer '):
            return None
        token = auth[7:].strip()
        api_key = getattr(settings, 'PDF_API_KEY', '')
        if api_key and token == api_key:
            return (AnonymousUser(), token)
        return None   # key incorrecta: la vista devuelve el 401 con su formato


class PdfApiKeyScheme(OpenApiAuthenticationExtension):
    """Registra el esquema de seguridad 'PdfApiKey' (Bearer) en Swagger."""
    target_class = 'CoreFisica.views.html_pdf_views.PdfApiKeyAuthentication'
    name = 'PdfApiKey'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'description': 'API Key del endpoint. Pega solo la clave (Swagger antepone "Bearer ").',
        }


@extend_schema(
    summary='Convierte HTML a PDF (devuelve el PDF en base64).',
    description='Autenticación por API Key (Authorization: Bearer <PDF_API_KEY>).',
    request=inline_serializer('HtmlAPdfRequest', {
        'html': serializers.CharField(help_text='HTML a convertir (obligatorio).'),
        'formato': serializers.ChoiceField(choices=['Letter', 'A4'], required=False),
        'horizontal': serializers.BooleanField(required=False),
        'margen': serializers.CharField(required=False, help_text='ej. "15mm"'),
    }),
    responses=inline_serializer('HtmlAPdfResponse', {
        'exito': serializers.BooleanField(),
        'pdf_base64': serializers.CharField(),
    }),
    examples=[OpenApiExample('Ejemplo', value={'html': '<h1>Hola</h1><p>Prueba</p>', 'formato': 'Letter', 'horizontal': False})],
)
@api_view(['POST'])
@authentication_classes([PdfApiKeyAuthentication])   # habilita el Authorize en Swagger
@permission_classes([AllowAny])
def html_a_pdf(request):
    # 1) API Key
    auth = request.headers.get('Authorization', '')
    token = auth[7:].strip() if auth.lower().startswith('bearer ') else ''
    api_key = getattr(settings, 'PDF_API_KEY', '')
    if not api_key or token != api_key:
        return Response({'exito': False, 'error': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data if isinstance(request.data, dict) else {}
    html = data.get('html')
    if not html or not str(html).strip():
        return Response({'exito': False, 'error': "Falta el campo 'html'."},
                        status=status.HTTP_400_BAD_REQUEST)

    if len(str(html).encode('utf-8', 'ignore')) > MAX_HTML_BYTES:
        return Response({'exito': False, 'error': 'HTML demasiado grande.'},
                        status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    formato = str(data.get('formato') or 'Letter').strip() or 'Letter'
    horizontal = bool(data.get('horizontal', False))
    margen = str(data.get('margen') or '15mm').strip() or '15mm'

    # 2) Import perezoso de WeasyPrint (evita romper el arranque si no esta instalado).
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:  # noqa: BLE001
        log.error("WeasyPrint no disponible: %s", e)
        return Response(
            {'exito': False, 'error': 'Generador de PDF no disponible en el servidor.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # 3) CSS @page para tamano/orientacion/margenes (WeasyPrint respeta print CSS).
    orientacion = 'landscape' if horizontal else 'portrait'
    page_css = f"@page {{ size: {formato} {orientacion}; margin: {margen}; }}"

    try:
        log.info("HTML->PDF: %d caracteres (formato=%s, horizontal=%s)", len(str(html)), formato, horizontal)
        pdf_bytes = HTML(string=str(html)).write_pdf(stylesheets=[_css(page_css)])
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        log.info("HTML->PDF: PDF generado (%.1f KB)", len(pdf_bytes) / 1024)
        return Response({'exito': True, 'pdf_base64': pdf_b64}, status=status.HTTP_200_OK)
    except Exception as e:  # noqa: BLE001
        log.exception("Error convirtiendo HTML a PDF")
        return Response({'exito': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _css(text):
    """Construye un objeto CSS de WeasyPrint (import perezoso)."""
    from weasyprint import CSS  # type: ignore
    return CSS(string=text)
