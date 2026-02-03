from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from ..models import Asignacion, AsignacionSemanal, Puesto
from ..serializers import AsignacionSerializer
import openpyxl
import datetime


@api_view(['GET'])
def obtener_asignaciones(request, mes=None, anio=None):
    if mes and anio:
        asignaciones = Asignacion.objects.filter(
            mes=mes,
            anio=anio,
            estado='ACTIVO'
        ).select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario')
    else:
        asignaciones = Asignacion.objects.filter(
            estado='ACTIVO'
        ).select_related('persona', 'cliente', 'instalacion', 'puesto', 'horario')
    
    serializer = AsignacionSerializer(asignaciones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def asignar_servicio(request):
    print(f"📥 Datos recibidos: {request.data}")
    serializer = AsignacionSerializer(data=request.data)
    if serializer.is_valid():
        asignacion = serializer.save()

        # Crear filas de AsignacionSemanal para el puesto en las semanas del mes/año de la asignación
        try:
            mes = int(asignacion.mes)
            anio = int(asignacion.anio)
            first_day = datetime.date(anio, mes, 1)
            if mes == 12:
                next_month_first = datetime.date(anio + 1, 1, 1)
            else:
                next_month_first = datetime.date(anio, mes + 1, 1)
            last_day = next_month_first - datetime.timedelta(days=1)

            # encontrar el primer lunes en o después del primer día (lunes=0)
            # datetime.weekday(): Monday=0 .. Sunday=6
            offset = (0 - first_day.weekday()) % 7
            current = first_day + datetime.timedelta(days=offset)

            # Normalización de nombres de días en español (lunes..domingo)
            weekday_names = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']

            # Obtener instancia de Puesto (por si asignacion.puesto es id)
            puesto_obj = None
            try:
                puesto_obj = getattr(asignacion, 'puesto')
                # si es un id (int), obtener el objeto
                if isinstance(puesto_obj, int) or isinstance(puesto_obj, str):
                    puesto_obj = Puesto.objects.get(id=int(puesto_obj))
            except Exception:
                try:
                    puesto_obj = Puesto.objects.get(id=asignacion.puesto_id)
                except Exception:
                    puesto_obj = None

            dias_puesto = []
            if puesto_obj:
                try:
                    dias_puesto = puesto_obj.dias or []
                except Exception:
                    dias_puesto = []

            # Normalizar y mapear diferentes formatos de días a nombres completos
            def normalize_day_token(tok: str) -> str:
                t = str(tok).strip().lower()
                if not t:
                    return ''
                map_short = {
                    'l': 'lunes', 'lu': 'lunes', 'lun': 'lunes', 'lunes': 'lunes',
                    'm': 'martes', 'ma': 'martes', 'mar': 'martes', 'martes': 'martes',
                    'mi': 'miercoles', 'mie': 'miercoles', 'miercoles': 'miercoles', 'miércoles':'miercoles',
                    'j': 'jueves', 'ju': 'jueves', 'jue': 'jueves', 'jueves': 'jueves',
                    'v': 'viernes', 'vi': 'viernes', 'vie': 'viernes', 'viernes': 'viernes',
                    's': 'sabado', 'sa': 'sabado', 'sab': 'sabado', 'sabado': 'sabado', 'sábado': 'sabado',
                    'd': 'domingo', 'do': 'domingo', 'dom': 'domingo', 'domingo': 'domingo'
                }
                return map_short.get(t, t)

            dias_norm = [normalize_day_token(d) for d in dias_puesto if d]
            turno = (getattr(puesto_obj, 'turno', '') or '').strip().lower() if puesto_obj else ''
            default_code = 'N' if turno.startswith('n') else 'D'

            while current <= last_day:
                # construir valores por día según dias_norm
                defaults = {}
                for idx, name in enumerate(weekday_names):
                    key = ['mon','tue','wed','thu','fri','sat','sun'][idx]
                    match = any(name == d or d in name or name in d for d in dias_norm)
                    defaults[key] = default_code if match else ''

                AsignacionSemanal.objects.get_or_create(
                    puesto=puesto_obj,
                    week_start=current,
                    defaults=defaults
                )
                current += datetime.timedelta(days=7)
        except Exception as e:
            print(f"⚠️ Error creando AsignacionSemanal: {e}")

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    # Si hay error de unicidad (persona, mes, anio) intentamos actualizar la asignación existente
    print(f"❌ Errores de validación: {serializer.errors}")
    try:
        errs = serializer.errors or {}
        nonf = errs.get('non_field_errors') if isinstance(errs, dict) else None
        is_unique = False
        if nonf:
            for e in nonf:
                if 'unique' in str(e).lower() or 'únic' in str(e).lower():
                    is_unique = True
                    break
        if is_unique:
            persona = request.data.get('persona')
            mes = request.data.get('mes')
            anio = request.data.get('anio')
            if persona and mes and anio:
                existing = Asignacion.objects.filter(persona_id=persona, mes=mes, anio=anio).first()
                if existing:
                    # actualizar la asignación existente con los nuevos datos
                    serializer2 = AsignacionSerializer(existing, data=request.data, partial=True)
                    if serializer2.is_valid():
                        asignacion = serializer2.save()
                        # crear/actualizar filas semanales también
                        try:
                            mes = int(asignacion.mes)
                            anio = int(asignacion.anio)
                            first_day = datetime.date(anio, mes, 1)
                            if mes == 12:
                                next_month_first = datetime.date(anio + 1, 1, 1)
                            else:
                                next_month_first = datetime.date(anio, mes + 1, 1)
                            last_day = next_month_first - datetime.timedelta(days=1)
                            offset = (0 - first_day.weekday()) % 7
                            current = first_day + datetime.timedelta(days=offset)
                            # reuse puesto_obj resolution
                            puesto_obj = None
                            try:
                                puesto_obj = getattr(asignacion, 'puesto')
                                if isinstance(puesto_obj, int) or isinstance(puesto_obj, str):
                                    puesto_obj = Puesto.objects.get(id=int(puesto_obj))
                            except Exception:
                                try:
                                    puesto_obj = Puesto.objects.get(id=asignacion.puesto_id)
                                except Exception:
                                    puesto_obj = None

                            dias_puesto = []
                            if puesto_obj:
                                try:
                                    dias_puesto = puesto_obj.dias or []
                                except Exception:
                                    dias_puesto = []

                            def normalize_day_token(tok: str) -> str:
                                t = str(tok).strip().lower()
                                if not t:
                                    return ''
                                map_short = {
                                    'l': 'lunes', 'lu': 'lunes', 'lun': 'lunes', 'lunes': 'lunes',
                                    'm': 'martes', 'ma': 'martes', 'mar': 'martes', 'martes': 'martes',
                                    'mi': 'miercoles', 'mie': 'miercoles', 'miercoles': 'miercoles', 'miércoles':'miercoles',
                                    'j': 'jueves', 'ju': 'jueves', 'jue': 'jueves', 'jueves': 'jueves',
                                    'v': 'viernes', 'vi': 'viernes', 'vie': 'viernes', 'viernes': 'viernes',
                                    's': 'sabado', 'sa': 'sabado', 'sab': 'sabado', 'sabado': 'sabado', 'sábado': 'sabado',
                                    'd': 'domingo', 'do': 'domingo', 'dom': 'domingo', 'domingo': 'domingo'
                                }
                                return map_short.get(t, t)

                            dias_norm = [normalize_day_token(d) for d in dias_puesto if d]
                            turno = (getattr(puesto_obj, 'turno', '') or '').strip().lower() if puesto_obj else ''
                            default_code = 'N' if turno.startswith('n') else 'D'

                            weekday_names = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
                            while current <= last_day:
                                defaults = {}
                                for idx, name in enumerate(weekday_names):
                                    key = ['mon','tue','wed','thu','fri','sat','sun'][idx]
                                    match = any(name == d or d in name or name in d for d in dias_norm)
                                    defaults[key] = default_code if match else ''
                                AsignacionSemanal.objects.get_or_create(
                                    puesto=puesto_obj,
                                    week_start=current,
                                    defaults=defaults
                                )
                                current += datetime.timedelta(days=7)
                        except Exception as e:
                            print(f"⚠️ Error creando AsignacionSemanal al actualizar: {e}")
                        return Response(serializer2.data, status=status.HTTP_200_OK)
                    else:
                        return Response(serializer2.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        pass

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def editar_servicio(request, id):
    try:
        asignacion = Asignacion.objects.get(id=id)
    except Asignacion.DoesNotExist:
        return Response({'error': 'Asignación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AsignacionSerializer(asignacion, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def guardar_orden_asignacion(request):
    ordenes = request.data.get('ordenes', [])

    for item in ordenes:
        try:
            asignacion = Asignacion.objects.get(id=item['id'])
            asignacion.orden = item['orden']
            asignacion.save()
        except Asignacion.DoesNotExist:
            continue
    return Response({'mensaje': 'Orden actualizado correctamente'})

@api_view(['DELETE'])
def eliminar_asignacion(request, id):
    try:
        asignar = Asignacion.objects.get(id=id)
        asignar.delete()
        return Response({'mensaje': 'Asignación eliminada correctamente'}, status=status.HTTP_204_NO_CONTENT)
    except Asignacion.DoesNotExist:
        return Response({'error': 'Asignacion no encontrada'}, status=status.HTTP_404_NOT_FOUND)


def exportar_asignaciones_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asignaciones"

    
    ws.append(['Horario', 'Código Cliente', 'Cliente', 'Nombre Puesto', 'Cantidad de Guardias', 'Horas de Trabajo', 'Cédula', 'Persona', 'Tipo'])

    for asignacion in Asignacion.objects.all():
        ws.append([
            f"{asignacion.horario.hora_ingreso} - {asignacion.horario.hora_salida}",
            asignacion.cliente.codigo,  
            asignacion.cliente.nombre_comercial,
            asignacion.puesto.nombre,
            asignacion.puesto.cantidad_guardias,
            asignacion.puesto.horas_trabajo,
            asignacion.persona.cedula,
            f"{asignacion.persona.apellidos} {asignacion.persona.nombres}",
            asignacion.persona.tipo
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reporte_asignaciones.xlsx'
    wb.save(response)
    return response