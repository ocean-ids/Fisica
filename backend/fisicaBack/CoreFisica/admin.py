from django.contrib import admin
from .models import Cliente, Instalacion, Puesto, Persona, Horario, Asignacion, AsignacionSemanal, PuestoHorario


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
	list_display = ('nombre_comercial', 'razon_social', 'ruc')


@admin.register(Instalacion)
class InstalacionAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'cliente', 'provincia', 'ciudad', 'codigo')


class PuestoHorarioInline(admin.TabularInline):
	model = PuestoHorario
	extra = 1
	fields = ('dia', 'horas', 'turno')


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'instalacion', 'get_turno_display', 'cantidad_guardias', 'get_horarios_count')
	readonly_fields = ('resumen',)
	inlines = (PuestoHorarioInline,)

	def get_turno_display(self, obj):
		return obj.get_turno_display()
	get_turno_display.short_description = 'Turno'

	def get_horarios_count(self, obj):
		return obj.horarios.count()
	get_horarios_count.short_description = 'Horarios'

	def save_related(self, request, form, formsets, change):
		# Guardar inlines primero y luego sincronizar campos derivados desde PuestoHorario
		super().save_related(request, form, formsets, change)
		instance = form.instance
		try:
			instance.sync_from_horarios()
			instance.save()
		except Exception:
			# evitar que errores de sincronización rompan el admin
			pass


@admin.action(description='Deshabilitar seleccionadas')
def make_disabled(modeladmin, request, queryset):
	queryset.update(is_active=False)


@admin.action(description='Habilitar seleccionadas')
def make_enabled(modeladmin, request, queryset):
	queryset.update(is_active=True)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
	list_display = ('nombres', 'apellidos', 'cedula', 'tipo', 'is_active')
	list_filter = ('tipo', 'is_active')
	actions = [make_disabled, make_enabled]


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
	list_display = ('hora_ingreso', 'hora_salida')


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
	list_display = ('persona', 'cliente', 'instalacion', 'puesto', 'horario', 'mes', 'anio', 'estado')
	list_filter = ('mes', 'anio', 'estado')


@admin.register(AsignacionSemanal)
class AsignacionSemanalAdmin(admin.ModelAdmin):
	list_display = ('puesto', 'week_start', 'created_at', 'updated_at')