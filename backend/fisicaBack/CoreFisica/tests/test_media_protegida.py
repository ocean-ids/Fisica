"""/media/: las fotos de personas y los certificados solo se entregan con la firma del enlace o con sesión."""
import json
import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from CoreFisica.media_protegida import firma_de, url_media

TMP = tempfile.mkdtemp(prefix='media_test_')


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


@override_settings(MEDIA_ROOT=TMP)
class MediaProtegidaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for carpeta, nombre, contenido in (('personas', 'foto.jpg', b'JPG'), ('certificados', 'cert.pdf', b'%PDF'),
                                           ('certificados', 'malo.html', b'<script>x</script>'),
                                           ('user_photos', 'yo.png', b'PNG')):
            os.makedirs(os.path.join(TMP, carpeta), exist_ok=True)
            with open(os.path.join(TMP, carpeta, nombre), 'wb') as f:
                f.write(contenido)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)
        super().tearDownClass()

    def test_sin_firma_ni_sesion_no_se_entrega(self):
        self.assertEqual(self.client.get('/media/personas/foto.jpg').status_code, 404)
        self.assertEqual(self.client.get('/media/certificados/cert.pdf').status_code, 404)

    def test_con_firma_correcta_se_entrega(self):
        r = self.client.get(f"/media/personas/foto.jpg?firma={firma_de('personas/foto.jpg')}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), b'JPG')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')

    def test_firma_de_otro_archivo_no_sirve(self):
        r = self.client.get(f"/media/certificados/cert.pdf?firma={firma_de('personas/foto.jpg')}")
        self.assertEqual(r.status_code, 404)

    def test_con_sesion_se_entrega(self):
        User.objects.create_user(username='m', password='MPass12345!', email='m@e.com')
        tok = _login(self.client, 'm', 'MPass12345!')
        r = self.client.get('/media/personas/foto.jpg', HTTP_AUTHORIZATION=f'Bearer {tok}')
        self.assertEqual(r.status_code, 200)

    def test_el_certificado_que_no_es_imagen_se_descarga(self):
        r = self.client.get(f"/media/certificados/malo.html?firma={firma_de('certificados/malo.html')}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Disposition'], 'attachment')       # no se abre dentro de la plataforma

    def test_las_fotos_de_usuarios_siguen_publicas(self):
        self.assertEqual(self.client.get('/media/user_photos/yo.png').status_code, 200)

    def test_no_se_sale_de_media(self):
        self.assertIn(self.client.get('/media/personas/../../settings.py').status_code, (400, 404))

    def test_el_enlace_que_manda_el_servidor_lleva_la_firma(self):
        class F:
            name = 'personas/foto.jpg'
            url = '/media/personas/foto.jpg'
        u = url_media(None, F())
        self.assertIn('firma=', u)
        self.assertEqual(self.client.get(u).status_code, 200)
