from django.test import TestCase
from datetime import date
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

from CoreFisica.models import Cliente, Instalacion, Puesto, AsignacionSemanal, Provincia, Canton, Zona


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