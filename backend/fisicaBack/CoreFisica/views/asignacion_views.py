from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import Asignacion

def obtener_asignaciones(request,mes,anio):
    asignaciones = Asignacion.objects.raw("SELECT * FROM obtener_asignaciones(%s, %s)",[mes, anio])
    data = []

    for a in asignaciones:
        data.append({
            "idAsignacion": a.id,
            "fecha_inicio": a.fecha_inicio,
            "fecha_fin": a.fecha_fin,
            "nombres":a.nombres,
            "apellidos":a.apellidos,
            "cedula":a.cedula,
            "denominativo":a.denominativo,
            "horaingreso":a.horaingreso,
            "horasalida":a.horasalida,
            "nombreinstalacion":a.nombreinstalacion,
            "codigo":a.codigo,
            "razonSocial":a.razonsocial,
            "nombrePuesto":a.nombrepuesto,
            "dia_1": a.dia_1,
            "dia_2": a.dia_2 ,
            "dia_3": a.dia_3 ,
            "dia_4": a.dia_4 ,
            "dia_5": a.dia_5 ,
            "dia_6": a.dia_6 ,
            "dia_7": a.dia_7 ,
            "dia_8": a.dia_8 ,
            "dia_9": a.dia_9 ,
            "dia_10": a.dia_10 ,
            "dia_11": a.dia_11 ,
            "dia_12": a.dia_12 ,
            "dia_13": a.dia_13 ,
            "dia_14": a.dia_14 ,
            "dia_15": a.dia_15 ,
            "dia_16": a.dia_16 ,
            "dia_17": a.dia_17 ,
            "dia_18": a.dia_18 ,
            "dia_19": a.dia_19 ,
            "dia_20": a.dia_20 ,
            "dia_21": a.dia_21 ,
            "dia_22": a.dia_22 ,
            "dia_23": a.dia_23 ,
            "dia_24": a.dia_24 ,
            "dia_25": a.dia_25 ,
            "dia_26": a.dia_26 ,
            "dia_27": a.dia_27 ,
            "dia_28": a.dia_28 ,
            "dia_29": a.dia_29 ,
            "dia_30": a.dia_30 ,
            "dia_31": a.dia_31 ,
            "mes": a.mes,
            "anio": a.anio,
            "rotativo": a.rotativo,
            "orden": a.orden,
            "estado": a.estado,
            
        })
    print(data)
    return JsonResponse(data, safe=False)


@csrf_exempt
def asignar_servicio(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print("daniel22: ",data)
        variableContar=Asignacion.objects.count()+1
        asignacion = Asignacion.objects.create(
            fecha_inicio=data.get('fecha_inicio'),
            fecha_fin=data.get('fecha_fin'),
            cliente_id=data.get('cliente_id'),
            horario_id=data.get('horario_id'),
            instalacion_id=data.get('instalacion_id'),
            puesto_id=data.get('puesto_id'),
            persona_id=data.get('persona_id'),
            rotativo=data.get('rotativo'),
            mes=data.get('mes'),
            anio=data.get('anio'),
            orden=variableContar,
            estado=data.get('estado'),
            tipo=data.get('tipo')
        )
        return JsonResponse({'message': 'Servicio asignado', 'id': asignacion.id})



@csrf_exempt
def editar_servicio(request, id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            asignacion = Asignacion.objects.get(id=id)

            asignacion.fecha_inicio = data.get('fecha_inicio', asignacion.fecha_inicio)
            asignacion.fecha_fin = data.get('fecha_fin', asignacion.fecha_fin)
            asignacion.cliente_id = data.get('cliente_id', asignacion.cliente_id)
            asignacion.horario_id = data.get('horario_id', asignacion.horario_id)
            asignacion.instalacion_id = data.get('instalacion_id', asignacion.instalacion_id)
            asignacion.puesto_id = data.get('puesto_id', asignacion.puesto_id)
            asignacion.persona_id = data.get('persona_id', asignacion.persona_id)
            asignacion.rotativo = data.get('rotativo', asignacion.rotativo)
            asignacion.mes = data.get('mes', asignacion.mes)
            asignacion.anio = data.get('anio', asignacion.anio)
            asignacion.estado = data.get('estado', asignacion.estado)

            asignacion.save()

            return JsonResponse({'message': 'Asignación actualizada correctamente'})

        except Asignacion.DoesNotExist:
            return JsonResponse({'error': 'La asignación no existe'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def guardar_orden_asignacion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids_orden = data.get('orden')
        print("ids_orden",ids_orden)
        for index, id in enumerate(ids_orden):
            Asignacion.objects.filter(id=id).update(orden=index)

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)