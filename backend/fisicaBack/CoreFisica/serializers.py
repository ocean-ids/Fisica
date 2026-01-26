from rest_framework import serializers
from .models import Asignacion, AsignacionCalendario

class AsignacionSerializer(serializers.ModelSerializer):
    
    persona_detalle = serializers.SerializerMethodField(read_only=True)
    cliente_detalle = serializers.SerializerMethodField(read_only=True)
    instalacion_detalle = serializers.SerializerMethodField(read_only=True)
    puesto_detalle = serializers.SerializerMethodField(read_only=True)
    horario_detalle = serializers.SerializerMethodField(read_only=True)

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
            'razon_social': obj.cliente.razon_social
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
            'nombre': obj.puesto.nombre
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

class AsignacionCalendarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionCalendario
        fields = '__all__'
    