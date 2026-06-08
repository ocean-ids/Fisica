from rest_framework import serializers
from django.db import transaction
from django.core.validators import RegexValidator
from .utils import parse_input
from .models import Asignacion, AsignacionSemanal, Instalacion, Persona, Provincia, Puesto, PuestoHorario, PatronAsignacion, SacafrancoFila, SacafrancoFilaSemanal


class PatronAsignacionSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(
        max_length=4,
        validators=[RegexValidator(regex=r'^\d{2,4}$', message='Use 2 a 4 dígitos')]
    )

    def validate_secuencia(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("La secuencia debe ser una lista no vacía")
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
    cedula_color = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def get_persona_detalle(self, obj):
        return {
            'id': obj.persona.id,
            'nombres': obj.persona.nombres,
            'apellidos': obj.persona.apellidos,
            'cedula': obj.persona.cedula,
            'tipo': obj.persona.tipo,
            'provincia': obj.persona.provincia_id,
            'canton': obj.persona.canton_id
        }

    def get_cliente_detalle(self, obj):
        return {
            'id': obj.cliente.id,
            'nombre_comercial': obj.cliente.nombre_comercial,
            'razon_social': obj.cliente.razon_social,
            'ruc': getattr(obj.cliente, 'ruc', '') or '',
            'size': getattr(obj.cliente, 'size', None),
            'fecha_ingreso': obj.cliente.fecha_ingreso.isoformat() if obj.cliente.fecha_ingreso else None,
            'fecha_retiro': obj.cliente.fecha_retiro.isoformat() if obj.cliente.fecha_retiro else None,
        }

    def get_instalacion_detalle(self, obj):
        inst = obj.instalacion
        return {
            'id': inst.id,
            'codigo': getattr(inst, 'codigo', '') or '',
            'canton_id': inst.canton_id,
            'canton_nombre': getattr(inst.canton, 'nombre', ''),
            'provincia_id': getattr(inst.canton, 'provincia_id', None),
            'provincia_nombre': getattr(getattr(inst.canton, 'provincia', None), 'nombre', ''),
            'direccion': getattr(inst, 'direccion', '') or ''
        }

    def get_puesto_detalle(self, obj):
        return {
            'id': obj.puesto.id,
            'nombre': obj.puesto.nombre,
            'cantidad_puestos': obj.puesto.cantidad_puestos,
            'zona_id': getattr(obj.puesto, 'zona_id', None),
            'zona_titulo': getattr(getattr(obj.puesto, 'zona', None), 'titulo', ''),
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


class AsignacionLiteSerializer(serializers.ModelSerializer):
    persona_detalle = serializers.SerializerMethodField(read_only=True)
    cliente_detalle = serializers.SerializerMethodField(read_only=True)
    instalacion_detalle = serializers.SerializerMethodField(read_only=True)
    puesto_detalle = serializers.SerializerMethodField(read_only=True)
    horario_detalle = serializers.SerializerMethodField(read_only=True)
    fecha = serializers.DateField(required=False, allow_null=True)
    recurring = serializers.BooleanField(required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    cedula_color = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def get_persona_detalle(self, obj):
        return {
            'id': obj.persona.id,
            'nombres': obj.persona.nombres,
            'apellidos': obj.persona.apellidos,
            'cedula': obj.persona.cedula,
            'tipo': obj.persona.tipo,
            'provincia': obj.persona.provincia_id,
            'canton': obj.persona.canton_id,
            'is_active': getattr(obj.persona, 'is_active', True)
        }

    def get_cliente_detalle(self, obj):
        return {
            'id': obj.cliente.id,
            'nombre_comercial': obj.cliente.nombre_comercial,
        }

    def get_instalacion_detalle(self, obj):
        inst = obj.instalacion
        return {
            'id': inst.id,
            'codigo': getattr(inst, 'codigo', '') or '',
            'canton_id': getattr(inst, 'canton_id', None),
            'canton_nombre': getattr(getattr(inst, 'canton', None), 'nombre', ''),
            'provincia_id': getattr(inst.canton, 'provincia_id', None),
            'provincia_nombre': getattr(getattr(inst.canton, 'provincia', None), 'nombre', ''),
        }

    def get_puesto_detalle(self, obj):
        return {
            'id': obj.puesto.id,
            'nombre': obj.puesto.nombre,
            'cantidad_puestos': obj.puesto.cantidad_puestos,
            'zona_id': getattr(obj.puesto, 'zona_id', None),
            'zona_titulo': getattr(getattr(obj.puesto, 'zona', None), 'titulo', ''),
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

    class Meta:
        model = Asignacion
        fields = [
            'id',
            'persona',
            'cliente',
            'instalacion',
            'puesto',
            'horario',
            'mes',
            'anio',
            'estado',
            'orden',
            'patronAsignacion',
            'recurring',
            'start_date',
            'end_date',
            'agregar_sacafranco',
            'sacafranco_grupo',
            'cedula_color',
            'fecha',
            'persona_detalle',
            'cliente_detalle',
            'instalacion_detalle',
            'puesto_detalle',
            'horario_detalle'
        ]


class AsignacionSemanalSerializer(serializers.ModelSerializer):
    puesto_detalle = serializers.SerializerMethodField(read_only=True)
    asignacion_sacafranco = serializers.BooleanField(source='asignacion.agregar_sacafranco', read_only=True)

    def get_puesto_detalle(self, obj):
        p = obj.puesto
        return {
            'id': p.id,
            'nombre': p.nombre,
            'cantidad_puestos': p.cantidad_puestos,
            'zona_id': getattr(p, 'zona_id', None),
            'zona_titulo': getattr(getattr(p, 'zona', None), 'titulo', ''),
            'turno': p.get_turno(),
            'turno_display': p.get_turno_display(),
            'horarios': [{'dia': h.dia, 'horas': h.horas, 'turno': h.turno} for h in p.horarios.all()],
            'resumen': p.resumen,
        }

    class Meta:
        model = AsignacionSemanal
        fields = ['id', 'asignacion', 'puesto', 'week_start', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'created_at', 'updated_at', 'puesto_detalle', 'asignacion_sacafranco']


class SacafrancoFilaSerializer(serializers.ModelSerializer):
    provincia = serializers.PrimaryKeyRelatedField(queryset=Provincia.objects.all(), allow_null=True, required=False)
    provincia_nombre = serializers.SerializerMethodField(read_only=True)
    persona_detalle = serializers.SerializerMethodField(read_only=True)
    persona = serializers.PrimaryKeyRelatedField(queryset=Persona.objects.all(), allow_null=True, required=False)

    def get_provincia_nombre(self, obj):
        return obj.provincia.nombre if obj.provincia else None

    def get_persona_detalle(self, obj):
        if not obj.persona:
            return None
        return {
            'id': obj.persona.id,
            'nombres': obj.persona.nombres,
            'apellidos': obj.persona.apellidos,
            'cedula': obj.persona.cedula,
            'tipo': obj.persona.tipo,
            'provincia': obj.persona.provincia_id,
            'canton': obj.persona.canton_id
        }

    class Meta:
        model = SacafrancoFila
        fields = ['id', 'mes', 'anio', 'orden', 'provincia', 'provincia_nombre', 'persona', 'persona_detalle', 'created_at', 'updated_at']


class SacafrancoFilaSemanalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SacafrancoFilaSemanal
        fields = ['id', 'sacafranco_fila', 'week_start', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'created_at', 'updated_at']

class InstalacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instalacion
        fields = ['id', 'cliente', 'canton', 'codigo', 'nombre', 'direccion']
        read_only_fields = ['id']
        

class PuestoHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuestoHorario
        fields = ('id', 'dia', 'horas', 'turno')

class PuestoSerializer(serializers.ModelSerializer):
    horarios = PuestoHorarioSerializer(many=True, required=False)
    horarios_text = serializers.CharField(write_only=True, required=False)
    horario_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Puesto
        fields = (
            'id', 'instalacion', 'zona', 'nombre', 'tipo', 'cantidad_puestos',
            'resumen', 'horarios', 'horarios_text', 'horario', 'horario_detalle'
        )

    def get_horario_detalle(self, obj):
        if not obj.horario:
            return None
        return {
            'id': obj.horario.id,
            'hora_ingreso': str(obj.horario.hora_ingreso),
            'hora_salida': str(obj.horario.hora_salida),
        }

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