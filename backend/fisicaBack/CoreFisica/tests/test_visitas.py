"""Visitas del supervisor: GPS revalidado en el servidor y envíos que no se duplican (app sin conexión)."""
import json
import uuid

from django.contrib.auth.models import Permission, User
from django.test import SimpleTestCase, TestCase

from CoreFisica.models import Cliente, Instalacion, Puesto, VisitaSupervisor
from CoreFisica.views.visita_views import distancia_m, evaluar_gps


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class DistanciaTests(SimpleTestCase):
    def test_haversine(self):
        self.assertAlmostEqual(distancia_m(-2.17, -79.92, -2.17, -79.92), 0, places=3)
        # 0.001 grados de latitud = unos 111 m
        self.assertTrue(105 < distancia_m(-2.170, -79.92, -2.171, -79.92) < 117)


class VisitasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sup', password='SupPass123!', email='s@e.com')
        for c in ('add_visitasupervisor', 'view_visitasupervisor'):
            self.user.user_permissions.add(Permission.objects.get(codename=c))
        self.sin = User.objects.create_user(username='sin', password='SinPass123!', email='x@e.com')
        self.tok = _login(self.client, 'sup', 'SupPass123!')
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        self.inst = Instalacion.objects.create(cliente=cli, nombre='PUESTO', codigo='K1')
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='GARITA')

    def _auth(self, tok=None):
        return {'HTTP_AUTHORIZATION': f'Bearer {tok or self.tok}'}

    def _enviar(self, **over):
        body = {'uuid_cliente': str(uuid.uuid4()), 'instalacion_id': self.inst.id, 'puesto_id': self.puesto.id,
                'fecha_hora': '2026-10-06T10:00:00-05:00', 'latitud': -2.17, 'longitud': -79.92, 'precision_m': 10}
        body.update(over)
        return self.client.post('/api/visitas/', data=json.dumps(body), content_type='application/json', **self._auth())

    def _ubicar(self, lat=-2.17, lon=-79.92):
        Instalacion.objects.filter(id=self.inst.id).update(latitud=lat, longitud=lon, ubicacion_confirmada=True)
        self.inst.refresh_from_db()

    def test_sin_ubicacion_del_puesto_se_guarda_igual(self):
        r = self._enviar()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['estado_gps'], 'SIN_UBICACION_PUESTO')

    def test_dentro_del_radio_es_ok(self):
        self._ubicar()
        self.assertEqual(self._enviar(latitud=-2.1705).json()['estado_gps'], 'OK')          # ~55 m, radio 150

    def test_fuera_del_radio(self):
        self._ubicar()
        r = self._enviar(latitud=-2.175).json()                                              # ~550 m
        self.assertEqual(r['estado_gps'], 'FUERA_DE_RANGO')
        self.assertGreater(r['distancia_m'], 150)

    def test_precision_baja_se_guarda_marcada(self):
        self._ubicar()
        r = self._enviar(precision_m=120)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['estado_gps'], 'PRECISION_BAJA')

    def test_sin_gps(self):
        r = self._enviar(latitud=None, longitud=None, precision_m=None)
        self.assertEqual(r.json()['estado_gps'], 'SIN_GPS')

    def test_reenviar_la_misma_visita_no_duplica(self):
        uid = str(uuid.uuid4())
        a = self._enviar(uuid_cliente=uid)
        b = self._enviar(uuid_cliente=uid)
        self.assertEqual((a.status_code, b.status_code), (201, 200))
        self.assertTrue(b.json()['duplicada'])
        self.assertEqual(a.json()['id'], b.json()['id'])
        self.assertEqual(VisitaSupervisor.objects.count(), 1)

    def test_validaciones(self):
        self.assertEqual(self._enviar(uuid_cliente='no-es-uuid').status_code, 400)
        self.assertEqual(self._enviar(instalacion_id=99999).status_code, 400)
        self.assertEqual(self._enviar(latitud=-2.17, longitud=None).status_code, 400)      # una sola coordenada
        self.assertEqual(self._enviar(latitud=200, longitud=-79.9).status_code, 400)       # fuera de rango
        self.assertEqual(VisitaSupervisor.objects.count(), 0)

    def test_sin_permiso_no_registra_ni_lista(self):
        tok = _login(self.client, 'sin', 'SinPass123!')
        r = self.client.post('/api/visitas/', data=json.dumps({'uuid_cliente': str(uuid.uuid4()), 'instalacion_id': self.inst.id}),
                             content_type='application/json', **self._auth(tok))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get('/api/visitas/', **self._auth(tok)).status_code, 403)

    def test_listar_por_fecha(self):
        self._enviar()
        r = self.client.get('/api/visitas/?fecha=2026-10-06', **self._auth())
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(len(self.client.get('/api/visitas/?fecha=2026-10-07', **self._auth()).json()), 0)

    def test_consola_confirma_la_ubicacion_del_puesto(self):
        v = self._enviar().json()
        consola = User.objects.create_superuser(username='con', password='ConPass123!', email='c@e.com')
        tok = _login(self.client, 'con', 'ConPass123!')
        r = self.client.post(f"/api/visitas/{v['id']}/confirmar-ubicacion/", **self._auth(tok))
        self.assertEqual(r.status_code, 200, r.content)
        self.inst.refresh_from_db()
        self.assertTrue(self.inst.ubicacion_confirmada)
        self.assertAlmostEqual(float(self.inst.latitud), -2.17, places=5)
        # a partir de aquí las visitas se comparan contra esa ubicación
        self.assertEqual(self._enviar(latitud=-2.175).json()['estado_gps'], 'FUERA_DE_RANGO')
        # sin permiso de cambiar instalaciones, no puede
        self.assertEqual(self.client.post(f"/api/visitas/{v['id']}/confirmar-ubicacion/", **self._auth()).status_code, 403)
