"""Login: tras 5 intentos fallidos del mismo usuario desde la misma IP, queda bloqueado 1 minuto (429).
Un login correcto borra el conteo; el bloqueo de un usuario no afecta a otro."""
import json
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase


class LoginBloqueoTests(TestCase):

    def setUp(self):
        cache.clear()
        User.objects.create_user(username='bloq_user', password='BuenaClave123!')
        User.objects.create_user(username='otro_user', password='OtraClave123!')

    def tearDown(self):
        cache.clear()

    def _login(self, username, password, ip='10.0.0.1'):
        return self.client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                                content_type='application/json', REMOTE_ADDR=ip)

    def test_cuatro_fallos_no_bloquean(self):
        for _ in range(4):
            self.assertEqual(self._login('bloq_user', 'mala').status_code, 400)
        self.assertEqual(self._login('bloq_user', 'BuenaClave123!').status_code, 200)

    def test_al_quinto_fallo_queda_bloqueado_aunque_ponga_la_clave_correcta(self):
        for _ in range(4):
            self._login('bloq_user', 'mala')
        r = self._login('bloq_user', 'mala')
        self.assertEqual(r.status_code, 429)
        self.assertIn('en 1 minuto.', r.json()['error'])
        self.assertEqual(self._login('bloq_user', 'BuenaClave123!').status_code, 429)

    def test_mayusculas_cuentan_como_el_mismo_usuario(self):
        for nombre in ('bloq_user', 'BLOQ_USER', 'Bloq_User', 'bloq_user', 'BLOQ_user'):
            self._login(nombre, 'mala')
        self.assertEqual(self._login('bloq_user', 'BuenaClave123!').status_code, 429)

    def test_no_afecta_a_otro_usuario_ni_a_otra_ip(self):
        for _ in range(5):
            self._login('bloq_user', 'mala')
        self.assertEqual(self._login('otro_user', 'OtraClave123!').status_code, 200)
        self.assertEqual(self._login('bloq_user', 'BuenaClave123!', ip='10.0.0.2').status_code, 200)

    def test_un_login_correcto_reinicia_el_conteo(self):
        for _ in range(4):
            self._login('bloq_user', 'mala')
        self.assertEqual(self._login('bloq_user', 'BuenaClave123!').status_code, 200)
        for _ in range(4):
            self.assertEqual(self._login('bloq_user', 'mala').status_code, 400)

    def test_pasado_el_tiempo_se_desbloquea(self):
        import time
        for _ in range(5):
            self._login('bloq_user', 'mala')
        with mock.patch('time.time', return_value=time.time() + 1 * 60 + 1):
            self.assertEqual(self._login('bloq_user', 'BuenaClave123!').status_code, 200)

    def test_inventar_x_forwarded_for_no_salta_el_bloqueo(self):
        for i in range(5):
            self.client.post('/api/login/', data=json.dumps({'username': 'bloq_user', 'password': 'mala'}),
                             content_type='application/json', REMOTE_ADDR='172.18.0.5',
                             HTTP_X_REAL_IP='200.1.1.1', HTTP_X_FORWARDED_FOR=f'9.9.9.{i}, 200.1.1.1')
        r = self.client.post('/api/login/', data=json.dumps({'username': 'bloq_user', 'password': 'BuenaClave123!'}),
                             content_type='application/json', REMOTE_ADDR='172.18.0.5',
                             HTTP_X_REAL_IP='200.1.1.1', HTTP_X_FORWARDED_FOR='8.8.8.8, 200.1.1.1')
        self.assertEqual(r.status_code, 429)
