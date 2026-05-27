from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings    
import datetime

def current_month():
    return datetime.date.today().month


def current_year():
    return datetime.date.today().year


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
    SIZE_CHOICES = [
        ('PEQUENO', 'Pequeño'),
        ('MEDIANO', 'Mediano'),
        ('GRANDE', 'Grande'),
        ('OFICINA', 'Oficina'),
    ]
    size = models.CharField(max_length=10,
        choices=SIZE_CHOICES,
        default='MEDIANO',
        db_index=True,
        verbose_name='Tamaño del Cliente',
    )
    fecha_ingreso = models.DateField(null=True, blank=True, db_index=True)
    fecha_retiro = models.DateField(null=True, blank=True, db_index=True)
    

    class Meta:
        indexes = [
            models.Index(fields=['nombre_comercial']),
        ]
        permissions = [
            ('import_cliente', 'Can import cliente'),
        ]

    def __str__(self):
        return self.nombre_comercial

class Provincia(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def save(self, *args, **kwargs):
        if self.nombre is not None:
            self.nombre = str(self.nombre).strip().upper()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.nombre

class Canton(models.Model):
    nombre = models.CharField(max_length=50, db_index=True)
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='cantones')

    def save(self, *args, **kwargs):
        if self.nombre is not None:
            self.nombre = str(self.nombre).strip().upper()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = (('provincia', 'nombre'),)
        ordering = ['provincia', 'nombre']

class Zona(models.Model):
    instalacion = models.ForeignKey('Instalacion', on_delete=models.CASCADE, related_name='zonas')
    opcionesZona = [
        ('Zona 1', 'Zona 1'),
        ('Zona 2', 'Zona 2'),
        ('Zona 3', 'Zona 3'),
    ]
    titulo = models.CharField(max_length=100, choices=opcionesZona, db_index=True)

    class Meta:
        ordering = ['instalacion', 'titulo']

class Instalacion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='instalaciones')
    canton = models.ForeignKey(Canton, on_delete=models.PROTECT, related_name='instalaciones', null=True, blank=True)
    codigo = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    nombre = models.CharField(max_length=150, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        prov = getattr(self.canton.provincia, 'nombre', '') if self.canton else ''
        canton_nombre = getattr(self.canton, 'nombre', '') if self.canton else ''
        return f"{self.cliente.nombre_comercial} - {prov}, {canton_nombre}".strip(' - ,')

class Puesto(models.Model):
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='puestos')
    zona = models.ForeignKey(Zona, on_delete=models.PROTECT, related_name='puestos', null=True, blank=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    cantidad_puestos = models.IntegerField(default=1)
    
    resumen = models.CharField(max_length=50, blank=True, editable=False)  

    def _format_dias_range(self, dias_nums):
        if not dias_nums:
            return ''
        day_map = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'}
        ordered = sorted(set(dias_nums))
        if len(ordered) == 1:
            return day_map.get(ordered[0], '')
        first = day_map.get(ordered[0], '')
        last = day_map.get(ordered[-1], '')
        return f"{first}{last}" if first or last else ''

    def save(self, *args, **kwargs):
        
        try:
            cantidad = int(self.cantidad_puestos) if self.cantidad_puestos is not None else 0
            
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
                        dias_code = self._format_dias_range(dias_nums)
            except Exception:
                horas = 0
                dias_code = ''

            
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
                                turno_letter = 'H'
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
                dias_code = self._format_dias_range(dias_nums)

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
                            turno_letter = 'H'
                    else:
                        turno_letter = 'M'
            except Exception:
                turno_letter = 'M'
            cantidad = int(self.cantidad_puestos) if self.cantidad_puestos is not None else 0
            self.resumen = f"{cantidad} {horas}{turno_letter}{dias_code}"
        except Exception:
            return

    def get_turno(self):
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
        if t == 'Ambos':
            return '24H'
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
        ('RETEN', 'RETEN'),
        ('CUSTODIO', 'CUSTODIO'),
        ('EVENTUAL', 'EVENTUAL'),
        ('SACAFRANCO', 'SACAFRANCO'),
        ('SACAVACACIONES', 'SACAVACACIONES'),
        ('SUPERVISOR ZONAL', 'SUPERVISOR ZONAL'),
        ('SUPERVISOR EVENTUAL', 'SUPERVISOR EVENTUAL'),
        ('SUPERVISOR MOTORIZADO', 'SUPERVISOR MOTORIZADO'),
        ('SUPERVISOR DE ACOMPAÑAMIENTO', 'SUPERVISOR DE ACOMPAÑAMIENTO'),
        ('OPERADOR CENTRO CONTROL', 'OPERADOR CENTRO CONTROL'),
        ('SUPERVISOR CENTRO CONTROL', 'SUPERVISOR CENTRO CONTROL'),
    ]
    tipo = models.CharField(null=True, max_length=28, choices=TIPO_CHOICES)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=10, unique=True, validators=[cedula_validator])
    provincia = models.ForeignKey(Provincia, null=True, blank=True, on_delete=models.PROTECT)
    canton = models.ForeignKey(Canton, null=True, blank=True, on_delete=models.PROTECT)
    
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

class PatronAsignacion(models.Model):
    codigo = models.CharField(
        max_length=4,
        unique=True,
        db_index=True,
        validators=[RegexValidator(regex=r'^\d{2,4}$', message='Use 2 a 4 dígitos')],
    )
    secuencia = models.JSONField(help_text="Ciclo ordenado (D/N/F/-)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ALLOWED = {"D", "N", "F"}

    def clean(self):
        seq = self.secuencia or []
        if not isinstance(seq, list) or not seq:
            raise ValueError("'secuencia' debe ser una lista no vacía")
        cleaned = []
        for token in seq:
            t = str(token).strip().upper()
            if t not in self.ALLOWED:
                raise ValueError(f"Símbolo no permitido: {token}")
            cleaned.append(t)
        self.secuencia = cleaned

    def __str__(self):
        return f"{self.codigo} ({'-'.join(self.secuencia)})"


class Horario(models.Model):
    hora_ingreso = models.TimeField()
    hora_salida = models.TimeField()

    def __str__(self):
        return f"{self.hora_ingreso} - {self.hora_salida}"


class SacafrancoFila(models.Model):
    mes = models.PositiveSmallIntegerField(default=current_month)
    anio = models.PositiveSmallIntegerField(default=current_year)
    orden = models.PositiveIntegerField(default=0)
    provincia = models.ForeignKey(Provincia, null=True, blank=True, on_delete=models.PROTECT)
    persona = models.ForeignKey(Persona, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['mes', 'anio'])]

    def __str__(self):
        return f"Sacafranco ({self.mes}/{self.anio})"


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
    patronAsignacion = models.ForeignKey(
        PatronAsignacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones'
    )

    sacafranco_grupo = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sacafranco_miembros'
    )

    fecha = models.DateField(null=True, blank=True)
    mes = models.PositiveSmallIntegerField(default=current_month)
    anio = models.PositiveSmallIntegerField(default=current_year)
    
    recurring = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    publicada_calendario = models.BooleanField(default=False, db_index=True)

    agregar_sacafranco = models.BooleanField(default=False)

    orden = models.PositiveIntegerField(default=0)

    cedula_color = models.CharField(max_length=7, blank=True, null=True)

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='ACTIVO'
    )

    class Meta:
        unique_together = ('persona', 'mes', 'anio')
        permissions = [
            ('export_asignacion', 'Can export asignacion'),
            ('import_puestos_asignaciones', 'Can import puestos/asignaciones'),
        ]

    def __str__(self):
        return f"{self.persona} - {self.puesto} ({self.mes}/{self.anio})"

class AsignacionSemanal(models.Model):

    asignacion = models.ForeignKey('Asignacion', on_delete=models.CASCADE, null=True, blank=True, related_name='semanales')
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE, related_name='asignaciones_semanales')
    week_start = models.DateField()  

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
        unique_together = (('asignacion', 'week_start'),)
        indexes = [models.Index(fields=['week_start']), models.Index(fields=['asignacion', 'week_start'])]

    def __str__(self):
        return f"{self.puesto} - {self.week_start}"


class SacafrancoFilaSemanal(models.Model):
    sacafranco_fila = models.ForeignKey(
        SacafrancoFila,
        on_delete=models.CASCADE,
        related_name='semanales'
    )
    week_start = models.DateField()

    mon = models.CharField(max_length=16, blank=True)
    tue = models.CharField(max_length=16, blank=True)
    wed = models.CharField(max_length=16, blank=True)
    thu = models.CharField(max_length=16, blank=True)
    fri = models.CharField(max_length=16, blank=True)
    sat = models.CharField(max_length=16, blank=True)
    sun = models.CharField(max_length=16, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('sacafranco_fila', 'week_start'),)
        indexes = [models.Index(fields=['week_start']), models.Index(fields=['sacafranco_fila', 'week_start'])]

    def __str__(self):
        return f"SacafrancoFila {self.sacafranco_fila_id} - {self.week_start}"


class CoberturaSacafranco(models.Model):
    DAY_CHOICES = [
        ('mon', 'Lunes'),
        ('tue', 'Martes'),
        ('wed', 'Miércoles'),
        ('thu', 'Jueves'),
        ('fri', 'Viernes'),
        ('sat', 'Sábado'),
        ('sun', 'Domingo'),
    ]

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='coberturas_sacafranco')
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE, related_name='coberturas_sacafranco')
    week_start = models.DateField()
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            ('puesto', 'week_start', 'day'),
            ('persona', 'week_start', 'day'),
        )
        indexes = [
            models.Index(fields=['week_start']),
            models.Index(fields=['puesto', 'week_start', 'day']),
            models.Index(fields=['persona', 'week_start', 'day']),
        ]

    def __str__(self):
        return f"{self.persona} cubre {self.puesto} {self.week_start} {self.day}"


class ReporteAsistencia(models.Model):
    ESTADO_CHOICES = [
        ('TURNO', 'Turno'),
        ('ADICIONAL', 'Adicional'),
        ('EVENTUAL', 'Eventual'),
        ('ADEL/TURNO', 'Adel/Turno'),
        ('DOBLADO', 'Doblado'),
        ('FR/TRABAJADO', 'Fr/Trabajado'),
        ('RETEN', 'Reten'),
        ('CUSTODIO', 'Custodio'),
        
    ]

    TIPOS_REEMPLAZO = [
        'FIJOS',
        'SACAFRANCO',
        'RETEN',
        'SACAVACACIONES',
        'EVENTUAL',
        'SUPERVISOR ZONAL',
        'SUPERVISOR MOTORIZADO',
        'SUPERVISOR DE ACOMPAÑAMIENTO',
        
    ]

    asignacion = models.OneToOneField(
        'Asignacion',
        on_delete=models.CASCADE,
        related_name='reporte_asistencia',
        null=True,
        blank=True
    )
    codigo = models.CharField(max_length=20, blank=True, null=True)

    persona = models.ForeignKey(Persona, on_delete=models.SET_NULL, null=True, blank=True, related_name='reportes_asistencia')
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='reportes_asistencia')
    instalacion = models.ForeignKey(Instalacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='reportes_asistencia')
    puesto = models.ForeignKey(Puesto, on_delete=models.SET_NULL, null=True, blank=True, related_name='reportes_asistencia')
    horario = models.ForeignKey(Horario, on_delete=models.SET_NULL, null=True, blank=True, related_name='reportes_asistencia')

    puesto_tipo = models.CharField(max_length=50, blank=True, null=True)

    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='TURNO')
    reemplazo = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_como_reemplazo',
        limit_choices_to={'tipo__in': TIPOS_REEMPLAZO}
    )
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_asistencia_modificados'
    )
    row_color = models.CharField(max_length=7, blank=True, null=True)
    fecha_reporte = models.DateField(null=True, blank=True)
    modificado_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado']),
        ]
        permissions = [
            ('export_reporte_asistencia', 'Can export reporte asistencia'),
        ]

    def __str__(self):
        if self.codigo:
            return self.codigo
        return f"Reporte {self.asignacion_id}"


class ReporteAsistenciaHistorial(models.Model):
    reporte = models.ForeignKey(ReporteAsistencia, on_delete=models.CASCADE, related_name='historial')
    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name='historial_asistencia')
    fecha_reporte = models.DateField(null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    codigo = models.CharField(max_length=20, blank=True, null=True)
    estado = models.CharField(max_length=12, blank=True, null=True)
    reemplazo = models.ForeignKey(Persona, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    row_color = models.CharField(max_length=7, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['asignacion', 'fecha_reporte']),
        ]


TURNOS_CONSOLIDADO = [
    ('Diurno', 'Diurno'),
    ('Nocturno', 'Nocturno'),
]


class Consolidado(models.Model):
    TIPOS = [
        ('CONSOLa', 'Consola'),
        ('GUARDIA', 'Guardia'),
    ]

    fecha = models.DateField(db_index=True)
    turno = models.CharField(max_length=10, choices=TURNOS_CONSOLIDADO, db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPOS, db_index=True)
    persona_ref = models.ForeignKey(Persona, on_delete=models.SET_NULL, null=True, blank=True, related_name='consolidados')
    asignacion_ref = models.ForeignKey(Asignacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='consolidados')
    nominativo = models.CharField(max_length=50, blank=True, null=True)
    proyecto = models.CharField(max_length=120, blank=True, null=True)
    puesto = models.CharField(max_length=120, blank=True, null=True)
    observacion = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['fecha', 'turno', 'tipo']),
            models.Index(fields=['tipo', 'persona_ref']),
            models.Index(fields=['tipo', 'asignacion_ref']),
        ]
        constraints = [
            models.CheckConstraint(
                name='corefisica_consolidado_consola_ref_ck',
                check=(
                    ~models.Q(tipo='CONSOLa') |
                    (
                        models.Q(asignacion_ref__isnull=True)
                    )
                )
            ),
            models.CheckConstraint(
                name='corefisica_consolidado_guardia_ref_ck',
                check=(
                    ~models.Q(tipo='GUARDIA') |
                    (
                        models.Q(persona_ref__isnull=True)
                    )
                )
            ),
        ]
        ordering = ['fecha', 'turno', 'tipo', 'id']
        permissions = [
            ('export_consolidado', 'Can export consolidado'),
        ]


class ConsolidadoResumen(models.Model):
    fecha = models.DateField(db_index=True)
    turno = models.CharField(max_length=10, choices=TURNOS_CONSOLIDADO, db_index=True)
    faltas = models.PositiveIntegerField(default=0)
    huecas = models.PositiveIntegerField(default=0)
    apoyos = models.PositiveIntegerField(default=0)
    capacitacion = models.PositiveIntegerField(default=0)
    apertura_puesto = models.PositiveIntegerField(default=0)
    servicios_temporales = models.PositiveIntegerField(default=0)
    servicios_adicionales = models.PositiveIntegerField(default=0)
    aprendiendo_consignas = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('fecha', 'turno')
        indexes = [models.Index(fields=['fecha', 'turno'])]


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Perfil {self.user_id}"

    



