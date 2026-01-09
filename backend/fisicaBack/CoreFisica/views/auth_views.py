from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        print("Datos recibidos:", request.body)
        
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
        except Exception as e:
            print("Error parseando JSON:", e)
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if not username or not password:
            return JsonResponse({"error": "Username and password required."}, status=400)

        print("Autenticando con:", username, password)
        user = authenticate(request, username=username, password=password)
        print("Usuario autenticado:", user)

        if user is not None:
            login(request, user)  # Crea sesión
            return JsonResponse({"message": "Login successful."})
        else:
            return JsonResponse({"error": "Invalid credentials."}, status=400)

    return JsonResponse({"error": "Only POST allowed."}, status=405)

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({"message": "Logout exitoso"}, status=200)
    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)

@csrf_exempt
def user_view(request):
    return JsonResponse({'username': request.user.username})
