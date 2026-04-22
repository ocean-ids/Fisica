from django.contrib import admin
from .models import Cliente, Canton,Provincia, Zona, Instalacion, Puesto, Persona, Horario, Asignacion, AsignacionSemanal, PuestoHorario, PatronAsignacion, ReporteAsistencia, SacafrancoFila, SacafrancoFilaSemanal, ReporteAsistenciaHistorial, PersonalConsola, Consolidado, UserProfile

admin.site.site_header = 'Seguridad Física'
admin.site.site_title = 'Seguridad Física'
admin.site.index_title = 'Panel de Administración'


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
	list_display = ('nombre_comercial', 'razon_social', 'ruc', 'fecha_ingreso', 'fecha_retiro')
	search_fields = ('nombre_comercial', 'razon_social', 'ruc')

@admin.register(Canton)
class CantonAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'provincia')
	search_fields = ('nombre', 'provincia__nombre')

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
	list_display = ('nombre',)
	search_fields = ('nombre',)

@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'instalacion')
	search_fields = ('titulo', 'instalacion__nombre', 'instalacion__canton__nombre')
	list_filter = ('instalacion',)

@admin.register(Instalacion)
class InstalacionAdmin(admin.ModelAdmin):
	list_display = ('codigo', 'nombre', 'cliente')
	search_fields = ('codigo', 'nombre', 'cliente__nombre_comercial', 'canton__provincia__nombre', 'canton__nombre')

class PuestoHorarioInline(admin.TabularInline):
	model = PuestoHorario
	extra = 1
	fields = ('dia', 'horas', 'turno')

@admin.register(SacafrancoFila)
class SacafrancoFilaAdmin(admin.ModelAdmin):
	list_display = ('id', 'mes', 'anio', 'orden', 'created_at', 'updated_at')
	search_fields = ()
	list_filter = ('mes', 'anio')

@admin.register(SacafrancoFilaSemanal)
class SacafrancoFilaSemanalAdmin(admin.ModelAdmin):
	list_display = ('sacafranco_fila', 'week_start', 'created_at', 'updated_at')
	list_filter = ('week_start',)

@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'instalacion', 'get_turno_display', 'cantidad_puestos', 'get_horarios_count')
	search_fields = ('nombre', 'instalacion__nombre')
	readonly_fields = ('resumen',)
	inlines = (PuestoHorarioInline,)

	def get_turno_display(self, obj):
		return obj.get_turno_display()
	get_turno_display.short_description = 'Turno'

	def get_horarios_count(self, obj):
		return obj.horarios.count()
	get_horarios_count.short_description = 'Horarios'

	def save_related(self, request, form, formsets, change):
		super().save_related(request, form, formsets, change)
		instance = form.instance
		try:
			instance.sync_from_horarios()
			instance.save()
		except Exception:
			
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
	search_fields = ('nombres', 'apellidos', 'cedula')
	list_filter = ('tipo', 'is_active')
	actions = [make_disabled, make_enabled]


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
	list_display = ('hora_ingreso', 'hora_salida')


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
	list_display = ('persona', 'cliente', 'instalacion', 'puesto', 'horario', 'mes', 'anio', 'estado')
	list_filter = ('mes', 'anio', 'estado')
	search_fields = ('persona__nombres', 'persona__apellidos', 'cliente__nombre_comercial', 'instalacion__nombre', 'puesto__nombre')

@admin.register(PatronAsignacion)
class PatronAsignacionAdmin(admin.ModelAdmin):
	list_display = ('codigo', 'secuencia')
	list_display_links = ('codigo',)
	search_fields = ('codigo',)
	fields = ('codigo', 'secuencia')

@admin.register(AsignacionSemanal)
class AsignacionSemanalAdmin(admin.ModelAdmin):
	list_display = ('puesto', 'week_start', 'created_at', 'updated_at')


@admin.register(PuestoHorario)
class PuestoHorarioAdmin(admin.ModelAdmin):
	list_display = ('puesto', 'dia', 'horas', 'turno')


@admin.register(ReporteAsistencia)
class ReporteAsistenciaAdmin(admin.ModelAdmin):
	list_display = ('codigo', 'cliente', 'persona', 'estado')
	search_fields = ('codigo', 'persona__nombres', 'persona__apellidos', 'cliente__nombre_comercial')
	list_filter = ('estado',)


@admin.register(ReporteAsistenciaHistorial)
class ReporteAsistenciaHistorialAdmin(admin.ModelAdmin):
	list_display = ('reporte', 'usuario', 'creado_en')
	search_fields = ('reporte__codigo', 'usuario__username')
	list_filter = ('creado_en',)

@admin.register(PersonalConsola)
class PersonalConsolaAdmin(admin.ModelAdmin):
	list_display = ('apellidos', 'nombres', 'tipo', 'turno', 'is_active')
	search_fields = ('apellidos', 'nombres', 'cedula')
	list_filter = ('tipo', 'turno', 'is_active')

	def has_module_permission(self, request):
		return request.user.has_perm('CoreFisica.view_personalconsola')

	def has_view_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.view_personalconsola')

	def has_change_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.change_personalconsola')

	def has_add_permission(self, request):
		return request.user.has_perm('CoreFisica.add_personalconsola')

	def has_delete_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.delete_personalconsola')


@admin.register(Consolidado)
class ConsolidadoAdmin(admin.ModelAdmin):
	list_display = ('fecha', 'turno', 'tipo', 'referencia_id', 'observacion')
	search_fields = ('observacion',)
	list_filter = ('fecha', 'turno', 'tipo')

	def has_module_permission(self, request):
		return request.user.has_perm('CoreFisica.view_consolidado')

	def has_view_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.view_consolidado')

	def has_change_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.change_consolidado')

	def has_add_permission(self, request):
		return request.user.has_perm('CoreFisica.add_consolidado')

	def has_delete_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.delete_consolidado')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'cargo', 'user_is_active', 'updated_at')
	search_fields = ('user__username', 'user__email', 'cargo')
	list_filter = ('user__is_active',)

	def user_is_active(self, obj):
		return obj.user.is_active
	user_is_active.boolean = True
	user_is_active.short_description = 'Activo'

	def has_module_permission(self, request):
		return request.user.has_perm('CoreFisica.view_userprofile')

	def has_view_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.view_userprofile')

	def has_change_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.change_userprofile')

	def has_add_permission(self, request):
		return request.user.has_perm('CoreFisica.add_userprofile')

	def has_delete_permission(self, request, obj=None):
		return request.user.has_perm('CoreFisica.delete_userprofile')
