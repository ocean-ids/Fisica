from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
from datetime import date
import calendar
from ..models import Asignacion, Asistencia

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_asignaciones(request, mes, anio):
    """
    Obtiene asignaciones con sus asistencias para el mes/año especificado
    """
    asignaciones = Asignacion.objects.filter(mes=mes, anio=anio).select_related(
        'persona', 'cliente', 'instalacion', 'puesto', 'horario'
    ).prefetch_related('asistencias')
    
    data = []
    
    # Obtener número de días del mes
    num_dias = calendar.monthrange(int(anio), int(mes))[1]

    for asignacion in asignaciones:
        # Construir diccionario de asistencias por día
        asistencias_dict = {}
        for asistencia in asignacion.asistencias.all():
            dia = asistencia.fecha.day
            # Formato similar al anterior: "D", "N", "DS30", etc.
            valor = ""
            if asistencia.turno:
                valor += asistencia.turno
            if asistencia.codigo_cliente:
                valor += asistencia.codigo_cliente
            if asistencia.estado == 'FRANCO':
                valor += 'F'
            elif asistencia.estado == 'DISPONIBLE':
                valor += 'DISP'
            
            asistencias_dict[dia] = valor
        
        # Construir objeto con estructura compatible
        asignacion_data = {
            "idAsignacion": asignacion.id,
            "fecha_inicio": asignacion.fecha_inicio.isoformat(),
            "fecha_fin": asignacion.fecha_fin.isoformat() if asignacion.fecha_fin else None,
            "nombres": asignacion.persona.nombres,
            "apellidos": asignacion.persona.apellidos,
            "cedula": asignacion.persona.cedula,
            "denominativo": asignacion.horario.denominativo,
            "horaingreso": asignacion.horario.hora_ingreso.isoformat(),
            "horasalida": asignacion.horario.hora_salida.isoformat(),
            "nombreinstalacion": asignacion.instalacion.nombre,
            "codigo": asignacion.cliente.codigo or "",
            "razonSocial": asignacion.cliente.razon_social,
            "nombrePuesto": asignacion.puesto.nombre,
            "mes": asignacion.mes,
            "anio": asignacion.anio,
            "rotativo": asignacion.rotativo,
            "orden": asignacion.orden,
            "estado": asignacion.estado,
        }
        
        # Agregar días del mes
        for dia in range(1, num_dias + 1):
            asignacion_data[f"dia_{dia}"] = asistencias_dict.get(dia, "")
        
        # Agregar días restantes como vacíos si el mes tiene menos de 31 días
        for dia in range(num_dias + 1, 32):
            asignacion_data[f"dia_{dia}"] = ""
        
        data.append(asignacion_data)
    
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_servicio(request):
    """
    Crea una asignación con sus registros de asistencia
    """
    data = json.loads(request.body)
    print("Datos recibidos: ", data)
    
    variableContar = Asignacion.objects.count() + 1
    mes = int(data.get('mes'))
    anio = int(data.get('anio'))
    
    # Crear la asignación
    asignacion = Asignacion.objects.create(
        fecha_inicio=data.get('fecha_inicio'),
        fecha_fin=data.get('fecha_fin'),
        cliente_id=data.get('cliente_id'),
        horario_id=data.get('horario_id'),
        instalacion_id=data.get('instalacion_id'),
        puesto_id=data.get('puesto_id'),
        persona_id=data.get('persona_id'),
        rotativo=data.get('rotativo', False),
        mes=mes,
        anio=anio,
        orden=variableContar,
        estado=data.get('estado', 'ACTIVO')
    )
    
    # Crear registros de asistencia si vienen datos de días
    num_dias = calendar.monthrange(anio, mes)[1]
    for dia in range(1, num_dias + 1):
        valor_dia = data.get(f'dia_{dia}')
        if valor_dia:
            # Parsear el valor (ej: "D", "N", "DS30", "NF", etc.)
            turno = None
            codigo_cliente = None
            estado_dia = 'NORMAL'
            
            valor = str(valor_dia).strip().upper()
            
            # Detectar turno
            if valor.startswith('D'):
                turno = 'D'
                resto = valor[1:]
            elif valor.startswith('N'):
                turno = 'N'
                resto = valor[1:]
            else:
                resto = valor
            
            # Detectar estado
            if 'F' in resto or resto == 'F':
                estado_dia = 'FRANCO'
                resto = resto.replace('F', '')
            elif 'DISP' in resto:
                estado_dia = 'DISPONIBLE'
                resto = resto.replace('DISP', '')
            
            # Extraer código cliente (ej: S30)
            if resto.strip():
                codigo_cliente = resto.strip()
            
            # Crear fecha
            fecha_asistencia = date(anio, mes, dia)
            
            # Crear asistencia
            Asistencia.objects.create(
                asignacion=asignacion,
                fecha=fecha_asistencia,
                turno=turno,
                codigo_cliente=codigo_cliente,
                estado=estado_dia
            )
    
    return JsonResponse({'message': 'Servicio asignado', 'id': asignacion.id})



@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def editar_servicio(request, id):
    """
    Edita una asignación y actualiza sus asistencias
    """
    try:
        data = json.loads(request.body)
        asignacion = Asignacion.objects.get(id=id)

        # Actualizar campos básicos
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
        
        # Actualizar asistencias si vienen datos de días
        mes = int(asignacion.mes)
        anio = int(asignacion.anio)
        num_dias = calendar.monthrange(anio, mes)[1]
        
        for dia in range(1, num_dias + 1):
            dia_key = f'dia_{dia}'
            if dia_key in data:
                valor_dia = data.get(dia_key)
                fecha_asistencia = date(anio, mes, dia)
                
                if valor_dia:
                    # Parsear el valor
                    turno = None
                    codigo_cliente = None
                    estado_dia = 'NORMAL'
                    
                    valor = str(valor_dia).strip().upper()
                    
                    if valor.startswith('D'):
                        turno = 'D'
                        resto = valor[1:]
                    elif valor.startswith('N'):
                        turno = 'N'
                        resto = valor[1:]
                    else:
                        resto = valor
                    
                    if 'F' in resto or resto == 'F':
                        estado_dia = 'FRANCO'
                        resto = resto.replace('F', '')
                    elif 'DISP' in resto:
                        estado_dia = 'DISPONIBLE'
                        resto = resto.replace('DISP', '')
                    
                    if resto.strip():
                        codigo_cliente = resto.strip()
                    
                    # Actualizar o crear asistencia
                    Asistencia.objects.update_or_create(
                        asignacion=asignacion,
                        fecha=fecha_asistencia,
                        defaults={
                            'turno': turno,
                            'codigo_cliente': codigo_cliente,
                            'estado': estado_dia
                        }
                    )
                else:
                    # Si el valor está vacío, eliminar la asistencia si existe
                    Asistencia.objects.filter(
                        asignacion=asignacion,
                        fecha=fecha_asistencia
                    ).delete()

        return JsonResponse({'message': 'Asignación actualizada correctamente'})

    except Asignacion.DoesNotExist:
        return JsonResponse({'error': 'La asignación no existe'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def guardar_orden_asignacion(request):
    data = json.loads(request.body)
    ids_orden = data.get('orden')
    print("ids_orden",ids_orden)
    for index, id in enumerate(ids_orden):
        Asignacion.objects.filter(id=id).update(orden=index)

    return JsonResponse({'status': 'ok'})