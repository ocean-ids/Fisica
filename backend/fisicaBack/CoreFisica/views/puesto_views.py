from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from ..models import Cliente, Instalacion, Puesto, Persona, Horario, Asignacion
from reportlab.pdfgen import canvas


@csrf_exempt
def crear_puesto(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        instalacion_id = data.get('instalacion_id')
        instalacion = Instalacion.objects.get(id=instalacion_id)
        puesto = Puesto.objects.create(
            nombre=data.get('nombre'),
            instalacion_id=instalacion.id
        )
        return JsonResponse({'message': 'Puesto creado', 'id': puesto.id})


@csrf_exempt
def obtener_puestos(request):
    if request.method == 'GET':
        puestos = Puesto.objects.all().values('id', 'nombre', 'instalacion_id')
        return JsonResponse(list(puestos), safe=False)