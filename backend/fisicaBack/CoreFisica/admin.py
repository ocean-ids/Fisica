from django.contrib import admin
from .models import Cliente, Instalacion, Puesto, Persona, Horario, Asignacion

admin.site.register(Cliente)
admin.site.register(Instalacion)
admin.site.register(Puesto)
admin.site.register(Persona)
admin.site.register(Horario)
admin.site.register(Asignacion)    