
from django.urls import path
from .views.auth_views import login_view, logout_view, user_view
from .views.persona_views import obtener_personas,actualizar_persona,crear_persona
from .views.puesto_views import crear_puesto,obtener_puestos
from .views.reportes_views import generar_pdf_Horario,generar_excel_horario,export_excel, export_pdf
from .views.instalacion_views import obtener_instalaciones, crear_instalacion, actualizar_instalacion, eliminar_instalacion
from .views.horario_views import obtener_horarios ,crear_horario
from .views.cliente_views import actualizar_cliente,obtener_clientes,crear_cliente, obtener_cliente_id, eliminar_cliente
from .views.asignacion_views import obtener_asignaciones, asignar_servicio,guardar_orden_asignacion,editar_servicio



urlpatterns = [
    path('login/', login_view),
    path('logout/', logout_view),
    path('user/', user_view),
    path('reporte/excel/', export_excel),
    path('reporte/pdf/', export_pdf),
    path('crear-cliente/', crear_cliente),
    path('clientes/', obtener_clientes),
    path('clientes/<str:id>/', obtener_cliente_id),
    path('actualizar-cliente/<int:id>/', actualizar_cliente),
    path('eliminar-cliente/<int:id>/', eliminar_cliente),
    path('crear-persona/', crear_persona),
    path('actualizar-persona/<int:id>/', actualizar_persona),
    path('crear-horario/', crear_horario),
    path('asignar-servicio/', asignar_servicio),
    path('editar-servicio/<str:id>/', editar_servicio),
    path('personas/', obtener_personas),
    path('instalaciones/', obtener_instalaciones),
    path('crear-instalacion/', crear_instalacion),
     path('eliminar-instalacion/<int:id>/', eliminar_instalacion),
    path('crear-puesto/', crear_puesto),
    path('actualizar-instalacion/<int:id>/', actualizar_instalacion),
    path('horarios/', obtener_horarios),
    path('puestos/', obtener_puestos),
    path('asignaciones/<str:mes>/<str:anio>/', obtener_asignaciones),
    path('generar-pdf/', generar_pdf_Horario),
    path('generar-excel/', generar_excel_horario),
    path('guardar-orden/', guardar_orden_asignacion),
    
]

