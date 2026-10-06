"""/media/: las fotos de personas y los certificados solo se entregan con la firma del enlace o con sesión."""
import json
import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from CoreFisica.media_protegida import firma_de, url_media

TMP = tempfile.mkdtemp(prefix='media_test_')
URL_SUBIDA = '/api/personas/{p}/certificados/{t}/archivo/'


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


@override_settings(MEDIA_ROOT=TMP)
class SubidaCertificadoTests(TestCase):
    """Los certificados solo aceptan PDF, JPG o PNG reales de hasta 10 MB."""

    def setUp(self):
        from CoreFisica.models import Persona, TipoCertificado
        User.objects.create_superuser(username='c', password='CPass12345!', email='c@e.com')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'c', 'CPass12345!')}"}
        self.p = Persona.objects.create(nombres='A', apellidos='B', cedula='0910000099', tipo='FIJOS')
        self.t = TipoCertificado.objects.create(nombre='CERT PRUEBA')

    def _subir(self, nombre, contenido):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile(nombre, contenido)
        return self.client.post(self._url(), {'archivo': f}, **self.auth)

    def _url(self):
        return URL_SUBIDA.format(p=self.p.id, t=self.t.id)

    def test_acepta_pdf_jpg_png_reales(self):
        for nombre, contenido in (('a.pdf', b'%PDF-1.4 x'), ('a.jpg', bytes.fromhex('ffd8ffe0') + b'x'),
                                  ('a.png', bytes.fromhex('89504e470d0a1a0a') + b'x')):
            r = self._subir(nombre, contenido)
            self.assertEqual(r.status_code, 200, (nombre, r.content))

    def test_rechaza_otros_tipos(self):
        for nombre in ('a.html', 'a.svg', 'a.exe', 'a.docx', 'sin_extension'):
            r = self._subir(nombre, b'%PDF-1.4')
            self.assertEqual(r.status_code, 400, nombre)
            self.assertIn('PDF, JPG o PNG', r.json()['error'])

    def test_rechaza_un_html_renombrado_a_pdf(self):
        r = self._subir('trampa.pdf', b'<html><script>alert(1)</script></html>')
        self.assertEqual(r.status_code, 400)
        self.assertIn('no es un PDF', r.json()['error'])

    def test_rechaza_mas_de_10_mb(self):
        r = self._subir('grande.pdf', b'%PDF' + b'0' * (10 * 1024 * 1024 + 1))
        self.assertEqual(r.status_code, 400)
