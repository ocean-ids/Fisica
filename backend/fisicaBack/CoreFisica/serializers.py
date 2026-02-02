from rest_framework import serializers
from .models import Asignacion, AsignacionSemanal

class AsignacionSerializer(serializers.ModelSerializer):
    
    persona_detalle = serializers.SerializerMethodField(read_only=True)
    cliente_detalle = serializers.SerializerMethodField(read_only=True)
    instalacion_detalle = serializers.SerializerMethodField(read_only=True)
    puesto_detalle = serializers.SerializerMethodField(read_only=True)
    horario_detalle = serializers.SerializerMethodField(read_only=True)
    fecha = serializers.DateField(required=False, allow_null=True)
    tipo = serializers.CharField(source='persona.tipo', read_only=True)


    def get_persona_detalle(self, obj):
        return {
            'id': obj.persona.id,
            'nombres': obj.persona.nombres,
            'apellidos': obj.persona.apellidos,
            'cedula': obj.persona.cedula,
            'tipo': obj.persona.tipo
        }
    
    def get_cliente_detalle(self, obj):
        return {
            'id': obj.cliente.id,
            'nombre_comercial': obj.cliente.nombre_comercial,
            'razon_social': obj.cliente.razon_social,
            'codigo': obj.cliente.codigo
        }
    
    def get_instalacion_detalle(self, obj):
        return {
            'id': obj.instalacion.id,
            'provincia': obj.instalacion.provincia,
            'ciudad': obj.instalacion.ciudad
        }
    
    def get_puesto_detalle(self, obj):
        return {
            'id': obj.puesto.id,
            'nombre': obj.puesto.nombre,
            'cantidad_guardias': obj.puesto.cantidad_guardias,
            'horas_trabajo': obj.puesto.horas_trabajo,
            'turno': obj.puesto.turno,
            'dias': obj.puesto.dias,
            'resumen': obj.puesto.resumen
        }
    
    
    def get_horario_detalle(self, obj):
        return {
            'id': obj.horario.id,
            'hora_ingreso': str(obj.horario.hora_ingreso),
            'hora_salida': str(obj.horario.hora_salida)
        }
    
    class Meta:
        model = Asignacion
        fields = '__all__'




class AsignacionSemanalSerializer(serializers.ModelSerializer):
    puesto_detalle = serializers.SerializerMethodField(read_only=True)

    def get_puesto_detalle(self, obj):
        p = obj.puesto
        return {
            'id': p.id,
            'nombre': p.nombre,
            'cantidad_guardias': p.cantidad_guardias,
            'horas_trabajo': p.horas_trabajo,
            'turno': p.turno,
            'dias': p.dias,
            'resumen': p.resumen,
        }

    class Meta:
        model = AsignacionSemanal
        fields = ['id', 'puesto', 'week_start', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'created_at', 'updated_at', 'puesto_detalle']

