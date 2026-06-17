from django.test import TestCase
from datetime import date
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

from CoreFisica.models import Cliente, Instalacion, Puesto, AsignacionSemanal, Provincia, Canton, Zona, Horario, Persona, Asignacion, Consolidado


def _login_token(client, username, password):
    """Crea sesión vía /api/login/ y devuelve el access token."""
    resp = client.post(
        '/api/login/',
        data='{"username":"%s","password":"%s"}' % (username, password),
        content_type='application/json',
    )
    return resp.json().get('access')


class SemanasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='semanas_user', password='SemPass123!', email='sem@example.com')
        self.user.user_permissions.add(Permission.objects.get(codename='view_asignacionsemanal'))
        self.access = _login_token(self.client, 'semanas_user', 'SemPass123!')

    def test_semanas_mes_valido(self):
        url = '/api/semanas/?mes=2&anio=2026'
        resp = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('weeks', data)
        self.assertTrue(isinstance(data['weeks'], list))


class AsignacionSemanalListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pag_user', password='PagPass123!', email='pag@example.com')
        self.user.user_permissions.add(Permission.objects.get(codename='view_asignacionsemanal'))
        self.access = _login_token(self.client, 'pag_user', 'PagPass123!')
        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.instalacion, nombre='P0')
        self.horario = Horario.objects.create(hora_ingreso='08:00', hora_salida='20:00')
        self.persona = Persona.objects.create(nombres='X', apellidos='Y', cedula='5234567890')

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access}'}

    def test_lista_devuelve_filas_de_asignacion_activa(self):
        # El endpoint sólo devuelve filas semanales ligadas a asignaciones activas
        # de esa semana (con auto_create+allow_autofill).
        ws = date(2026, 2, 2)
        asignacion = Asignacion.objects.create(
            persona=self.persona, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, horario=self.horario, mes=ws.month, anio=ws.year,
        )
        AsignacionSemanal.objects.create(asignacion=asignacion, puesto=self.puesto, week_start=ws, mon='D')

        url = f'/api/asignacion-semanal/?week_start={ws.isoformat()}&auto_create=true&allow_autofill=true'
        resp = self.client.get(url, **self._auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        rows = data.get('results', data) if isinstance(data, dict) else data
        self.assertIsInstance(rows, list)
        # debe incluir al menos la fila de la asignación activa creada
        self.assertGreaterEqual(len(rows), 1)

    def test_lista_requiere_permiso(self):
        # Usuario sin permiso view_asignacionsemanal -> 403
        otro = User.objects.create_user(username='noperm', password='NoPerm123!', email='np@example.com')
        token = _login_token(self.client, 'noperm', 'NoPerm123!')
        resp = self.client.get('/api/asignacion-semanal/?week_start=2026-02-02', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 403)


class ApiSmokeAuthTests(TestCase):
    def setUp(self):
        self.username = 'smoke_user'
        self.password = 'Sm0kePass123!'
        User.objects.create_user(
            username=self.username,
            password=self.password,
            email='smoke@example.com',
        )

    def test_login_returns_tokens(self):
        response = self.client.post(
            '/api/login/',
            data='{"username":"%s","password":"%s"}' % (self.username, self.password),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('access', payload)
        self.assertIn('refresh', payload)

    def test_v1_login_returns_tokens(self):
        response = self.client.post(
            '/api/v1/login/',
            data='{"username":"%s","password":"%s"}' % (self.username, self.password),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('access', payload)
        self.assertIn('refresh', payload)

    def test_protected_user_endpoint_requires_authentication(self):
        response = self.client.get('/api/user/')
        self.assertIn(response.status_code, [401, 403])

    def test_protected_user_endpoint_with_bearer_token(self):
        login_response = self.client.post(
            '/api/login/',
            data='{"username":"%s","password":"%s"}' % (self.username, self.password),
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        access = login_response.json().get('access')
        self.assertTrue(access)

        response = self.client.get(
            '/api/user/',
            HTTP_AUTHORIZATION=f'Bearer {access}'
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get('username'), self.username)


class UbicacionPermissionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ubic_user',
            password='UbicPass123!',
            email='ubic@example.com',
        )
        login_response = self.client.post(
            '/api/login/',
            data='{"username":"ubic_user","password":"UbicPass123!"}',
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.access_token = login_response.json().get('access')
        self.assertTrue(self.access_token)

        self.provincia = Provincia.objects.get_or_create(nombre='GUAYAS')[0]
        self.canton = Canton.objects.get_or_create(nombre='GUAYAQUIL', provincia=self.provincia)[0]
        self.cliente = Cliente.objects.create(razon_social='ACME SA', nombre_comercial='ACME')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente, canton=self.canton)
        self.zona = Zona.objects.create(instalacion=self.instalacion, titulo='Zona 1')

    def _auth_headers(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}

    def test_provincias_requires_view_perm(self):
        response = self.client.get('/api/provincias/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        perm = Permission.objects.get(codename='view_provincia')
        self.user.user_permissions.add(perm)

        response = self.client.get('/api/provincias/', **self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_cantones_requires_view_perm(self):
        response = self.client.get('/api/cantones/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        perm = Permission.objects.get(codename='view_canton')
        self.user.user_permissions.add(perm)

        response = self.client.get('/api/cantones/', {'provincia_id': self.provincia.id}, **self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_zonas_requires_view_perm(self):
        response = self.client.get('/api/zonas/', {'instalacion_id': self.instalacion.id}, **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        perm = Permission.objects.get(codename='view_zona')
        self.user.user_permissions.add(perm)

        response = self.client.get('/api/zonas/', {'instalacion_id': self.instalacion.id}, **self._auth_headers())
        self.assertEqual(response.status_code, 200)


class CriticalPermissionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='perm_user',
            password='PermPass123!',
            email='perm@example.com',
        )
        login_response = self.client.post(
            '/api/login/',
            data='{"username":"perm_user","password":"PermPass123!"}',
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.access_token = login_response.json().get('access')
        self.assertTrue(self.access_token)

        provincia = Provincia.objects.get_or_create(nombre='PICHINCHA')[0]
        canton = Canton.objects.get_or_create(nombre='QUITO', provincia=provincia)[0]
        cliente = Cliente.objects.create(razon_social='SEGURIDAD SA', nombre_comercial='SEGURIDAD')
        instalacion = Instalacion.objects.create(cliente=cliente, canton=canton)
        puesto = Puesto.objects.create(instalacion=instalacion, nombre='PUESTO TEST')
        horario = Horario.objects.create(hora_ingreso='08:00', hora_salida='20:00')
        persona = Persona.objects.create(nombres='JUAN', apellidos='PEREZ', cedula='1234567890')
        self.asignacion = Asignacion.objects.create(
            persona=persona,
            cliente=cliente,
            instalacion=instalacion,
            puesto=puesto,
            horario=horario,
            mes=date.today().month,
            anio=date.today().year,
        )

    def _auth_headers(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}

    def test_asignar_servicio_requires_add_perm(self):
        response = self.client.post('/api/asignar-servicio/', data='{}', content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='add_asignacion'))
        response = self.client.post('/api/asignar-servicio/', data='{}', content_type='application/json', **self._auth_headers())
        self.assertNotEqual(response.status_code, 403)

    def test_editar_servicio_requires_change_perm(self):
        response = self.client.put('/api/editar-servicio/999999/', data='{}', content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='change_asignacion'))
        response = self.client.put('/api/editar-servicio/999999/', data='{}', content_type='application/json', **self._auth_headers())
        self.assertNotEqual(response.status_code, 403)

    def test_eliminar_asignacion_requires_delete_perm(self):
        response = self.client.delete('/api/eliminar-asignacion/999999/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='delete_asignacion'))
        response = self.client.delete('/api/eliminar-asignacion/999999/', **self._auth_headers())
        self.assertNotEqual(response.status_code, 403)

    def test_reporte_list_requires_view_perm(self):
        response = self.client.get('/api/reporte-asistencia/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='view_reporteasistencia'))
        response = self.client.get('/api/reporte-asistencia/', **self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_reporte_update_requires_change_perm(self):
        response = self.client.put(f'/api/reporte-asistencia/{self.asignacion.id}/', data='{}', content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='change_reporteasistencia'))
        response = self.client.put(f'/api/reporte-asistencia/{self.asignacion.id}/', data='{}', content_type='application/json', **self._auth_headers())
        self.assertNotEqual(response.status_code, 403)

    def test_reporte_export_requires_export_and_view_perm(self):
        response = self.client.get('/api/reporte-asistencia/exportar-excel/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='export_reporte_asistencia'))
        response = self.client.get('/api/reporte-asistencia/exportar-excel/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename='view_reporteasistencia'))
        response = self.client.get('/api/reporte-asistencia/exportar-excel/', **self._auth_headers())
        self.assertNotEqual(response.status_code, 403)


class AsignacionCrudIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='crud_user',
            password='CrudPass123!',
            email='crud@example.com',
        )
        login_response = self.client.post(
            '/api/login/',
            data='{"username":"crud_user","password":"CrudPass123!"}',
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.access_token = login_response.json().get('access')
        self.assertTrue(self.access_token)

        self.mes = date.today().month
        self.anio = date.today().year

        self.provincia = Provincia.objects.get_or_create(nombre='AZUAY')[0]
        self.canton = Canton.objects.get_or_create(nombre='CUENCA', provincia=self.provincia)[0]
        self.cliente = Cliente.objects.create(razon_social='CLIENTE CRUD SA', nombre_comercial='CLIENTE CRUD')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente, canton=self.canton)
        self.puesto_base = Puesto.objects.create(instalacion=self.instalacion, nombre='PUESTO BASE')
        self.puesto_nuevo = Puesto.objects.create(instalacion=self.instalacion, nombre='PUESTO NUEVO')
        self.horario = Horario.objects.create(hora_ingreso='08:00', hora_salida='20:00')

        self.persona_base = Persona.objects.create(nombres='BASE', apellidos='USUARIO', cedula='2234567890')
        self.persona_nueva = Persona.objects.create(nombres='NUEVA', apellidos='PERSONA', cedula='3234567890')

        self.asignacion_base = Asignacion.objects.create(
            persona=self.persona_base,
            cliente=self.cliente,
            instalacion=self.instalacion,
            puesto=self.puesto_base,
            horario=self.horario,
            mes=self.mes,
            anio=self.anio,
        )

    def _auth_headers(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}

    def _grant(self, *codenames):
        for codename in codenames:
            self.user.user_permissions.add(Permission.objects.get(codename=codename))

    def test_asignaciones_list_requires_view_perm(self):
        response = self.client.get(f'/api/asignaciones/?mes={self.mes}&anio={self.anio}', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('view_asignacion')
        response = self.client.get(f'/api/asignaciones/?mes={self.mes}&anio={self.anio}', **self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_create_edit_delete_asignacion_flow(self):
        payload = {
            'persona': self.persona_nueva.id,
            'cliente': self.cliente.id,
            'instalacion': self.instalacion.id,
            'puesto': self.puesto_nuevo.id,
            'horario': self.horario.id,
            'mes': self.mes,
            'anio': self.anio,
            'estado': 'ACTIVO',
            'orden': 5,
        }

        # create
        response = self.client.post('/api/asignar-servicio/', data=payload, content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('add_asignacion')
        response = self.client.post('/api/asignar-servicio/', data=payload, content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 201)
        created_id = response.json().get('id')
        self.assertTrue(created_id)
        self.assertTrue(Asignacion.objects.filter(id=created_id).exists())

        # edit
        response = self.client.put(
            f'/api/editar-servicio/{created_id}/',
            data={'orden': 11},
            content_type='application/json',
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 403)

        self._grant('change_asignacion')
        response = self.client.put(
            f'/api/editar-servicio/{created_id}/',
            data={'orden': 11},
            content_type='application/json',
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Asignacion.objects.get(id=created_id).orden, 11)

        # delete
        response = self.client.delete(f'/api/eliminar-asignacion/{created_id}/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('delete_asignacion')
        response = self.client.delete(f'/api/eliminar-asignacion/{created_id}/', **self._auth_headers())
        self.assertIn(response.status_code, [200, 202, 204])
        self.assertFalse(Asignacion.objects.filter(id=created_id).exists())


class ConsolidadoIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='consol_user',
            password='ConsolPass123!',
            email='consol@example.com',
        )
        login_response = self.client.post(
            '/api/login/',
            data='{"username":"consol_user","password":"ConsolPass123!"}',
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.access_token = login_response.json().get('access')
        self.assertTrue(self.access_token)

        self.fecha = date.today()

        provincia = Provincia.objects.get_or_create(nombre='MANABI')[0]
        canton = Canton.objects.get_or_create(nombre='MANTA', provincia=provincia)[0]
        cliente = Cliente.objects.create(razon_social='CONSOL SA', nombre_comercial='CONSOL')
        instalacion = Instalacion.objects.create(cliente=cliente, canton=canton)
        puesto = Puesto.objects.create(instalacion=instalacion, nombre='PUESTO CONSOL')
        horario = Horario.objects.create(hora_ingreso='07:00', hora_salida='19:00')
        persona = Persona.objects.create(nombres='PEDRO', apellidos='CONSOL', cedula='4234567890')

        self.asignacion = Asignacion.objects.create(
            persona=persona,
            cliente=cliente,
            instalacion=instalacion,
            puesto=puesto,
            horario=horario,
            mes=self.fecha.month,
            anio=self.fecha.year,
        )

    def _auth_headers(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}

    def _grant(self, *codenames):
        for codename in codenames:
            self.user.user_permissions.add(Permission.objects.get(codename=codename))

    def test_consolidado_list_requires_view_perm(self):
        response = self.client.get('/api/consolidado/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('view_consolidado')
        response = self.client.get('/api/consolidado/', **self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_consolidado_crud_and_export_permissions(self):
        payload = {
            'fecha': self.fecha.isoformat(),
            'turno': 'Diurno',
            'tipo': 'GUARDIA',
            'asignacion_ref_id': self.asignacion.id,
            'nominativo': 'NOM-01',
            'proyecto': 'Proyecto Test',
            'puesto': 'Puesto Test',
            'observacion': 'Obs inicial',
        }

        # create
        response = self.client.post('/api/consolidado/crear/', data=payload, content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('add_consolidado')
        response = self.client.post('/api/consolidado/crear/', data=payload, content_type='application/json', **self._auth_headers())
        self.assertEqual(response.status_code, 201)
        consolidado_id = response.json().get('id')
        self.assertTrue(consolidado_id)
        self.assertTrue(Consolidado.objects.filter(id=consolidado_id).exists())

        # update
        response = self.client.put(
            f'/api/consolidado/{consolidado_id}/',
            data={'observacion': 'Obs actualizada'},
            content_type='application/json',
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 403)

        self._grant('change_consolidado')
        response = self.client.put(
            f'/api/consolidado/{consolidado_id}/',
            data={'observacion': 'Obs actualizada'},
            content_type='application/json',
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Consolidado.objects.get(id=consolidado_id).observacion, 'Obs actualizada')

        # export
        response = self.client.get('/api/consolidado/exportar-excel/', {'fecha': self.fecha.isoformat()}, **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('export_consolidado')
        response = self.client.get('/api/consolidado/exportar-excel/', {'fecha': self.fecha.isoformat()}, **self._auth_headers())
        self.assertEqual(response.status_code, 200)

        # delete
        response = self.client.delete(f'/api/consolidado/{consolidado_id}/eliminar/', **self._auth_headers())
        self.assertEqual(response.status_code, 403)

        self._grant('delete_consolidado')
        response = self.client.delete(f'/api/consolidado/{consolidado_id}/eliminar/', **self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Consolidado.objects.filter(id=consolidado_id).exists())


class AuditTrailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='audit_user', password='AudPass123!', email='audit@example.com')
        for cn in ('add_cliente', 'change_cliente', 'delete_cliente'):
            self.user.user_permissions.add(Permission.objects.get(codename=cn))
        self.access = _login_token(self.client, 'audit_user', 'AudPass123!')

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access}'}

    def test_create_update_delete_quedan_auditados_con_usuario(self):
        from CoreFisica.models import AuditLog

        # CREATE
        resp = self.client.post(
            '/api/crear-cliente/',
            data='{"razon_social":"AUD SA","nombre_comercial":"AUD"}',
            content_type='application/json', **self._auth(),
        )
        self.assertEqual(resp.status_code, 201)
        cid = resp.json().get('id')
        log = AuditLog.objects.filter(modelo='Cliente', objeto_id=str(cid), accion='CREATE').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.usuario_id, self.user.id)
        self.assertEqual(log.usuario_str, 'audit_user')

        # UPDATE
        resp = self.client.put(
            f'/api/actualizar-cliente/{cid}/',
            data='{"nombre_comercial":"AUD2"}',
            content_type='application/json', **self._auth(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(modelo='Cliente', objeto_id=str(cid), accion='UPDATE').exists())

        # DELETE
        resp = self.client.delete(f'/api/eliminar-cliente/{cid}/', **self._auth())
        self.assertIn(resp.status_code, [200, 202, 204])
        self.assertTrue(AuditLog.objects.filter(modelo='Cliente', objeto_id=str(cid), accion='DELETE').exists())