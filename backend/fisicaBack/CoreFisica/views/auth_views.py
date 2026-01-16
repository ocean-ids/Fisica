from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
    })