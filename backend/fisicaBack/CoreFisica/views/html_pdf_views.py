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
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

log = logging.getLogger("html2pdf")

# Tamano maximo del HTML aceptado (anti-abuso): 10 MB.
MAX_HTML_BYTES = 10 * 1024 * 1024


@api_view(['POST'])
@authentication_classes([])          # no usa JWT: se autentica por API Key
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
