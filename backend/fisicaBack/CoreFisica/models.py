from django.db import models
from django.core.validators import RegexValidator


class Cliente(models.Model):
    ruc = models.CharField(
        max_length=13,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^\d{10}(\d{3})?$', message='RUC: 10 o 13 dígitos')]
    )
    razon_social = models.CharField(max_length=100)
    nombre_comercial = models.CharField(max_length=100)
    
    

    class Meta:
        indexes = [
            models.Index(fields=['nombre_comercial']),
        ]

    def __str__(self):
        return self.nombre_comercial


class Instalacion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='instalaciones')
    nombre = models.CharField(max_length=150, blank=True, null=True)
    provincia = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=50)
    codigo = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    

    def __str__(self):
        return f"{self.cliente.nombre_comercial} - {self.provincia}, {self.ciudad}"


class Puesto(models.Model):
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='puestos')
    nombre = models.CharField(max_length=100)
    cantidad_guardias = models.IntegerField(default=1)
    # `horas_trabajo` moved to `PuestoHorario` (one row per day). Kept out of model.
    # `turno` ahora se almacena por fila en `PuestoHorario` (cada dia puede tener turno distinto)
    resumen = models.CharField(max_length=50, blank=True, editable=False)  # campo para el resumen

    def save(self, *args, **kwargs):
        # Calcular resumen compacto a partir de los horarios relacionados si existen.
        try:
            cantidad = int(self.cantidad_guardias) if self.cantidad_guardias is not None else 0
            # Determine horas y dias desde los horarios relacionados
            horas = 0
            dias_code = ''
            try:
                horarios_qs = getattr(self, 'horarios', None)
                if horarios_qs is not None:
                    horas_list = list(horarios_qs.values_list('horas', flat=True))
                    dias_nums = list(horarios_qs.values_list('dia', flat=True))
                    if horas_list:
                        unique = set(horas_list)
                        if len(unique) == 1:
                            horas = int(unique.pop())
                    if dias_nums:
                        day_map = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'}
                        dias_code = ''.join([day_map.get(d, '') for d in sorted(set(dias_nums))])
            except Exception:
                horas = 0
                dias_code = ''

            # Determinar turno global del puesto a partir de los horarios: si todos los horarios
            # comparten el mismo turno usamos ese, si no, marcamos como 'M' (mixto)
            turno_letter = 'M'
            try:
                horarios_qs = getattr(self, 'horarios', None)
                if horarios_qs is not None:
                    turnos = list(horarios_qs.values_list('turno', flat=True))
                    if turnos:
                        unique_turnos = set([t.strip().lower() for t in turnos if t])
                        if len(unique_turnos) == 1:
                            val = list(unique_turnos)[0]
                            if val.startswith('d'):
                                turno_letter = 'D'
                            elif val.startswith('n'):
                                turno_letter = 'N'
                            else:
                                turno_letter = 'A'
                        else:
                            turno_letter = 'M'
            except Exception:
                turno_letter = 'M'
            self.resumen = f"{cantidad} {horas}{turno_letter}{dias_code}"
        except Exception:
            try:
                self.resumen = f"{self.nombre} - {self.get_turno_display()}"
            except Exception:
                self.resumen = self.nombre or ''
        super().save(*args, **kwargs)

    def sync_from_horarios(self):
        """Actualiza `resumen` desde `PuestoHorario` relacionados.

        No realiza commits; asigna `resumen` en la instancia.
        """
        try:
            horarios_qs = getattr(self, 'horarios', None)
            if horarios_qs is None:
                return
            horas = 0
            dias_code = ''
            horas_list = list(horarios_qs.values_list('horas', flat=True))
            dias_nums = list(horarios_qs.values_list('dia', flat=True))
            turno_letter = 'M'
            if horas_list:
                unique = set(horas_list)
                if len(unique) == 1:
                    horas = int(unique.pop())
            if dias_nums:
                day_map = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'}
                dias_code = ''.join([day_map.get(d, '') for d in sorted(set(dias_nums))])

            turno_letter = 'M'
            try:
                turnos = list(horarios_qs.values_list('turno', flat=True))
                if turnos:
                    unique_turnos = set([t.strip().lower() for t in turnos if t])
                    if len(unique_turnos) == 1:
                        val = list(unique_turnos)[0]
                        if val.startswith('d'):
                            turno_letter = 'D'
                        elif val.startswith('n'):
                            turno_letter = 'N'
                        else:
                            turno_letter = 'A'
                    else:
                        turno_letter = 'M'
            except Exception:
                turno_letter = 'M'
            cantidad = int(self.cantidad_guardias) if self.cantidad_guardias is not None else 0
            self.resumen = f"{cantidad} {horas}{turno_letter}{dias_code}"
        except Exception:
            return

    def get_turno(self):
        """Devuelve 'Diurno', 'Nocturno' o 'Mixto' según los turnos de `PuestoHorario`.
        Si no hay horarios devuelve None.
        """
        try:
            horarios_qs = getattr(self, 'horarios', None)
            if not horarios_qs:
                return None
            turnos = [t for t in horarios_qs.values_list('turno', flat=True) if t]
            if not turnos:
                return None
            unique = set([t.strip().lower() for t in turnos])
            if len(unique) == 1:
                val = list(unique)[0]
                if val.startswith('d'):
                    return 'Diurno'
                if val.startswith('n'):
                    return 'Nocturno'
                return 'Ambos'
            return 'Mixto'
        except Exception:
            return None

    def get_turno_display(self):
        t = self.get_turno()
        return t or '-'

    def __str__(self):
        return self.nombre

DIAS = (
    (1, 'L'),
    (2, 'M'),
    (3, 'X'),
    (4, 'J'),
    (5, 'V'),
    (6, 'S'),
    (7, 'D'),
)


class PuestoHorario(models.Model):
    """Horario por puesto, una fila por día (modelo normalizado).

            turno_letter = 'M'
            try:
                turnos = list(horarios_qs.values_list('turno', flat=True))
                if turnos:
                    unique_turnos = set([t.strip().lower() for t in turnos if t])
                    if len(unique_turnos) == 1:
                        turno_letter = 'D' if list(unique_turnos)[0].startswith('d') else 'N'
            except Exception:
                turno_letter = 'M'
    """
    puesto = models.ForeignKey(Puesto, related_name='horarios', on_delete=models.CASCADE)
    dia = models.PositiveSmallIntegerField(choices=DIAS)
    horas = models.PositiveIntegerField(default=12)
    turno = models.CharField(
        max_length=10,
        choices=[('Diurno', 'Diurno'), ('Nocturno', 'Nocturno'), ('Ambos', 'Ambos')],
        default='Diurno'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('puesto', 'dia')
        verbose_name = 'Horario de Puesto'
        verbose_name_plural = 'Horarios de Puestos'

    def __str__(self):
        return f"{self.puesto} - {self.get_dia_display()} {self.horas}h {self.turno}"


cedula_validator = RegexValidator(regex=r'^\d{1,10}$', message='Cédula: sólo dígitos, máximo 10')

class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Persona(models.Model):
    TIPO_CHOICES = [
        ('FIJOS', 'FIJOS'),
        ('RETENES', 'RETENES'),
        ('EVENTUALES', 'EVENTUALES'),
        ('SACAFRANCO', 'SACAFRANCO'),
        ('SACAVACACIONES', 'SACAVACACIONES'),
        ('SUPERVISOR ZONAL', 'SUPERVISOR ZONAL'),
        ('SUPERVISOR MOTORIZADO', 'SUPERVISOR MOTORIZADO'),
    ]
    tipo = models.CharField(null=True, max_length=25, choices=TIPO_CHOICES)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=10, unique=True, validators=[cedula_validator])

    
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Activo')

   
    objects = models.Manager()
    active = ActiveManager()

    def disable(self, by_user=None):
        if not self.is_active:
            return
        self.is_active = False
        self.save(update_fields=['is_active'])

    def enable(self, by_user=None):
        if self.is_active:
            return
        self.is_active = True
        self.save(update_fields=['is_active'])

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
    # Recurrence: si `recurring` es True, la asignación aplica desde `start_date` hasta `end_date` (opcional)
    recurring = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

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


