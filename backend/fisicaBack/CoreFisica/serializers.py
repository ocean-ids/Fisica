from rest_framework import serializers
from django.db import transaction
from django.core.validators import RegexValidator
from .models import Asignacion, AsignacionSemanal, Instalacion, Puesto, PuestoHorario, PatronAsignacion
from .utils import parse_input



class PatronAsignacionSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(
        max_length=4,
        validators=[RegexValidator(regex=r'^\d{3,4}$', message='Use 3 o 4 dígitos')]
    )
    def validate_secuencia(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("La secuencia debe ser una lista no vacía")
        if len(value) > 7:
            raise serializers.ValidationError("La secuencia puede tener como máximo 7 símbolos")
        allowed = {"D", "N", "F"}
        cleaned = []
        for token in value:
            t = str(token).strip().upper()
            if t not in allowed:
                raise serializers.ValidationError(f"Símbolo no permitido: {token}")
            cleaned.append(t)
        return cleaned

    class Meta:
        model = PatronAsignacion
        fields = ['id', 'codigo', 'secuencia']


class AsignacionSerializer(serializers.ModelSerializer):
    persona_detalle = serializers.SerializerMethodField(read_only=True)
    cliente_detalle = serializers.SerializerMethodField(read_only=True)
    instalacion_detalle = serializers.SerializerMethodField(read_only=True)
    puesto_detalle = serializers.SerializerMethodField(read_only=True)
    horario_detalle = serializers.SerializerMethodField(read_only=True)
    patron_detalle = PatronAsignacionSerializer(source='patronAsignacion', read_only=True)
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
            'ruc': getattr(obj.cliente, 'ruc', '') or '',
            'size': getattr(obj.cliente, 'size', None)
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
            'turno': obj.puesto.get_turno(),
            'turno_display': obj.puesto.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in obj.puesto.horarios.all()],
            'resumen': obj.puesto.resumen
        }

    def get_horario_detalle(self, obj):
        return {
            'id': obj.horario.id,
            'hora_ingreso': str(obj.horario.hora_ingreso),
            'hora_salida': str(obj.horario.hora_salida),
        }

    # patron_detalle ahora es serializado automáticamente por PatronAsignacionSerializer

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
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
            'resumen': p.resumen,
        }

    class Meta:
        model = AsignacionSemanal
        fields = ['id', 'puesto', 'week_start', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'created_at', 'updated_at', 'puesto_detalle']

class PatronAsignacionSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(
        max_length=4,
        validators=[RegexValidator(regex=r'^\d{3,4}$', message='Use 3 o 4 dígitos')]
    )
    def validate_secuencia(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("La secuencia debe ser una lista no vacía")
        if len(value) > 7:
            raise serializers.ValidationError("La secuencia puede tener como máximo 7 símbolos")
        allowed = {"D", "N", "F"}
        cleaned = []
        for token in value:
            t = str(token).strip().upper()
            if t not in allowed:
                raise serializers.ValidationError(f"Símbolo no permitido: {token}")
            cleaned.append(t)
        return cleaned

    class Meta:
        model = PatronAsignacion
        fields = ['id', 'codigo', 'secuencia']

class InstalacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instalacion
        fields = ['id', 'cliente', 'nombre', 'provincia', 'ciudad', 'codigo', 'direccion']
        read_only_fields = ['id']
        

class PuestoHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuestoHorario
        fields = ('id', 'dia', 'horas', 'turno')

class PuestoSerializer(serializers.ModelSerializer):
    horarios = PuestoHorarioSerializer(many=True, required=False)
    horarios_text = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Puesto
        fields = ('id', 'instalacion', 'nombre', 'tipo', 'cantidad_guardias',
                  'resumen', 'horarios')

    def create(self, validated_data):
        text = validated_data.pop('horarios_text', None)
        horarios_data = validated_data.pop('horarios', [])
        if text:
            try:
                parsed = parse_input(text)
                horarios_data = [
                    {
                        "dia": r["dia"],
                        "horas": r["horas"],
                        "turno": r.get("turno", "Diurno"),
                    }
                    for r in parsed
                ]
            except ValueError as e:
                raise serializers.ValidationError({"horarios_text": str(e)})
        with transaction.atomic():
            puesto = Puesto.objects.create(**validated_data)
            for h in horarios_data:
                PuestoHorario.objects.create(
                    puesto=puesto,
                    dia=h.get('dia'),
                    horas=h.get('horas') if h.get('horas') is not None else 12,
                    turno=h.get('turno', 'Diurno')
                )
            # sincronizar campos derivados desde los horarios creados
            try:
                puesto.sync_from_horarios()
                puesto.save()
            except Exception:
                pass
        return puesto

    def update(self, instance, validated_data):
        text = validated_data.pop('horarios_text', None)
        horarios_data = validated_data.pop('horarios', None)
        if text:
            try:
                parsed = parse_input(text)
                horarios_data = [
                    {
                        "dia": r["dia"],
                        "horas": r["horas"],
                        "turno": r.get("turno", "Diurno"),
                    }
                    for r in parsed
                ]
            except ValueError as e:
                raise serializers.ValidationError({"horarios_text": str(e)})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        with transaction.atomic():
            instance.save()
            if horarios_data is not None:
                instance.horarios.all().delete()
                for h in horarios_data:
                    PuestoHorario.objects.create(
                        puesto=instance,
                        dia=h.get('dia'),
                        horas=h.get('horas') if h.get('horas') is not None else 12,
                        turno=h.get('turno', 'Diurno')
                    )
            
            try:
                instance.sync_from_horarios()
                instance.save()
            except Exception:
                pass
        return instance