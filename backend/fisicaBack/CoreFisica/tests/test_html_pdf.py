"""Auth y validacion del endpoint HTML->PDF (/api/v1/html-a-pdf/), sin render real."""
import json
from django.test import TestCase, override_settings


@override_settings(PDF_API_KEY='secreto123')
class HtmlPdfEndpointTests(TestCase):
    URL = '/api/v1/html-a-pdf/'

    def _post(self, body, key=None):
        headers = {}
        if key is not None:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {key}'
        return self.client.post(self.URL, data=json.dumps(body),
                                content_type='application/json', **headers)

    def test_sin_api_key_401(self):
        r = self._post({'html': '<h1>hola</h1>'})
        self.assertEqual(r.status_code, 401)

    def test_api_key_incorrecta_401(self):
        r = self._post({'html': '<h1>hola</h1>'}, key='malo')
        self.assertEqual(r.status_code, 401)

    def test_sin_html_400(self):
        r = self._post({'formato': 'A4'}, key='secreto123')
        self.assertEqual(r.status_code, 400)

    def test_con_html_llega_al_generador(self):
        # Con key + html correctos pasa auth/validacion. Como WeasyPrint no esta
        # instalado en este entorno, debe responder 503 (no 401/400) -> el wiring OK.
        r = self._post({'html': '<h1>hola</h1>'}, key='secreto123')
        self.assertIn(r.status_code, (200, 500, 503))
        self.assertNotIn(r.status_code, (400, 401))
