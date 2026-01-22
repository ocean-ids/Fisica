from rest_framework import serializers
from .models import Asignacion

class AsignacionSerializer(serializers.ModelSerializer):
    
    persona_nombre = serializers.CharField(source='persona.__str__', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre_comercial', read_only=True)
    instalacion_ubicacion = serializers.SerializerMethodField(read_only=True)
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)
    horario_denominativo = serializers.CharField(source='horario.denominativo', read_only=True)

    def get_instalacion_ubicacion(self, obj):
        return f"{obj.instalacion.provincia} - {obj.instalacion.ciudad}"
    
    class Meta:
        model = Asignacion
        fields = '__all__'