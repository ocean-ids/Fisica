from django.db import models


class Cliente(models.Model):
    razon_social = models.CharField(max_length=100)
    nombre_comercial = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, blank=True, null=True)

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
    #horas_trabajo = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre


class Persona(models.Model):
    TIPO_CHOICES = [
        ('SUPERVISOR', 'SUPERVISOR'),
        ('FIJO', 'FIJO'),
        ('FRANCO', 'FRANCO'),
    ]
    tipo = models.CharField(null=True,max_length=10, choices=TIPO_CHOICES)
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
    TIPO_ESTADO = [
        ('ACTIVO', 'ACTIVO'),
        ('INACTIVO', 'INACTIVO'),
    ]
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE)
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE)
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE)
    rotativo = models.CharField(max_length=10,null=True, blank=True)
    mes = models.CharField(max_length=2,null=True, blank=True)
    anio = models.CharField(max_length=4,null=True, blank=True)
    dia_1 = models.CharField(max_length=10,null=True, blank=True)
    dia_2 = models.CharField(max_length=10,null=True, blank=True)
    dia_3 = models.CharField(max_length=10,null=True, blank=True)
    dia_4 = models.CharField(max_length=10,null=True, blank=True)
    dia_5 = models.CharField(max_length=10,null=True, blank=True)
    dia_6 = models.CharField(max_length=10,null=True, blank=True)
    dia_7 = models.CharField(max_length=10,null=True, blank=True)
    dia_8 = models.CharField(max_length=10,null=True, blank=True)
    dia_9 = models.CharField(max_length=10,null=True, blank=True)
    dia_10 = models.CharField(max_length=10,null=True, blank=True)
    dia_11 = models.CharField(max_length=10,null=True, blank=True)
    dia_12 = models.CharField(max_length=10,null=True, blank=True)
    dia_13 = models.CharField(max_length=10,null=True, blank=True)
    dia_14 = models.CharField(max_length=10,null=True, blank=True)
    dia_15 = models.CharField(max_length=10,null=True, blank=True)
    dia_16 = models.CharField(max_length=10,null=True, blank=True)
    dia_17 = models.CharField(max_length=10,null=True, blank=True)
    dia_18 = models.CharField(max_length=10,null=True, blank=True)
    dia_19 = models.CharField(max_length=10,null=True, blank=True)
    dia_20 = models.CharField(max_length=10,null=True, blank=True)
    dia_21 = models.CharField(max_length=10,null=True, blank=True)
    dia_22 = models.CharField(max_length=10,null=True, blank=True)
    dia_23 = models.CharField(max_length=10,null=True, blank=True)
    dia_24 = models.CharField(max_length=10,null=True, blank=True)
    dia_25 = models.CharField(max_length=10,null=True, blank=True)
    dia_26 = models.CharField(max_length=10,null=True, blank=True)
    dia_27 = models.CharField(max_length=10,null=True, blank=True)
    dia_28 = models.CharField(max_length=10,null=True, blank=True)
    dia_29 = models.CharField(max_length=10,null=True, blank=True)
    dia_30 = models.CharField(max_length=10,null=True, blank=True)
    dia_31 = models.CharField(max_length=10,null=True, blank=True)
    orden = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=10,null=True, blank=True, choices=TIPO_ESTADO)

    class Meta:
        ordering = ['orden'] 
    
    #def __str__(self):
    #    return f"{self.persona} en {self.puesto} ({self.fecha_inicio} - {self.fecha_fin or 'actual'})"