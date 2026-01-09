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

@csrf_exempt
def obtener_instalaciones(request):
    if request.method == 'GET':
        instalaciones = Instalacion.objects.all().values('id', 'nombre', 'provincia', 'ciudad', 'cliente_id')
        return JsonResponse(list(instalaciones), safe=False)


@csrf_exempt
def crear_instalacion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(data)
        cliente_id = data.get('cliente_id')
        cliente = Cliente.objects.get(id=cliente_id)

        instalacion = Instalacion.objects.create(
            nombre=data.get('nombre_instalacion'),
            codigo=data.get('codigo'),
            cliente=cliente,
            ciudad=data.get('ciudad'),
            provincia=data.get('provincia'),
        )

        return JsonResponse({'message': 'Instalación creada', 'id': instalacion.id})