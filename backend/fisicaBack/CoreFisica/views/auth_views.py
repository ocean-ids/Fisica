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


def _get_photo_url(request, profile: UserProfile | None):
    if not profile or not profile.photo:
        return None
    try:
        return request.build_absolute_uri(profile.photo.url)
    except Exception:
        return profile.photo.url


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


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_view(request):
    user = request.user
    return Response(_serialize_user(request, user))


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def user_profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

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

    if cache.get(cooldown_key):
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})

    count = cache.get(hour_key, 0)
    if count >= max_per_hour:
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})

    cache.set(cooldown_key, 1, timeout=cooldown_seconds)
    cache.set(hour_key, count + 1, timeout=3600)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})
    
    
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
   
    base_url = getattr(settings, 'PASSWORD_RESET_BASE_URL', 'http://localhost:4200').rstrip('/')
    reset_link = f"{base_url}/reset-password/{uid}/{token}"
    
    
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