from django.db import models


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
    nombre = models.CharField(max_length=100)
    provincia = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre


class Puesto(models.Model):
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='puestos')
    nombre = models.CharField(max_length=100)
    horas_trabajo = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre


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
    cedula = models.CharField(max_length=20, unique=True)
    

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Horario(models.Model):
    hora_ingreso = models.TimeField()
    hora_salida = models.TimeField()
    denominativo = models.CharField(max_length=25)


    def __str__(self):
        return f"{self.denominativo} ({self.hora_ingreso} - {self.hora_salida})"


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

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    mes = models.PositiveSmallIntegerField(default=1)
    anio = models.PositiveSmallIntegerField(default=2026)

    rotativo = models.BooleanField(default=False)

    orden = models.PositiveIntegerField(default=0)
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='ACTIVO'
    )

    class Meta:
        ordering = ['orden']
        unique_together = ('persona', 'puesto', 'mes', 'anio')

    def __str__(self):
        return f"{self.persona} - {self.puesto} ({self.mes}/{self.anio})"


class Asistencia(models.Model):

    TURNO_CHOICES = [
        ('D', 'Día'),
        ('N', 'Noche'),
    ]

    ESTADO_CHOICES = [
        ('NORMAL', 'Normal'),
        ('FRANCO', 'Franco'),
        ('DISPONIBLE', 'Disponible'),
    ]

    asignacion = models.ForeignKey(
        Asignacion,
        on_delete=models.CASCADE,
        related_name='asistencias'
    )
    fecha = models.DateField()

    # D / N
    turno = models.CharField(
        max_length=1,
        choices=TURNO_CHOICES,
        null=True,
        blank=True
    )

    # S30, S31, etc
    codigo_cliente = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    # NORMAL / FRANCO / DISPONIBLE
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='NORMAL'
    )

    class Meta:
        unique_together = ('asignacion', 'fecha')
        ordering = ['fecha']

    def __str__(self):
        return f"{self.fecha} - {self.turno or ''}{self.codigo_cliente or ''}"