from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import  Persona



@csrf_exempt
def crear_persona(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            persona = Persona.objects.create(
                nombres = data.get('nombres'),
                apellidos = data.get('apellidos'),
                cedula = data.get('cedula'),
                tipo = data.get('tipo'),
            )
            return JsonResponse({'message': 'Persona creada correctamente', 'id': persona.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'No se creo persona'}, status=400)     

@csrf_exempt
def obtener_personas(request):
    if request.method == 'GET':
        try:
            PersonasSinAsignacion = Persona.objects.filter(asignacion__isnull=True).order_by('apellidos')
            return JsonResponse(list(PersonasSinAsignacion.values('id', 'nombres', 'apellidos', 'cedula', 'tipo')), safe=False)
        except PersonasSinAsignacion.DoesNotExist:
            return JsonResponse({'error': 'No se encontraron personas'}, status=404)
        


@csrf_exempt
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

@csrf_exempt
def actualizar_persona(request, id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)

            try:
                persona = Persona.objects.get(id=id)
            except Persona.DoesNotExist:
                return JsonResponse({'error': 'Persona no encontrada'}, status=404)

            persona.nombres = data.get('nombres', persona.nombres)
            persona.apellidos = data.get('apellidos', persona.apellidos)
            persona.cedula = data.get('cedula', persona.cedula)
            persona.tipo = data.get('tipo', persona.tipo)

            persona.save()

            return JsonResponse({'message': 'Persona actualizada correctamente', 'id': persona.id})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)