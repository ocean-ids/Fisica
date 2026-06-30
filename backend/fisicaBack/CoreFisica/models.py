from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
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

    TIPO_CLIENTE_CHOICES = [('JURIDICA', 'Jurídica'), ('NATURAL', 'Natural')]
    TIPO_ID_CHOICES = [
        ('RUC', 'Registro Único de Contribuyente'),
        ('CEDULA', 'Cédula'),
        ('PASAPORTE', 'Pasaporte'),
    ]
    ESTADO_CHOICES = [('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo')]
    SEXO_CHOICES = [('MASCULINO', 'Masculino'), ('FEMENINO', 'Femenino')]
    ESTADO_CIVIL_CHOICES = [
        ('SOLTERO', 'Soltero'), ('CASADO', 'Casado'),
        ('DIVORCIADO', 'Divorciado'), ('UNION LIBRE', 'Unión Libre'), ('VIUDO', 'Viudo'),
    ]

    codigo_erp = models.CharField(max_length=20, blank=True, default='')        # Código
    ultima_venta = models.DateField(null=True, blank=True)                      # Ult. Venta
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVO')   # STATUS (select)
    control_cupo = models.BooleanField(default=False)                          # Control Cupo (S/N)

    # Identificación / ubicación
    tipo_id = models.CharField(max_length=12, choices=TIPO_ID_CHOICES, blank=True, default='')          # Tipo ID (select)
    tipo_cliente = models.CharField(max_length=10, choices=TIPO_CLIENTE_CHOICES, blank=True, default='') # Tipo Cliente (select)
    provincia = models.ForeignKey('Provincia', null=True, blank=True, on_delete=models.SET_NULL, related_name='clientes')  # Provincia (select)
    canton = models.ForeignKey('Canton', null=True, blank=True, on_delete=models.SET_NULL, related_name='clientes')        # Cantón (select)
    parroquia = models.CharField(max_length=80, blank=True, default='')         # Parroquia
    ciudad = models.CharField(max_length=80, blank=True, default='')            # Ciudad
    direccion_comercial = models.CharField(max_length=255, blank=True, default='')  # Dir. Comercial
    sector = models.CharField(max_length=120, blank=True, default='')           # Sector (select pendiente)
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, blank=True, default='')                 # Sexo (select)
    estado_civil = models.CharField(max_length=15, choices=ESTADO_CIVIL_CHOICES, blank=True, default='') # Estado Civil (select)

    # Contacto
    telefono = models.CharField(max_length=30, blank=True, default='')          # Tel Com.
    telefono2 = models.CharField(max_length=30, blank=True, default='')         # Tel Com. (2)
    fax = models.CharField(max_length=30, blank=True, default='')               # FAX
    email = models.CharField(max_length=255, blank=True, default='')            # Correo
    email_adicional = models.CharField(max_length=255, blank=True, default='')  # Correos Adicional
    copia_correo_1 = models.CharField(max_length=120, blank=True, default='')   # Copias Correo Nuevo
    copia_correo_2 = models.CharField(max_length=120, blank=True, default='')
    copia_correo_3 = models.CharField(max_length=120, blank=True, default='')
    copia_correo_4 = models.CharField(max_length=120, blank=True, default='')
    copia_correo_5 = models.CharField(max_length=120, blank=True, default='')

    # Comercial / crédito
    vendedor = models.CharField(max_length=80, blank=True, default='')          # Vendedor
    rep_legal = models.CharField(max_length=120, blank=True, default='')        # Rep. Legal
    plazo_max = models.IntegerField(default=0)                                  # Plazo Max
    desc_vta = models.DecimalField(max_digits=6, decimal_places=2, default=0)   # Desc Vta
    cupo = models.DecimalField(max_digits=16, decimal_places=2, default=0)      # Cupo
    cod_agrupacion = models.CharField(max_length=40, blank=True, default='')    # Cod de agrupacion
    valoracion_custodias = models.CharField(max_length=40, blank=True, default='')  # Valorizacion Custodias (select pendiente)
    tipo_precio = models.CharField(max_length=40, blank=True, default='')       # Tipo Precio (select pendiente)
    valor_puesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Valor Puesto
    forma_pago = models.CharField(max_length=40, blank=True, default='')        # Forma de Pago (select pendiente)
    origen_ingreso = models.CharField(max_length=60, blank=True, default='')    # Origen Ingresos (select pendiente)
    ZONA_CHOICES = [
        ('Seguridad Física', 'Seguridad Física'),
        ('Seguridad Electrónica', 'Seguridad Electrónica'),
        ('Seguridad de Carga', 'Seguridad de Carga'),
    ]
    zona = models.CharField(max_length=80, choices=ZONA_CHOICES, blank=True, default='')   # Zona
    requiere_correo = models.BooleanField(default=False)                        # Require correo (S/N)
    controla_factura_reverso = models.BooleanField(default=False)              # Controla Factura Reverso

    # Contable
    cuenta_contable = models.CharField(max_length=60, blank=True, default='')   # Cuenta
    cod_area = models.CharField(max_length=20, blank=True, default='')          # Cod Area
    cod_rol = models.CharField(max_length=20, blank=True, default='')           # Cod Rol

    # Banderas
    paga_iva = models.BooleanField(default=True)                               # Paga IVA (check)

    observaciones = models.TextField(blank=True, default='')

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


class Parroquia(models.Model):
    """Parroquia (DPA Ecuador) ligada a un cantón. Catálogo sembrado desde el INEC."""
    nombre = models.CharField(max_length=120, db_index=True)
    canton = models.ForeignKey(Canton, on_delete=models.CASCADE, related_name='parroquias')
    codigo = models.CharField(max_length=10, blank=True, default='', db_index=True)

    def save(self, *args, **kwargs):
        if self.nombre is not None:
            self.nombre = str(self.nombre).strip().upper()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = (('canton', 'nombre'),)
        ordering = ['canton', 'nombre']

    def __str__(self):
        return self.nombre


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
    sector = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        prov = getattr(self.canton.provincia, 'nombre', '') if self.canton else ''
        canton_nombre = getattr(self.canton, 'nombre', '') if self.canton else ''
        return f"{self.cliente.nombre_comercial} - {prov}, {canton_nombre}".strip(' - ,')

def _fmt_horas(h):
    """Formatea las horas para el resumen: 12 -> '12', 10.5 -> '10.5' (sin ceros sobrantes)."""
    try:
        return f"{float(h):g}"
    except (TypeError, ValueError):
        return str(h or '')


class Puesto(models.Model):
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='puestos')
    zona = models.ForeignKey(Zona, on_delete=models.PROTECT, related_name='puestos', null=True, blank=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    cantidad_puestos = models.IntegerField(default=1)
    horario = models.ForeignKey('Horario', null=True, blank=True, on_delete=models.SET_NULL, related_name='puestos')
    activo = models.BooleanField(default=True, db_index=True, verbose_name='Activo')

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
            # El resumen representa UN puesto (registro), no su capacidad de cupos.
            cantidad = 1

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
                            horas = unique.pop()
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
                                turno_letter = ''  # 24h/Ambos: sin letra (evita doble H)
                        else:
                            turno_letter = 'M'
            except Exception:
                turno_letter = 'M'
            self.resumen = f"{cantidad} {_fmt_horas(horas)}H{turno_letter}{dias_code}"
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
            # El resumen representa UN puesto (registro), no su capacidad de cupos.
            cantidad = 1
            self.resumen = f"{cantidad} {_fmt_horas(horas)}H{turno_letter}{dias_code}"
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
    # Duración del turno en horas. Decimal para soportar minutos (ej. 19.33 = 19:20).
    horas = models.DecimalField(max_digits=4, decimal_places=2, default=12)
    hora_ingreso = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
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

    SEXO_CHOICES = [
        ('MASCULINO', 'Masculino'),
        ('FEMENINO', 'Femenino')
    ]

    ESTADO_CIVIL_CHOICES = [
        ('SOLTERO', 'Soltero'),
        ('CASADO', 'Casado'),
        ('DIVORCIADO', 'Divorciado'),
        ('UNION LIBRE', 'Unión Libre'),
        ('VIUDO', 'Viudo'),   
    ]

    TIPO_EMPLEADO_CHOICES = [
        ('EMPLEADO', 'Empleado'),
        ('OPERADOR', 'Operador'),
        ('OBRERO', 'Obrero o Eventual'),
    ]

    PERFIL_CHOICES = [
        ('SENSIBLE', 'Sensible'),
        ('RIGIDO', 'Rígido'),
        ('INDUSTRIAL', 'Industrial'),
        ('CUSTODIA', 'Custodia'),
        ('OTROS', 'Otros'),
    ]

    FORMA_PAGO_CHOICES = [
        ('MENSUAL', 'Mensual'),
        ('QUINCENAL', 'Quincenal'),
        ('SEMANAL', 'Semanal'),
    ]

    MOTIVO_SALIDA_CHOICES = [
        ('RENUNCIA VOLUNTARIA', 'Renuncia Voluntaria'),
        ('DESPIDO', 'Despido'),
        ('VISTO BUENO', 'Visto Bueno'),
        ('TERMINACIÓN DE CONTRATO', 'Terminación de Contrato'),
        ('PROBLEMAS FAMILIARES', 'Problemas Familiares'),
        ('MEJOR PROPUESTA DE TRABAJO', 'Mejor Propuesta de Trabajo'),
    ]

    NACIONALIDAD_CHOICES = [
        ('Ecuatoriana', 'Ecuatoriana'),
        ('Extranjero', 'Extranjero'),
        ('Otros', 'Otros'),
    ]

    UNIDAD_NEGOCIO_CHOICES = [
        ('SEGURIDAD FISICA', 'Seguridad Física'),
        ('SEGURIDAD DE CARGA', 'Seguridad de Carga'),
    ]

    REGION_CHOICES = [
        ('SIERRA', 'Sierra'),
        ('COSTA', 'Costa'),
    ]

    ESTADO_EMPLEADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('LIQUIDADO', 'Liquidado'),
        ('SUSPENDIDO', 'Suspendido'),
    ]

    tipo = models.CharField(null=True, max_length=28, choices=TIPO_CHOICES)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=10, unique=True, validators=[cedula_validator])
    provincia = models.ForeignKey(Provincia, null=True, blank=True, on_delete=models.PROTECT)
    canton = models.ForeignKey(Canton, null=True, blank=True, on_delete=models.PROTECT)
    
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Activo')
    # Estado del empleado (lo que se elige en el formulario). LIQUIDADO/SUSPENDIDO = deshabilitado.
    # is_active se sincroniza desde aquí en save(); todos los filtros del sistema siguen usando is_active.
    estado_empleado = models.CharField(max_length=12, choices=ESTADO_EMPLEADO_CHOICES, default='ACTIVO', db_index=True)
    
    fecha_nacimiento = models.DateField(null=True, blank=True)
    departamento = models.CharField(max_length=120, blank=True, default='')
    seccion = models.CharField(max_length=120, blank=True, default='')
    sexo = models.CharField(max_length=10, blank=True, default='', choices=SEXO_CHOICES)
    cargo = models.CharField(max_length=120, blank=True, default='')
    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_salida = models.DateField(null=True, blank=True)
    correo_personal = models.EmailField(blank=True, default='')
    direccion = models.CharField(max_length=255, blank=True, default='')
    
    foto = models.ImageField(upload_to='personas/', null=True, blank=True)
    codigo_erp = models.CharField(max_length=255, blank=True, default='')
    centro_costo = models.CharField(max_length=60, blank=True, default='')
    estatura = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    lugar_nacimiento = models.CharField(max_length=120, blank=True, default='')
    parroquia = models.CharField(max_length=120, blank=True, default='')
    estado_civil = models.CharField(max_length=20, blank=True, default='', choices=ESTADO_CIVIL_CHOICES)
    telefono = models.CharField(max_length=20, blank=True, default='')
    conyuge = models.CharField(max_length=150, blank=True, default='')
    nacionalidad = models.CharField(max_length=40, blank=True, default='', choices=NACIONALIDAD_CHOICES)
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL, related_name='empleados')
    unidad_negocio = models.CharField(max_length=60, blank=True, default='', choices=UNIDAD_NEGOCIO_CHOICES)
    tipo_empleado = models.CharField(max_length=20, blank=True, default='', choices=TIPO_EMPLEADO_CHOICES)
    forma_pago = models.CharField(max_length=20, blank=True, default='', choices=FORMA_PAGO_CHOICES)
    numero_afiliacion = models.CharField(max_length=30, blank=True, default='')
    numero_contrato = models.CharField(max_length=30, blank=30, default='')
    actividad = models.CharField(max_length=120, blank=True, default='')
    perfil = models.CharField(max_length=60, blank=True, default='', choices=PERFIL_CHOICES)
    fecha_pago_liquidacion = models.DateField(null=True, blank=True)
    motivo_salida = models.CharField(max_length=120, blank=True, default='', choices=MOTIVO_SALIDA_CHOICES)
    region = models.CharField(max_length=60, blank=True, default='', choices=REGION_CHOICES)
    gypaseg = models.BooleanField(default=False)
    affis = models.BooleanField(default=False)
    pbip = models.BooleanField(default=False)

    objects = models.Manager()
    active = ActiveManager()

    def save(self, *args, **kwargs):
        # estado_empleado es la fuente de verdad: ACTIVO -> habilitado; LIQUIDADO/SUSPENDIDO -> deshabilitado.
        self.is_active = (self.estado_empleado == 'ACTIVO')
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'is_active' not in update_fields:
            kwargs['update_fields'] = list(update_fields) + ['is_active']
        super().save(*args, **kwargs)

    def disable(self, by_user=None):
        if not self.is_active:
            return
        self.estado_empleado = 'LIQUIDADO'
        self.save(update_fields=['estado_empleado'])

    def enable(self, by_user=None):
        if self.is_active:
            return
        self.estado_empleado = 'ACTIVO'
        self.save(update_fields=['estado_empleado'])

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class EmpleadoNomina(models.Model):
    """Datos de nómina (Ingresos / Descuentos) del empleado. 1 registro por Persona."""
    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name='nomina', primary_key=True
    )

    # --- Sueldo y Beneficios de Ley ---
    sueldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desc_genesis = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonificacion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transporte = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    compensacion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    horas_25 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    horas_50 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    horas_100 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pagar_fondo_reserva = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, default='')

    # --- Acumulados de Beneficios Sociales Históricos ---
    decimo_tercer = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    decimo_cuarto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vacaciones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fondo_reserva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pagar_rol_10mo_3ero = models.BooleanField(default=False)
    pagar_rol_10mo_4to = models.BooleanField(default=False)
    pagar_rol_vacaciones = models.BooleanField(default=False)
    desc_aporte_conyuge = models.BooleanField(default=False)
    giro_contable_liquidacion = models.BooleanField(default=False)
    numero_liquidacion_ministerio = models.CharField(max_length=60, blank=True, default='')

    # --- Rol Extra ---
    moviliza = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lunch = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    anticipo_22 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    viaticos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ingreso_extra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    concepto = models.CharField(max_length=255, blank=True, default='')

    # --- Subsidio ---
    subsidio_enfermedad = models.BooleanField(default=False)
    subsidio_enfermedad_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subsidio_accidente = models.BooleanField(default=False)
    subsidio_accidente_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subsidio_maternidad = models.BooleanField(default=False)
    subsidio_maternidad_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Nómina de {self.persona}"

class EmpleadoOtrosDatos(models.Model):
    """Pestaña 'Otros Datos': bancario, contable, vacaciones, cargas y gastos deducibles."""
    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name='otros_datos', primary_key=True
    )

    # --- Datos Generales ---
    incluir_en_rol = models.BooleanField(default=True)
    acreditar = models.BooleanField(default=False)
    ultima_liquidacion = models.DateField(null=True, blank=True)
    grupo_sanguineo = models.CharField(max_length=8, blank=True, default='')
    banco = models.CharField(max_length=80, blank=True, default='')
    cuenta_ahorros = models.CharField(max_length=30, blank=True, default='')
    cuenta_corriente = models.CharField(max_length=30, blank=True, default='')

    # --- Vacaciones ---
    fecha_ini_vacaciones = models.DateField(null=True, blank=True)
    fecha_fin_vacaciones = models.DateField(null=True, blank=True)
    dias_vacaciones = models.IntegerField(default=0)

    # --- Cuentas Contables ---
    codigo_cuenta = models.CharField(max_length=30, blank=True, default='')
    cuenta_departamento = models.CharField(max_length=20, blank=True, default='')
    cuenta_auxiliar = models.CharField(max_length=30, blank=True, default='')

    # --- Cargas del empleado ---
    numero_cargas = models.IntegerField(default=0)

    # --- Relación de Dependencia (gastos deducibles) ---
    gasto_salud = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_vestimenta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_educacion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_vivienda = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_alimentacion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_arte_cultura = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_turismo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Otros datos de {self.persona}"

class EmpleadoReferencias(models.Model):
    """Pestaña 'Referencias': datos referenciales, estudios y servicios."""
    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name='referencias', primary_key=True
    )

    # --- Datos Referenciales ---
    cedula_militar = models.CharField(max_length=30, blank=True, default='')
    observacion = models.CharField(max_length=255, blank=True, default='')
    edad = models.IntegerField(null=True, blank=True)
    maniobras = models.CharField(max_length=120, blank=True, default='')
    carnet_conadis = models.CharField(max_length=40, blank=True, default='')
    numero_certificado_votacion = models.CharField(max_length=40, blank=True, default='')
    licencia_conducir = models.CharField(max_length=20, blank=True, default='')
    codigo_iess = models.CharField(max_length=40, blank=True, default='')
    certificado_violencia_intrafamiliar = models.CharField(max_length=120, blank=True, default='')

    # --- Estudios ---
    primaria = models.BooleanField(default=False)
    secundaria = models.BooleanField(default=False)
    universidad = models.BooleanField(default=False)
    titulo = models.CharField(max_length=120, blank=True, default='')
    anios_estudio = models.IntegerField(default=0)

    # --- Servicios ---
    miembro_fuerza_publica = models.BooleanField(default=False)
    realizo_servicio_militar = models.BooleanField(default=False)
    contrato_inspectoria = models.CharField(max_length=120, blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Referencias de {self.persona}"


class EmpleadoDocumento(models.Model):
    """Documentos del empleado: referencias a archivos en rutas compartidas de red
    (\\\\Servidor\\...). No sube archivos; guarda la ruta/nombre que lleva a ellos."""
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=60, blank=True, default='PDF GENERAL')
    nombre_archivo = models.CharField(max_length=255, blank=True, default='')
    ruta_archivo = models.CharField(max_length=500, blank=True, default='')
    extension = models.CharField(max_length=10, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.nombre_archivo or self.ruta_archivo} ({self.persona_id})"


class EmpleadoExperiencia(models.Model):
    """Más Referencias: experiencia profesional del empleado."""
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='experiencias')
    empresa = models.CharField(max_length=150, blank=True, default='')
    puesto_cargo = models.CharField(max_length=150, blank=True, default='')
    tiempo = models.CharField(max_length=60, blank=True, default='')
    motivo_salida = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.empresa} ({self.persona_id})"


class EmpleadoReferenciaPersonal(models.Model):
    """Más Referencias: referencia personal del empleado."""
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='referencias_personales')
    persona_contactar = models.CharField(max_length=150, blank=True, default='')
    relacion = models.CharField(max_length=60, blank=True, default='')
    telefonos = models.CharField(max_length=80, blank=True, default='')
    comentario = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.persona_contactar} ({self.persona_id})"


class EmpleadoNivelEstudio(models.Model):
    """Más Referencias: nivel de estudio del empleado."""
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='niveles_estudio')
    nivel_estudio = models.CharField(max_length=80, blank=True, default='')
    completa = models.BooleanField(default=False)
    centro_capacitacion = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.nivel_estudio} ({self.persona_id})"


class EmpleadoFormacion(models.Model):
    """Más Referencias: formación / cursos del empleado."""
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='formaciones')
    centro_capacitacion = models.CharField(max_length=150, blank=True, default='')
    curso = models.CharField(max_length=150, blank=True, default='')
    area = models.CharField(max_length=100, blank=True, default='')
    horas = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.curso} ({self.persona_id})"


class TipoCertificado(models.Model):
    """Catálogo de tipos de certificado/documento (editable, sin migrar para agregar)."""
    nombre = models.CharField(max_length=80, unique=True)
    grupo = models.CharField(max_length=40, blank=True, default='')
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return self.nombre


class EmpleadoCertificado(models.Model):
    """Certificados que tiene un empleado (marca del catálogo TipoCertificado)."""
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='certificados')
    tipo = models.ForeignKey(TipoCertificado, on_delete=models.CASCADE, related_name='empleados')
    tiene = models.BooleanField(default=True)
    archivo = models.FileField(upload_to='certificados/', null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    observacion = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        unique_together = ('persona', 'tipo')

    def __str__(self):
        return f"{self.persona_id} - {self.tipo_id}"


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
    hora_ingreso = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    # Alcance de la vista donde se creó: si están seteados, la fila se muestra SOLO
    # en vistas que coincidan (cantones o empresas). Si ambos están vacíos, la fila
    # es "heredada" y se muestra por el cantón de su persona (compatibilidad).
    cantones = ArrayField(models.IntegerField(), default=list, blank=True)
    clientes = ArrayField(models.IntegerField(), default=list, blank=True)
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

    persona = models.ForeignKey(Persona, on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE)
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE)
    # El horario real proviene del puesto (PuestoHorario). Este FK queda como
    # fallback opcional: ya no es obligatorio al crear una asignación.
    horario = models.ForeignKey(Horario, on_delete=models.SET_NULL, null=True, blank=True)
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

    ESTADO_ASISTENCIA_CHOICES = [
        ('ASISTIO', 'Asistio'),
        ('FALTO', 'Falto'),
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
    estado_asistencia = models.CharField(
        max_length=10,
        choices=ESTADO_ASISTENCIA_CHOICES,
        null=True,
        blank=True,
    )
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
            models.Index(fields=['estado_asistencia']),
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
    estado_asistencia = models.CharField(max_length=10, blank=True, null=True)
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
    provincia_ref = models.ForeignKey(Provincia, on_delete=models.SET_NULL, null=True, blank=True, related_name='consolidados')
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


class AsignacionCalendarioLog(models.Model):
    asignacion = models.ForeignKey(
        'Asignacion', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='logs_calendario'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    week_start = models.DateField()
    dia = models.CharField(max_length=3)
    valor_anterior = models.CharField(max_length=10, blank=True)
    valor_nuevo = models.CharField(max_length=10, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['-creado_en']),
            models.Index(fields=['asignacion', 'week_start']),
            models.Index(fields=['usuario']),
        ]

    def __str__(self):
        return f"{self.creado_en:%Y-%m-%d %H:%M} | {self.dia} | {self.valor_anterior}→{self.valor_nuevo}"


class VistaCanton(models.Model):
    """Vista personalizada compartida (global) entre todos los usuarios.

    Puede ser de dos tipos:
      - 'canton'  -> agrupa cantones (lista de ids en `cantones`).
      - 'cliente' -> agrupa empresas/clientes (lista de ids en `clientes`);
                     muestra todas las instalaciones de esos clientes.
    """
    TIPO_CHOICES = [
        ('canton', 'Cantones'),
        ('cliente', 'Empresas'),
        ('persona_tipo', 'Tipos de persona'),
    ]
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='canton')
    cantones = models.JSONField(default=list)
    clientes = models.JSONField(default=list)
    # Para tipo='cliente': instalaciones especificas de la empresa. Si va vacio,
    # la vista incluye TODAS las instalaciones del cliente.
    instalaciones = models.JSONField(default=list)
    # Para tipo='persona_tipo': lista de tipos de persona (FIJOS, SACAFRANCO, ...).
    # Es ADITIVA: estas personas siguen apareciendo en sus vistas por cantón.
    tipos = models.JSONField(default=list)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class AuditLog(models.Model):
    """Registro de auditoría: quién creó/editó/eliminó qué entidad y cuándo.

    Se llena automáticamente vía señales (post_save/post_delete) en CoreFisica/signals.py.
    El usuario se obtiene del request actual mediante el middleware de auditoría.
    """
    ACCIONES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
    ]
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='auditorias'
    )
    usuario_str = models.CharField(max_length=150, blank=True)  # respaldo del username
    accion = models.CharField(max_length=10, choices=ACCIONES)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=64, blank=True)
    objeto_repr = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['-creado_en']),
            models.Index(fields=['modelo', 'objeto_id']),
            models.Index(fields=['usuario']),
        ]

    def __str__(self):
        return f"{self.creado_en:%Y-%m-%d %H:%M} | {self.usuario_str} | {self.accion} {self.modelo}#{self.objeto_id}"


class NovedadPuesto(models.Model):
    """Reporte de Apertura, Modificación o Cierre de Puesto (formato FR).

    Cada registro es una novedad de un puesto en una fecha y turno. El reporte FR
    se agrupa por fecha y se separa en TURNO DIURNO / TURNO NOCTURNO.
    """
    TURNOS = [
        ('Diurno', 'Diurno'),
        ('Nocturno', 'Nocturno'),
    ]
    NOVEDADES = [
        ('APERTURA', 'Apertura'),
        ('MODIFICACION', 'Modificación'),
        ('CIERRE', 'Cierre'),
        ('INCREMENTO', 'Incremento'),
        ('MODIFICACION INCREMENTO', 'Modificación / Incremento'),
    ]

    puesto = models.ForeignKey(
        Puesto, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='novedades'
    )
    instalacion = models.ForeignKey(
        Instalacion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='novedades'
    )
    fecha = models.DateField()
    turno = models.CharField(max_length=10, choices=TURNOS, default='Diurno')
    cliente_denominativo = models.CharField(max_length=200, blank=True)
    sector = models.CharField(max_length=150, blank=True)
    novedad = models.CharField(max_length=40, choices=NOVEDADES)
    tipo = models.CharField(max_length=100, blank=True)
    horario = models.CharField(max_length=100, blank=True)
    solicitado_por = models.CharField(max_length=150, blank=True)
    observacion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', 'turno', 'cliente_denominativo']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['fecha', 'turno']),
        ]
        permissions = [
            ('export_novedadpuesto', 'Puede exportar reporte de novedades de puesto'),
        ]

    def __str__(self):
        return f"{self.fecha} | {self.turno} | {self.novedad} | {self.cliente_denominativo}"


