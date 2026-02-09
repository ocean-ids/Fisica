from rest_framework import serializers
from .models import Asignacion, AsignacionSemanal, Instalacion, Puesto

class AsignacionSerializer(serializers.ModelSerializer):
    
    persona_detalle = serializers.SerializerMethodField(read_only=True)
    cliente_detalle = serializers.SerializerMethodField(read_only=True)
    instalacion_detalle = serializers.SerializerMethodField(read_only=True)
    puesto_detalle = serializers.SerializerMethodField(read_only=True)
    horario_detalle = serializers.SerializerMethodField(read_only=True)
    fecha = serializers.DateField(required=False, allow_null=True)
    tipo = serializers.CharField(source='persona.tipo', read_only=True)
    recurring = serializers.BooleanField(required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


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
            'ruc': getattr(obj.cliente, 'ruc', '') or ''
        }
    
    def get_instalacion_detalle(self, obj):
        inst = obj.instalacion
        return {
            'id': inst.id,
            'provincia': inst.provincia,
            'ciudad': inst.ciudad,
            'codigo': getattr(inst, 'codigo', '') or '',
            'direccion': getattr(inst, 'direccion', '') or ''
        }
    
    def get_puesto_detalle(self, obj):
        return {
            'id': obj.puesto.id,
            'nombre': obj.puesto.nombre,
            'cantidad_guardias': obj.puesto.cantidad_guardias,
            'horas_trabajo': obj.puesto.horas_trabajo,
            'turno': obj.puesto.turno,
            'turno_display': obj.puesto.get_turno_display(),
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
            'turno_display': p.get_turno_display(),
            'dias': p.dias,
            'resumen': p.resumen,
        }

    class Meta:
        model = AsignacionSemanal
        fields = ['id', 'puesto', 'week_start', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'created_at', 'updated_at', 'puesto_detalle']


class InstalacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instalacion
        fields = ['id', 'cliente', 'nombre', 'provincia', 'ciudad', 'codigo', 'direccion']
        read_only_fields = ['id']
        

class PuestoSerializer(serializers.ModelSerializer):
    turno_display = serializers.CharField(source='get_turno_display', read_only=True)

    class Meta:
        model = Puesto
        fields = ['id','instalacion','nombre','cantidad_guardias','horas_trabajo','turno','turno_display','dias','resumen']
        read_only_fields = ['id','turno_display']
    