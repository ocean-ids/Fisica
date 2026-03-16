from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import User
from django.conf import settings
import json


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
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "groups": list(user.groups.values_list('name', flat=True)),
                    "permissions": sorted(list(user.get_all_permissions())),
                }
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
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "groups": list(user.groups.values_list('name', flat=True)),
        'permissions': sorted(list(user.get_all_permissions())),
    })


@api_view(['POST'])
def solicitar_reset_password(request):

    email = request.data.get('email')
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        
        return JsonResponse({'message': 'Si el email existe, recibirás un correo'})
    
    
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
   
    reset_link = f"http://localhost:4200/reset-password/{uid}/{token}"
    
    
    try:
        send_mail(
            subject='Restablecer contraseña - Sistema Física',
            message=f'Hola {user.username},\n\nHaz clic en el siguiente enlace para restablecer tu contraseña:\n\n{reset_link}\n\nEste enlace expira en 24 horas.\n\nSi no solicitaste este cambio, ignora este mensaje.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f"✓ Email enviado exitosamente a {email}")
    except Exception as e:
        print(f"✗ ERROR al enviar email: {e}")
       
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