from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
import json
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from ..models import Cliente, Instalacion, Puesto, Persona, Horario, Asignacion
from reportlab.pdfgen import canvas


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_puesto(request):
    data = json.loads(request.body)
    instalacion_id = data.get('instalacion_id')
    instalacion = Instalacion.objects.get(id=instalacion_id)
    puesto = Puesto.objects.create(
        nombre=data.get('nombre'),
        instalacion_id=instalacion.id
    )
    return JsonResponse({'message': 'Puesto creado', 'id': puesto.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_puestos(request):
    puestos = Puesto.objects.all().values('id', 'nombre', 'instalacion_id')
    return JsonResponse(list(puestos), safe=False)