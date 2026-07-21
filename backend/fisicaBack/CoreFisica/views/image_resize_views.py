"""Endpoint para reducir/comprimir imagenes (reemplaza el truco OneDrive+SharePoint getpreview.ashx).

POST /api/v1/reducir-imagen/
- Autenticacion por API Key: header Authorization: Bearer <PDF_API_KEY> (misma clave que html-a-pdf).
- Body JSON:
    {
      "imagen_base64": "iVBORw0KG...",   (obligatorio; con o sin el prefijo "data:image/...;base64,")
      "ancho_max": 1000,                  (opcional, default 1000px)
      "calidad": 80                       (opcional, default 80, calidad JPEG)
    }
- Respuesta JSON: { "exito": true, "imagen_base64": "/9j/4AAQ...", "ancho": 1000, "alto": 750, "peso_kb": 145.2 }

Un solo llamado por foto: reemplaza la cadena Crear_archivo -> Wait -> getpreview.ashx ->
Crear_archivo_miniatura -> Wait -> Eliminar_archivo que se usaba antes en Power Automate.
Requiere Pillow (ya viene en requirements.txt).
"""
import base64
import io
import logging

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample

from .html_pdf_views import PdfApiKeyAuthentication  # reutiliza el esquema Bearer para Swagger

log = logging.getLogger("reducir_imagen")

MAX_IMG_BYTES = 15 * 1024 * 1024  # anti-abuso: 15MB de imagen de entrada (decodificada)
DEFAULT_ANCHO_MAX = 1000
DEFAULT_CALIDAD = 80


@extend_schema(
    summary='Reduce/comprime una imagen (base64) y la devuelve en base64 (JPEG).',
    description='Autenticación por API Key (Authorization: Bearer <PDF_API_KEY>). Un solo llamado por foto.',
    request=inline_serializer('ReducirImagenRequest', {
        'imagen_base64': serializers.CharField(help_text='Imagen en base64 (con o sin prefijo "data:image/...;base64,").'),
        'ancho_max': serializers.IntegerField(required=False, help_text='Ancho máximo en px (default 1000).'),
        'calidad': serializers.IntegerField(required=False, help_text='Calidad JPEG 1-95 (default 80).'),
    }),
    responses=inline_serializer('ReducirImagenResponse', {
        'exito': serializers.BooleanField(),
        'imagen_base64': serializers.CharField(),
        'ancho': serializers.IntegerField(),
        'alto': serializers.IntegerField(),
        'peso_kb': serializers.FloatField(),
    }),
    examples=[OpenApiExample('Ejemplo', value={'imagen_base64': 'iVBORw0KGgo...', 'ancho_max': 1000, 'calidad': 80})],
)
@api_view(['POST'])
@authentication_classes([PdfApiKeyAuthentication])   # habilita el Authorize en Swagger
@permission_classes([AllowAny])
def reducir_imagen(request):
    # 1) API Key (misma que html-a-pdf)
    auth = request.headers.get('Authorization', '')
    token = auth[7:].strip() if auth.lower().startswith('bearer ') else ''
    api_key = getattr(settings, 'PDF_API_KEY', '')
    if not api_key or token != api_key:
        return Response({'exito': False, 'error': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data if isinstance(request.data, dict) else {}
    imagen_b64 = data.get('imagen_base64')
    if not imagen_b64 or not str(imagen_b64).strip():
        return Response({'exito': False, 'error': "Falta el campo 'imagen_base64'."},
                        status=status.HTTP_400_BAD_REQUEST)

    # Acepta tanto base64 puro como data URI completa ("data:image/png;base64,....").
    imagen_b64 = str(imagen_b64).strip()
    if imagen_b64.startswith('data:') and ',' in imagen_b64:
        imagen_b64 = imagen_b64.split(',', 1)[1]

    try:
        ancho_max = int(data.get('ancho_max') or DEFAULT_ANCHO_MAX)
    except (TypeError, ValueError):
        ancho_max = DEFAULT_ANCHO_MAX
    try:
        calidad = int(data.get('calidad') or DEFAULT_CALIDAD)
    except (TypeError, ValueError):
        calidad = DEFAULT_CALIDAD

    try:
        raw = base64.b64decode(imagen_b64, validate=False)
    except Exception:
        return Response({'exito': False, 'error': "'imagen_base64' no es base64 valido."},
                        status=status.HTTP_400_BAD_REQUEST)

    if len(raw) > MAX_IMG_BYTES:
        return Response({'exito': False, 'error': 'Imagen demasiado grande.'},
                        status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    try:
        from PIL import Image  # type: ignore
    except Exception as e:  # noqa: BLE001
        log.error("Pillow no disponible: %s", e)
        return Response(
            {'exito': False, 'error': 'Reductor de imagenes no disponible en el servidor.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        # Corrige orientacion segun metadatos EXIF (fotos de celular).
        try:
            from PIL import ImageOps  # type: ignore
            img = ImageOps.exif_transpose(img)
        except Exception:  # noqa: BLE001
            pass

        if img.width > ancho_max:
            ratio = ancho_max / img.width
            img = img.resize((ancho_max, max(1, int(img.height * ratio))), Image.LANCZOS)

        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=calidad, optimize=True)
        out_bytes = buf.getvalue()
        out_b64 = base64.b64encode(out_bytes).decode('utf-8')

        log.info(
            "reducir_imagen: %.1fKB -> %.1fKB (%dx%d)",
            len(raw) / 1024, len(out_bytes) / 1024, img.width, img.height,
        )
        return Response({
            'exito': True,
            'imagen_base64': out_b64,
            'ancho': img.width,
            'alto': img.height,
            'peso_kb': round(len(out_bytes) / 1024, 1),
        }, status=status.HTTP_200_OK)
    except Exception as e:  # noqa: BLE001
        log.exception("Error reduciendo imagen")
        return Response({'exito': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
