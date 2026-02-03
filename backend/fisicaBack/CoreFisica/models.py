from django.db import models
from django.core.validators import RegexValidator


class Cliente(models.Model):
    razon_social = models.CharField(max_length=100)
    nombre_comercial = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['nombre_comercial']),
        ]

    def __str__(self):
        return self.nombre_comercial


class Instalacion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='instalaciones')
    provincia = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.cliente.nombre_comercial} - {self.provincia}, {self.ciudad}"


class Puesto(models.Model):
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='puestos')
    nombre = models.CharField(max_length=100)
    cantidad_guardias = models.IntegerField(default=0)
    horas_trabajo = models.IntegerField(default=0)
    turno = models.CharField(max_length=10, choices=[
        ('dia', 'Día'),
        ('noche', 'Noche'),
    ], default='dia')
    dias = models.JSONField(default=list)
    resumen = models.CharField(max_length=50, blank=True, editable=False)  # campo para el resumen

    def save(self, *args, **kwargs):
        # Calcular resumen compacto: "<cantidad> <horas>H<T><dias>"
        # Ejemplo: "1 12HDLMXJV" (1 guardia, 12 horas, D=día, días abreviados)
        try:
            cantidad = int(self.cantidad_guardias) if self.cantidad_guardias is not None else 0
            horas = int(self.horas_trabajo) if self.horas_trabajo is not None else 0
            turno_letter = 'D' if (self.turno or '').lower() == 'dia' else 'N'

            # Mapear nombres de días a códigos compactos (usar primera letra)
            day_map = {
                'lunes': 'L',
                'martes': 'M',
                'miercoles': 'M',
                'miércoles': 'M',
                'jueves': 'J',
                'viernes': 'V',
                'sábado': 'S',
                'sabado': 'S',
                'domingo': 'D'
            }

            dias_list = []
            if isinstance(self.dias, (list, tuple)):
                for d in self.dias:
                    if not d:
                        continue
                    key = str(d).strip().lower()
                    dias_list.append(day_map.get(key, key[:1].upper()))
            # Unir códigos de días (ej: LMA MIJV -> LMA MIJV) — usamos abreviaturas claras
            dias_code = ''.join(dias_list)

            # Formato compacto solicitado: "<cantidad> <horas><D|N><dias>" (sin 'H')
            self.resumen = f"{cantidad} {horas}{turno_letter}{dias_code}"
        except Exception:
            # Fallback: nombre - turno
            try:
                self.resumen = f"{self.nombre} - {self.turno}"
            except Exception:
                self.resumen = self.nombre or ''
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


cedula_validator = RegexValidator(regex=r'^\d{1,10}$', message='Cédula: sólo dígitos, máximo 10')

class Persona(models.Model):
    TIPO_CHOICES = [
        ('SUPERVISOR', 'SUPERVISOR'),
        ('FIJO', 'FIJO'),
        ('FRANCO', 'FRANCO'),
        ('SACAFRANCO', 'SACAFRANCO'),
        ('EVENTUAL', 'EVENTUAL'),
    ]
    tipo = models.CharField(null=True,max_length=15, choices=TIPO_CHOICES)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=10, unique=True, validators=[cedula_validator])
    

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Horario(models.Model):
    hora_ingreso = models.TimeField()
    hora_salida = models.TimeField()

    def __str__(self):
        return f"{self.hora_ingreso} - {self.hora_salida}"


class Asignacion(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'ACTIVO'),
        ('INACTIVO', 'INACTIVO'),
    ]

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE)
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE)
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE)

    fecha = models.DateField(null=True, blank=True)
    mes = models.PositiveSmallIntegerField(default=1)
    anio = models.PositiveSmallIntegerField(default=2026)

    # orden eliminado
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='ACTIVO'
    )

    class Meta:
        unique_together = ('persona', 'mes', 'anio')

    def __str__(self):
        return f"{self.persona} - {self.puesto} ({self.mes}/{self.anio})"
        

class AsignacionSemanal(models.Model):
    """Programación semanal por puesto.

    Cada fila representa una semana (fecha del lunes en `week_start`) y contiene
    7 celdas con hasta 4 caracteres por día (límite `max_length=4`).
    """

    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE, related_name='asignaciones_semanales')
    week_start = models.DateField()  # fecha del lunes de la semana

    mon = models.CharField(max_length=4, blank=True)
    tue = models.CharField(max_length=4, blank=True)
    wed = models.CharField(max_length=4, blank=True)
    thu = models.CharField(max_length=4, blank=True)
    fri = models.CharField(max_length=4, blank=True)
    sat = models.CharField(max_length=4, blank=True)
    sun = models.CharField(max_length=4, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('puesto', 'week_start'),)
        indexes = [models.Index(fields=['week_start']),]

    def __str__(self):
        return f"{self.puesto} - {self.week_start}"