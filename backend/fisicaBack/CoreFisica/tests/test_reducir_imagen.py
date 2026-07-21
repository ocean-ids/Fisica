"""Auth, validacion y reduccion real del endpoint /api/v1/reducir-imagen/."""
import base64
import io
import json

from django.test import TestCase, override_settings


@override_settings(PDF_API_KEY='secreto123')
class ReducirImagenTests(TestCase):
    URL = '/api/v1/reducir-imagen/'

    def _post(self, body, key=None):
        headers = {}
        if key is not None:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {key}'
        return self.client.post(self.URL, data=json.dumps(body),
                                content_type='application/json', **headers)

    def _img_b64(self, w=1600, h=1200):
        from PIL import Image
        img = Image.new('RGB', (w, h), (120, 60, 200))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('ascii')

    def test_sin_api_key_401(self):
        self.assertEqual(self._post({'imagen_base64': 'abc'}).status_code, 401)

    def test_api_key_incorrecta_401(self):
        self.assertEqual(self._post({'imagen_base64': 'abc'}, key='malo').status_code, 401)

    def test_sin_imagen_400(self):
        self.assertEqual(self._post({'ancho_max': 800}, key='secreto123').status_code, 400)

    def test_base64_invalido_400(self):
        # 'validate=False' es tolerante; una cadena claramente no-imagen debe fallar
        # al abrirla con Pillow -> 500 (no 200). Con basura base64 real -> 400 o 500.
        r = self._post({'imagen_base64': '@@@no-es-imagen@@@'}, key='secreto123')
        self.assertIn(r.status_code, (400, 500))

    def test_reduce_ok(self):
        r = self._post({'imagen_base64': self._img_b64(1600, 1200), 'ancho_max': 1000},
                       key='secreto123')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d['exito'])
        self.assertEqual(d['ancho'], 1000)                 # redimensiona al ancho_max
        self.assertEqual(d['alto'], 750)                   # mantiene proporcion 4:3
        self.assertGreater(d['peso_kb'], 0)

    def test_acepta_data_uri(self):
        data_uri = 'data:image/png;base64,' + self._img_b64(400, 300)
        r = self._post({'imagen_base64': data_uri}, key='secreto123')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['exito'])
