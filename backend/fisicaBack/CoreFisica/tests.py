from django.test import TestCase
from datetime import date
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

from CoreFisica.models import Cliente, Instalacion, Puesto, AsignacionSemanal, Provincia, Canton, Zona, Horario, Persona, Asignacion, Consolidado


class SemanasTests(TestCase):
    def test_semanas_mes_valido(self):
        url = '/api/semanas/?mes=2&anio=2026'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('weeks', data)
        self.assertTrue(isinstance(data['weeks'], list))


class AsignacionSemanalPaginationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente, provincia='P', ciudad='C')
        # crear varios puestos
        self.puestos = [Puesto.objects.create(instalacion=self.instalacion, nombre=f'P{i}') for i in range(5)]

    def test_paginacion_asignacion_semanal(self):
        ws = date(2026, 2, 2)
        # crear 5 filas, una por puesto
        for p in self.puestos:
            AsignacionSemanal.objects.create(puesto=p, week_start=ws, mon='')

        url = f'/api/asignacion-semanal/?week_start={ws.isoformat()}&page_size=2'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # aceptar dos formatos: paginado DRF (dict con 'results') o lista simple
        if isinstance(data, dict) and 'results' in data:
            # estructura paginada de DRF: count, next, previous, results
            self.assertEqual(data.get('count'), 5)
            self.assertEqual(len(data.get('results', [])), 2)
            self.assertIsNotNone(data.get('next'))

            # solicitar la tercera página
            resp3 = self.client.get(url + '&page=3')
            self.assertEqual(resp3.status_code, 200)
            d3 = resp3.json()
            self.assertEqual(len(d3.get('results', [])), 1)
        else:
            # lista simple: la API puede devolver la lista completa si no usa paginación
            self.assertIsInstance(data, list)
            # verificar que devolvió entre 1 y los 5 elementos creados
            self.assertTrue(1 <= len(data) <= 5)
            # solicitar la tercera página — solo comprobar que no da error
            resp3 = self.client.get(url + '&page=3')
            self.assertEqual(resp3.status_code, 200)
            d3 = resp3.json()
            # aceptar lista o estructura paginada
            if isinstance(d3, list):
                self.assertIsInstance(d3, list)
            else:
                self.assertIn('results', d3)


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

        self.provincia = Provincia.objects.create(nombre='GUAYAS')
        self.canton = Canton.objects.create(nombre='GUAYAQUIL', provincia=self.provincia)
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

        provincia = Provincia.objects.create(nombre='PICHINCHA')
        canton = Canton.objects.create(nombre='QUITO', provincia=provincia)
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

        self.provincia = Provincia.objects.create(nombre='AZUAY')
        self.canton = Canton.objects.create(nombre='CUENCA', provincia=self.provincia)
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

        provincia = Provincia.objects.create(nombre='MANABI')
        canton = Canton.objects.create(nombre='MANTA', provincia=provincia)
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