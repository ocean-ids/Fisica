from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
import logging
import json
from ..models import UserProfile

logger = logging.getLogger(__name__)

# funcion get_photo_url que recibe un request y un profile, devuelve la url absoluta de la foto del perfil o None si no tiene foto
def _get_photo_url(request, profile: UserProfile | None):
    if not profile or not profile.photo:
        return None
    try:
        return request.build_absolute_uri(profile.photo.url)
    except Exception:
        return profile.photo.url

#funcion serialize_user que recibe un request y un ser y devuelve un diccionario con la informacion del usuario, incluyendo la url de la foto del perfil y los permisos
def _serialize_user(request, user: User):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    first = user.first_name or ''
    last = user.last_name or ''
    full = f"{first} {last}".strip()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": first,
        "last_name": last,
        "full_name": full,
        "photo_url": _get_photo_url(request, profile),
        "cargo": profile.cargo,
        "is_superuser": user.is_superuser,
        "groups": list(user.groups.values_list('name', flat=True)),
        "permissions": sorted(list(user.get_all_permissions())),
    }

#funcion get_client_ip que recibe un request y devuelve la ip del cliente, teniendo en cuenta posibles proxies
def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')

#csrf_exempt para permitir peticiones sin token csrf, recibe un request con username y password en el body, intenta autenticar al usuario y devuelve un token de acceso y refresh si es exitoso, o un error si no lo es
@csrf_exempt
#login_view que recibe un request con username y password en el body, intenta autenticar al usuario y devuelve un token de acceso y refresh si es exitoso, o un error si no lo es
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # si el usuario o la contraseña no se proporcionan, devolver error 400
        if not username or not password:
            return JsonResponse({"error": "Username and password required."}, status=400)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            
            refresh = RefreshToken.for_user(user)
            
            return JsonResponse({
                "message": "Login exitoso",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": _serialize_user(request, user)
            })
        else:
            return JsonResponse({"error": "Credenciales inválidas."}, status=400)

@csrf_exempt
#logout_view que recibe un request con un refresh token en el body, intenta invalidar el token y devuelve un mensaje de éxito o error  
def logout_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            refresh_token = data.get('refresh')
            
            
            if not refresh_token:
                return JsonResponse(
                    {"error": "Refresh token requerido."}, 
                    status=400
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return JsonResponse(
                {"message": "Logout exitoso"}, 
                status=200  
            )
            
        except Exception as e:
            return JsonResponse(
                {"error": f"Token inválido o expirado: {str(e)}"}, 
                status=400
            )
    else:

        return JsonResponse(
            {"error": "Método no permitido"}, 
            status=405
        )

#funcion user_view que recibe un request con un token de acceso valido, devuelve la información del usuario autenticado, incluyendo la url de la foto del perfil y los permisos
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_view(request):
    user = request.user
    return Response(_serialize_user(request, user))

#funcion user_profile_view que recibe un request con un token de acceso valido, permite actualizar la foto del perfil si se envía una nueva foto o se indica que se debe eliminar la foto actual, devuelve la información del usuario autenticado, incluyendo la url de la foto del perfil y los permisos
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def user_profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    #si el metodo es PUT, revisar si se debe eliminar la foto actual o actualizarla con una nueva foto enviada en el request, luego devolver la informacion del usuario autenticado, incluyendo la url de la foto del perfil y los permisos
    if request.method == 'PUT':
        remove = str(request.data.get('remove') or '').strip() == '1'
        if remove and profile.photo:
            profile.photo.delete(save=False)
            profile.photo = None
            profile.save(update_fields=['photo'])
        elif 'photo' in request.FILES:
            profile.photo = request.FILES['photo']
            profile.save(update_fields=['photo'])

    return Response({
        'photo_url': _get_photo_url(request, profile),
        'full_name': f"{request.user.first_name} {request.user.last_name}".strip(),
        'first_name': request.user.first_name or '',
        'last_name': request.user.last_name or '',
        'username': request.user.username,
        'email': request.user.email,
        'cargo': profile.cargo,
    })

# funcion solicitar_reset_password que recibe un request con un email en el body, si el email existe en el sistema, envía un correo con un enlace para restablecer la contraseña, el enlace incluye un token de seguridad que expira en 24 horas, devuelve un mensaje indicando que se ha enviado el correo si el email existe, o simplemente un mensaje genérico si no existe para evitar revelar información sobre los usuarios registrados
@api_view(['POST'])
def solicitar_reset_password(request):
    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})

    ip = _get_client_ip(request)
    cooldown_seconds = getattr(settings, 'RESET_PASSWORD_COOLDOWN_SECONDS', 60)
    max_per_hour = getattr(settings, 'RESET_PASSWORD_MAX_PER_HOUR', 5)
    cooldown_key = f"reset:cooldown:{email}:{ip}"
    hour_key = f"reset:hour:{email}:{ip}"
    # si el usuario ha solicitado un reset de contraseña recientemente, devolver un mensaje generico
    if cache.get(cooldown_key):
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})
    # limitar a un maximo de solicitudes por hora por email e ip para evitar abuso, si se supera el limite devolver un mensaje generico
    count = cache.get(hour_key, 0)
    if count >= max_per_hour:
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})
    # cachear la solicitud para evitar multiples solicitudes en un corto periodo de tiempo, y contar el numero de solicitudes por hora
    cache.set(cooldown_key, 1, timeout=cooldown_seconds)
    cache.set(hour_key, count + 1, timeout=3600)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})
    
    # generar token de restablecimiento de contraseña y uid para el usuario
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
   #
    base_url = getattr(settings, 'PASSWORD_RESET_BASE_URL', 'http://89.117.146.163').rstrip('/')
    reset_link = f"{base_url}/reset-password/{uid}/{token}"
    
    # enviar correo con el enlace de restablecimiento de contraseña, si hay un error al enviar el correo, registrar el error y devolver un mensaje generico si estamos en produccion, o el error detallado si estamos en modo debug para facilitar la depuración
    try:
        send_mail(
            subject='Restablecer contraseña - Sistema Física',
            message=f'Hola {user.username},\n\nHaz clic en el siguiente enlace para restablecer tu contraseña:\n\n{reset_link}\n\nEste enlace expira en 24 horas.\n\nSi no solicitaste este cambio, ignora este mensaje.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Password reset email sent to %s", email)
    except Exception as e:
        logger.error("Error sending password reset email", exc_info=e)
       
        if settings.DEBUG:
            return JsonResponse({'error': f'Error al enviar email: {str(e)}'}, status=500)
    
    return JsonResponse({'message': 'Si el email existe, recibirás un correo'})

# funcion reset_password que recibe un request con un nuevo password en el body, junto con el uid y token en la url, verifica que el token sea válido para el usuario correspondiente al uid, si es válido actualiza la contraseña del usuario y devuelve un mensaje de éxito, si no es válido devuelve un error indicando que el token es inválido o ha expirado
@api_view(['POST'])
def reset_password(request, uidb64, token):
   
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return JsonResponse({'error': 'Token inválido'}, status=400)
    

    if not default_token_generator.check_token(user, token):
        return JsonResponse({'error': 'Token expirado o inválido'}, status=400)
    
    nueva_password = request.data.get('password')
    user.set_password(nueva_password)
    user.save()
    
    return JsonResponse({'message': 'Contraseña actualizada correctamente'})