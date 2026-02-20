
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,)
from .views.auth_views import login_view, logout_view, user_view, solicitar_reset_password, reset_password
from .views.cliente_views import actualizar_cliente, obtener_clientes,crear_cliente, obtener_cliente_id, eliminar_cliente
from .views.importar_clientes import importar_clientes
from .views.instalacion_views import obtener_instalaciones, crear_instalacion, actualizar_instalacion, eliminar_instalacion
from .views.persona_views import obtener_personas, actualizar_persona, crear_persona, eliminar_persona, disable_persona, enable_persona, importar_personas
from .views.puesto_views import crear_puesto, obtener_puestos, obtener_puestos_por_instalacion, obtener_puestos_por_cliente, actualizar_puesto, eliminar_puesto
from .views.horario_views import obtener_horarios, crear_horario, actualizar_horario, eliminar_horario, crear_patron, obtener_patrones, actualizar_patron, eliminar_patron
from .views.asignacion_views import obtener_asignaciones, asignar_servicio, editar_servicio, guardar_orden_asignacion, eliminar_asignacion, exportar_asignaciones_excel
from .views.asignacion_semanal_views import listar_asignacion_semanal, semanas_del_mes, crear_o_actualizar_asignacion_semanal, copiar_semana


urlpatterns = [
    path('login/', login_view),
    path('logout/', logout_view),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/', user_view),
    path('solicitar-reset-password/', solicitar_reset_password),
    path('reset-password/<str:uidb64>/<str:token>/', reset_password),
    path('crear-cliente/', crear_cliente),
    path('clientes/', obtener_clientes),
    path('clientes/<str:id>/', obtener_cliente_id),
    path('actualizar-cliente/<int:id>/', actualizar_cliente),
    path('eliminar-cliente/<int:id>/', eliminar_cliente),
    path('importar-clientes/', importar_clientes),
    path('personas/', obtener_personas),
    path('crear-persona/', crear_persona),
    path('actualizar-persona/<int:id>/', actualizar_persona),
    path('eliminar-persona/<int:id>/', eliminar_persona),
    path('importar-personas/', importar_personas),
    path('disable-persona/<int:id>/', disable_persona),
    path('enable-persona/<int:id>/', enable_persona),
    path('crear-horario/', crear_horario),
    path('instalaciones/', obtener_instalaciones),
    path('crear-instalacion/', crear_instalacion),
    path('actualizar-instalacion/<int:id>/', actualizar_instalacion),
    path('eliminar-instalacion/<int:id>/', eliminar_instalacion),
    path('horarios/', obtener_horarios),
    path('crear-horario/', crear_horario),
    path('actualizar-horario/<int:id>/', actualizar_horario),
    path('eliminar-horario/<int:id>/', eliminar_horario),
    path('patrones/', obtener_patrones),
    path('crear-patron/', crear_patron),
    path('actualizar-patron/<int:id>/', actualizar_patron),
    path('eliminar-patron/<int:id>/', eliminar_patron),
    path('puestos/', obtener_puestos),
    path('crear-puesto/', crear_puesto),
    path('actualizar-puesto/<int:id>/', actualizar_puesto),
    path('eliminar-puesto/<int:id>/', eliminar_puesto),
    path('puestos/instalacion/<int:instalacion_id>/', obtener_puestos_por_instalacion),
    path('puestos/cliente/<int:cliente_id>/', obtener_puestos_por_cliente),
    path('asignaciones/<int:mes>/<int:anio>/', obtener_asignaciones),
    path('asignar-servicio/', asignar_servicio),
    path('editar-servicio/<int:id>/', editar_servicio),
    path('asignaciones/', obtener_asignaciones),
    path('guardar-orden-asignacion/', guardar_orden_asignacion),
    path('eliminar-asignacion/<int:id>/', eliminar_asignacion),
    path('reporte-asignaciones/', exportar_asignaciones_excel, name='reporte_asignaciones'),
    path('asignacion-semanal/', listar_asignacion_semanal),
    path('asignacion-semanal/guardar/', crear_o_actualizar_asignacion_semanal),
    path('asignacion-semanal/copy/', copiar_semana),
    path('semanas/', semanas_del_mes, name='semanas')
]

