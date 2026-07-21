"""Logout tolerante: siempre 200 (no 400) aunque el refresh sea invalido/expirado/blacklisteado."""
import json

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutTests(TestCase):
    URL = '/api/logout/'

    def setUp(self):
        self.user = User.objects.create_user('u_logout', password='x')

    def _post(self, body):
        return self.client.post(self.URL, data=json.dumps(body), content_type='application/json')

    def test_get_405(self):
        self.assertEqual(self.client.get(self.URL).status_code, 405)

    def test_sin_refresh_200(self):
        # Antes daba 400 ("Refresh token requerido"); ahora el logout igual procede.
        self.assertEqual(self._post({}).status_code, 200)

    def test_refresh_invalido_200(self):
        # Antes daba 400 ("Token inválido o expirado"); ahora 200.
        self.assertEqual(self._post({'refresh': 'aaa.bbb.ccc'}).status_code, 200)

    def test_refresh_valido_200(self):
        token = str(RefreshToken.for_user(self.user))
        self.assertEqual(self._post({'refresh': token}).status_code, 200)

    def test_refresh_ya_blacklisteado_200(self):
        # Reproduce el caso del servidor: token ya rotado/blacklisteado -> igual 200.
        token = str(RefreshToken.for_user(self.user))
        self.assertEqual(self._post({'refresh': token}).status_code, 200)   # 1a vez: lo bloquea
        self.assertEqual(self._post({'refresh': token}).status_code, 200)   # 2a vez: ya bloqueado, igual 200
