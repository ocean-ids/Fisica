# import datetime 
# from django.conf import settings
# from rest_framework.decorators import  api_view, permission_classes, authentication_classes
# from rest_framework.permissions import AllowAny
# from rest_framework.response import Response
# from rest_framework import status
# from ..models import Persona, Provincia, Canton

# def _fecha(v):
#     if not v:
#         return None
#     try:
#         return datetime.date.fromisoformat(str(v)[:10])
#     except (TypeError, ValueError):
#         return None

# @api_view(['POST'])
# @authentication_classes([])
# @permission_classes([AllowAny])
# def sincronizar_empleado(request):
#     auth = request.headers.get('Authoriz')
