from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from ..models import  Persona


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_persona(request):
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_personas(request):
    try:
        personas = Persona.objects.all().order_by('apellidos')
        return JsonResponse(list(personas.values('id', 'nombres', 'apellidos', 'cedula', 'tipo')), safe=False)
    except Exception:
        return JsonResponse({'error': 'No se encontraron personas'}, status=404)
        

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_persona(request, id):
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


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_persona(request, id):
    try:
        persona = Persona.objects.get(id=id)
        persona.delete()
        return JsonResponse({'message': 'Persona eliminada correctamente'}, status=200)
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona no encontrada'}, status=404)

            