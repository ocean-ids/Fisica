
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,)
from .views.auth_views import login_view, logout_view, user_view, user_profile_view, solicitar_reset_password, reset_password
from .views.cliente_views import actualizar_cliente, obtener_clientes,crear_cliente, obtener_cliente_id, eliminar_cliente
from .views.importar_clientes import importar_clientes
from .views.importar_puestos_asignaciones import importar_puestos_asignaciones
from .views.ubicacion_views import obtener_provincias, obtener_cantones, obtener_zonas
from .views.instalacion_views import obtener_instalaciones, crear_instalacion, actualizar_instalacion, eliminar_instalacion
from .views.persona_views import obtener_personas, actualizar_persona, crear_persona, eliminar_persona, disable_persona, enable_persona, importar_personas, exportar_personas_excel, SacafrancoListView, asignar_sacafranco, desasignar_sacafranco
from .views.puesto_views import crear_puesto, obtener_puestos, obtener_puestos_por_instalacion, obtener_puestos_por_cliente, actualizar_puesto, eliminar_puesto
from .views.horario_views import obtener_horarios, crear_horario, actualizar_horario, eliminar_horario
from .views.asignacion_views import obtener_asignaciones, asignar_servicio, editar_servicio, guardar_orden_asignacion, guardar_orden_sacafranco, eliminar_asignacion, exportar_asignaciones_excel, sacafranco_filas, eliminar_sacafranco_fila, asignaciones_vacantes, personas_asignadas
from .views.asignacion_semanal_views import listar_asignacion_semanal, listar_asignacion_semanal_mes, semanas_del_mes, crear_o_actualizar_asignacion_semanal, copiar_semana, listar_sacafranco_fila_semanal, crear_o_actualizar_sacafranco_fila_semanal
from .views.patron_asignacion_views import PatronAsignacionListCreateView, PatronAsignacionRetrieveUpdateDestroyView
from .views.reporte_asistencia_views import obtener_reporte_asistencia, listar_descripciones_reporte, insertar_reporte_asistencia, historial_reporte_asistencia, exportar_reporte_asistencia_excel, exportar_reporte_asistencia_pdf
from .views.consolidado_views import obtener_consolidado, crear_consolidado, actualizar_consolidado, eliminar_consolidado, obtener_consolidado_armado, exportar_consolidado_excel, exportar_consolidado_pdf, obtener_consolidado_resumen, actualizar_consolidado_resumen
from .views.vista_canton_views import vistas_cantones
from .views.novedad_puesto_views import obtener_novedades, crear_novedad, actualizar_novedad, eliminar_novedad, exportar_novedades_excel

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('login/', login_view),
    path('logout/', logout_view),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/', user_view),
    path('user/profile/', user_profile_view),
    path('solicitar-reset-password/', solicitar_reset_password),
    path('reset-password/<str:uidb64>/<str:token>/', reset_password),
    path('crear-cliente/', crear_cliente),
    path('clientes/', obtener_clientes),
    path('clientes/<str:id>/', obtener_cliente_id),
    path('actualizar-cliente/<int:id>/', actualizar_cliente),
    path('eliminar-cliente/<int:id>/', eliminar_cliente),
    path('importar-clientes/', importar_clientes),
    path('importar-puestos-asignaciones/', importar_puestos_asignaciones),
    path('personas/', obtener_personas),
    path('crear-persona/', crear_persona),
    path('actualizar-persona/<int:id>/', actualizar_persona),
    path('eliminar-persona/<int:id>/', eliminar_persona),
    path('importar-personas/', importar_personas),
    path('exportar-personas-excel/', exportar_personas_excel, name='exportar-personas-excel'),
    path('personas/sacafrancos/', SacafrancoListView.as_view(), name='sacafrancos-list'),
    path('personas/sacafrancos/assign/', asignar_sacafranco, name='sacafrancos-assign'),
    path('personas/sacafrancos/unassign/', desasignar_sacafranco, name='sacafrancos-unassign'),
    path('disable-persona/<int:id>/', disable_persona),
    path('enable-persona/<int:id>/', enable_persona),
    path('provincias/', obtener_provincias),
    path('cantones/', obtener_cantones),
    path('zonas/', obtener_zonas),
    path('instalaciones/', obtener_instalaciones),
    path('crear-instalacion/', crear_instalacion),
    path('actualizar-instalacion/<int:id>/', actualizar_instalacion),
    path('eliminar-instalacion/<int:id>/', eliminar_instalacion),
    path('horarios/', obtener_horarios),
    path('crear-horario/', crear_horario),
    path('actualizar-horario/<int:id>/', actualizar_horario),
    path('eliminar-horario/<int:id>/', eliminar_horario),
    path('puestos/', obtener_puestos),
    path('crear-puesto/', crear_puesto),
    path('actualizar-puesto/<int:id>/', actualizar_puesto),
    path('eliminar-puesto/<int:id>/', eliminar_puesto),
    path('puestos/instalacion/<int:instalacion_id>/', obtener_puestos_por_instalacion),
    path('puestos/cliente/<int:cliente_id>/', obtener_puestos_por_cliente),
    path('asignaciones/<int:mes>/<int:anio>/', obtener_asignaciones),
    path('asignaciones-vacantes/<int:mes>/<int:anio>/', asignaciones_vacantes),
    path('personas-asignadas/<int:mes>/<int:anio>/', personas_asignadas),
    path('asignar-servicio/', asignar_servicio),
    path('editar-servicio/<int:id>/', editar_servicio),
    path('asignaciones/', obtener_asignaciones),
    path('guardar-orden-asignacion/', guardar_orden_asignacion),
    path('guardar-orden-sacafranco/', guardar_orden_sacafranco),
    path('eliminar-asignacion/<int:id>/', eliminar_asignacion),
    path('sacafranco-filas/', sacafranco_filas),
    path('sacafranco-filas/<int:id>/', eliminar_sacafranco_fila),
    path('vistas-cantones/', vistas_cantones),
    path('reporte-asignaciones/', exportar_asignaciones_excel, name='reporte_asignaciones'),
    path('asignacion-semanal/', listar_asignacion_semanal),
    path('asignacion-semanal/mes/', listar_asignacion_semanal_mes),
    path('asignacion-semanal/guardar/', crear_o_actualizar_asignacion_semanal),
    path('sacafranco-fila-semanal/', listar_sacafranco_fila_semanal),
    path('sacafranco-fila-semanal/guardar/', crear_o_actualizar_sacafranco_fila_semanal),
    path('asignacion-semanal/copy/', copiar_semana),
    path('semanas/', semanas_del_mes, name='semanas'),
    path('patrones/', PatronAsignacionListCreateView.as_view(), name='patron-list-create'),
    path('patrones/<int:pk>/', PatronAsignacionRetrieveUpdateDestroyView.as_view(), name='patron-detail'),
    path('reporte-asistencia/', obtener_reporte_asistencia, name='reporte-asistencia'),
    path('reporte-asistencia/descripciones/', listar_descripciones_reporte, name='reporte-asistencia-descripciones'),
    path('reporte-asistencia/<int:asignacion_id>/', insertar_reporte_asistencia, name='reporte-asistencia-update'),
    path('reporte-asistencia/<int:asignacion_id>/historial/', historial_reporte_asistencia, name='reporte-asistencia-historial'),
    path('reporte-asistencia/exportar-excel/', exportar_reporte_asistencia_excel, name='reporte-asistencia-excel'),
    path('reporte-asistencia/exportar-pdf/', exportar_reporte_asistencia_pdf, name='reporte-asistencia-pdf'),
    path('consolidado/', obtener_consolidado),
    path('consolidado/armado/', obtener_consolidado_armado),
    path('consolidado/resumen/', obtener_consolidado_resumen),
    path('consolidado/crear/', crear_consolidado),
    path('consolidado/<int:id>/', actualizar_consolidado),
    path('consolidado/<int:id>/eliminar/', eliminar_consolidado),
    path('consolidado/resumen/actualizar/', actualizar_consolidado_resumen),
    path('consolidado/exportar-excel/', exportar_consolidado_excel),
    path('consolidado/exportar-pdf/', exportar_consolidado_pdf),
    path('novedades-puesto/', obtener_novedades),
    path('novedades-puesto/crear/', crear_novedad),
    path('novedades-puesto/<int:id>/', actualizar_novedad),
    path('novedades-puesto/<int:id>/eliminar/', eliminar_novedad),
    path('novedades-puesto/exportar-excel/', exportar_novedades_excel),

]

