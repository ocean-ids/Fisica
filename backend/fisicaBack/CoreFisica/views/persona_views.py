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
from ..models import  Persona, Horario, Asignacion
from reportlab.pdfgen import canvas



@csrf_exempt
def crear_persona(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        persona = Persona.objects.create(
            nombres=data.get('nombres'),
            apellidos=data.get('apellidos'),
            cedula=data.get('cedula'),
            tipo=data.get('tipo'),
        )
        return JsonResponse({'message': 'Persona creada', 'id': persona.id})


@csrf_exempt
def actualizar_persona(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            persona_id = data.get('id')

            if not persona_id:
                return JsonResponse({'error': 'ID de persona no proporcionado'}, status=400)

            try:
                persona = Persona.objects.get(id=persona_id)
            except Persona.DoesNotExist:
                return JsonResponse({'error': 'Persona no encontrada'}, status=404)

            persona.nombres = data.get('nombres', persona.nombres)
            persona.apellidos = data.get('apellidos', persona.apellidos)
            persona.cedula = data.get('cedula', persona.cedula)
            persona.tipo = data.get('tipo', persona.tipo)

            persona.save()

            return JsonResponse({'message': 'Persona actualizado correctamente', 'id': persona.id})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)



@csrf_exempt
def obtener_personas(request):
    if request.method == 'GET':
        PersonasSinAsignacion = Persona.objects.filter(asignacion__isnull=True).order_by('apellidos')
        #personas = Persona.objects.all().values('id', 'nombres', 'apellidos', 'cedula','tipo')
        #return JsonResponse(list(personas), safe=False)
        return JsonResponse(list(PersonasSinAsignacion.values('id', 'nombres', 'apellidos','tipo')), safe=False)



def obtener_Persona(request,idPersona):


    personas = Persona.objects.raw("SELECT * FROM obtener_datosPersona(%s)",[idPersona])
    data = []

    for p in personas:
        data.append({
            "idPersona": p.id,
            "nombres":p.nombres,
            "apellidos":p.apellidos,
            "cedula":p.cedula,
            "tipo":p.tipo,
            
        })

    return JsonResponse(data, safe=False)