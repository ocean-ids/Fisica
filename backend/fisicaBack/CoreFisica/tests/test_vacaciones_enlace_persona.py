"""Sacavacaciones: si 'quién cubre' / 'quién sale' llegan solo como TEXTO (se escribió el
nombre sin elegirlo de la lista), al guardar se enlaza la persona por nombre. Sin ese enlace el
Reporte de Asistencia no pone al sacavacaciones en el puesto (bug: seguía saliendo el fijo)."""
import json

from django.test import TestCase
from django.contrib.auth.models import User

from CoreFisica.models import Persona, ReporteVacaciones


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class VacacionesEnlacePersonaTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='vac_admin', email='v@e.com', password='VacPass123!')
        self.tok = _login(self.client, 'vac_admin', 'VacPass123!')
        self.sale = Persona.objects.create(nombres='JACINTO ALBERTO', apellidos='FRANCO VILLEGAS',
                                           cedula='0910000001', tipo='FIJOS')
        self.cubre = Persona.objects.create(nombres='GLADYS MARIA', apellidos='TOMALA CASSAGNE',
                                            cedula='0910000002', tipo='SACAVACACIONES')
        self.tilde = Persona.objects.create(nombres='JORGE ANDRES', apellidos='CEDEÑO BOHORQUEZ',
                                            cedula='0910000003', tipo='SACAVACACIONES')

    def _post(self, **datos):
        base = {'cliente': 'RIVERFRONT 2', 'fecha_desde': '2026-09-17', 'fecha_hasta': '2026-10-08', 'dias': 22}
        base.update(datos)
        return self.client.post('/api/reporte-vacaciones/crear/', data=json.dumps(base),
                                content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.tok}')

    def test_texto_sin_persona_se_enlaza_por_nombre(self):
        r = self._post(persona_sale='JACINTO ALBERTO FRANCO VILLEGAS',
                       sacavacaciones='GLADYS MARIA TOMALA CASSAGNE')
        self.assertEqual(r.status_code, 201, r.content)
        v = ReporteVacaciones.objects.get(id=r.json()['id'])
        self.assertEqual(v.persona_sale_ref_id, self.sale.id)
        self.assertEqual(v.sacavacaciones_ref_id, self.cubre.id)

    def test_apellidos_primero_y_sin_tildes(self):
        r = self._post(persona_sale_ref=self.sale.id, persona_sale='x',
                       sacavacaciones='cedeno bohorquez jorge andres')
        v = ReporteVacaciones.objects.get(id=r.json()['id'])
        self.assertEqual(v.sacavacaciones_ref_id, self.tilde.id)

    def test_nombre_inexistente_no_enlaza(self):
        r = self._post(persona_sale_ref=self.sale.id, persona_sale='x', sacavacaciones='NADIE CON ESTE NOMBRE')
        v = ReporteVacaciones.objects.get(id=r.json()['id'])
        self.assertIsNone(v.sacavacaciones_ref_id)
