"""Smoke test del PDF del Reporte de Asistencia: genera OK y en tamaño HORIZONTAL (carta
landscape). No repetir el encabezado en cada página se valida por inspección visual; aquí
solo se asegura que la exportación no falle y salga en landscape."""
import json
import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from CoreFisica.models import Cliente, Instalacion, Puesto, Persona, Asignacion


def _login_token(client, username, password):
    resp = client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                       content_type='application/json')
    return resp.json().get('access')


class ExportPdfPortraitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='pdf_user', password='PdfPass123!', email='p@e.com')
        self.access = _login_token(self.client, 'pdf_user', 'PdfPass123!')
        hoy = timezone.localdate()
        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.inst = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='P1')
        self.persona = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111', tipo='FIJOS')
        Asignacion.objects.create(
            persona=self.persona, cliente=self.cliente, instalacion=self.inst,
            puesto=self.puesto, mes=hoy.month, anio=hoy.year, estado='ACTIVO',
        )
        self.fecha = hoy.isoformat()

    def test_pdf_se_genera_en_horizontal(self):
        r = self.client.get(f'/api/reporte-asistencia/exportar-pdf/?fecha={self.fecha}',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        contenido = r.content
        self.assertTrue(contenido.startswith(b'%PDF'), 'El contenido debe ser un PDF')
        # Carta landscape: MediaBox 792 x 612 (ancho x alto). Ancho > alto = horizontal.
        self.assertIn(b'/MediaBox', contenido)
        self.assertIn(b'792 612', contenido)       # ancho 792 (11") x alto 612 (8.5") = horizontal
        self.assertNotIn(b'612 792', contenido)    # no debe ser vertical
