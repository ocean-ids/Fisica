"""Al desactivar una persona con asignación activa, el puesto pasa a HUECA desde HOY;
los días pasados conservan a la persona en el reporte de asistencia."""
import json
import datetime
from unittest import mock
from django.test import TestCase
from django.contrib.auth.models import User

from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion,
    ReporteAsistencia, AsignacionPersonaPeriodo,
)


def _login_token(client, username, password):
    resp = client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                       content_type='application/json')
    return resp.json().get('access')


class DesactivarHuecaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='des_user', password='DesPass123!', email='d@e.com')
        self.access = _login_token(self.client, 'des_user', 'DesPass123!')

        self.anio, self.mes = 2026, 6
        self.hoy = datetime.date(self.anio, self.mes, 15)      # fecha simulada del cambio
        self.dia5 = datetime.date(self.anio, self.mes, 5)      # pasado
        self.dia15 = datetime.date(self.anio, self.mes, 15)    # hoy

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.instalacion, nombre='P1')
        self.a = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111',
                                        tipo='FIJOS', estado_empleado='ACTIVO')
        self.asig = Asignacion.objects.create(
            persona=self.a, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        # Día pasado con ANA marcada ASISTIO (ReporteAsistencia es OneToOne por asignación).
        ReporteAsistencia.objects.create(asignacion=self.asig, persona=self.a,
                                         fecha_reporte=self.dia5, estado='TURNO', estado_asistencia='ASISTIO')

    def _desactivar(self):
        with mock.patch('CoreFisica.views.persona_views.timezone.localdate', return_value=self.hoy):
            return self.client.post(f'/api/disable-persona/{self.a.id}/',
                                    HTTP_AUTHORIZATION=f'Bearer {self.access}')

    def test_asignacion_pasa_a_hueca_y_conserva_pasado(self):
        resp = self._desactivar()
        self.assertEqual(resp.status_code, 200)

        self.asig.refresh_from_db()
        self.a.refresh_from_db()
        # La persona quedó inactiva; la asignación quedó HUECA (sin persona).
        self.assertFalse(self.a.is_active)
        self.assertIsNone(self.asig.persona_id)
        self.assertTrue(self.asig.es_hueca)

        # Períodos: ANA hasta ayer (día 14); HUECA (None) desde hoy (día 15).
        periodos = list(AsignacionPersonaPeriodo.objects.filter(asignacion=self.asig).order_by('desde'))
        self.assertEqual(len(periodos), 2)
        self.assertEqual(periodos[0].persona_id, self.a.id)
        self.assertEqual(periodos[0].hasta, self.dia15 - datetime.timedelta(days=1))
        self.assertIsNone(periodos[1].persona_id)
        self.assertEqual(periodos[1].desde, self.dia15)

        # El registro del día pasado (5) se conserva (fecha < hoy).
        self.assertTrue(ReporteAsistencia.objects.filter(asignacion=self.asig, fecha_reporte=self.dia5).exists())

    def test_registro_de_hoy_se_borra(self):
        # Si el override es de HOY, al desactivar se borra (queda hueca limpia).
        b = Persona.objects.create(nombres='BETO', apellidos='DOS', cedula='0222222222',
                                   tipo='FIJOS', estado_empleado='ACTIVO')
        asig_b = Asignacion.objects.create(
            persona=b, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        ReporteAsistencia.objects.create(asignacion=asig_b, persona=b,
                                         fecha_reporte=self.dia15, estado='TURNO', estado_asistencia='ASISTIO')
        with mock.patch('CoreFisica.views.persona_views.timezone.localdate', return_value=self.hoy):
            self.client.post(f'/api/disable-persona/{b.id}/', HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertFalse(ReporteAsistencia.objects.filter(asignacion=asig_b).exists())

    def test_reporte_muestra_persona_en_pasado_y_hueca_hoy(self):
        self._desactivar()

        r5 = self.client.get(f'/api/reporte-asistencia/?fecha={self.dia5.isoformat()}',
                             HTTP_AUTHORIZATION=f'Bearer {self.access}').json()
        fila5 = next((x for x in r5.get('results', []) if x.get('asignacion_id') == self.asig.id), None)
        self.assertIsNotNone(fila5, 'La asignación debe seguir apareciendo el día pasado')
        self.assertEqual(fila5['nombre_apellidos'], 'ANA UNO')
        self.assertFalse(fila5.get('hueca'))

        r15 = self.client.get(f'/api/reporte-asistencia/?fecha={self.dia15.isoformat()}',
                              HTTP_AUTHORIZATION=f'Bearer {self.access}').json()
        fila15 = next((x for x in r15.get('results', []) if x.get('asignacion_id') == self.asig.id), None)
        self.assertIsNotNone(fila15, 'La asignación debe aparecer hoy como HUECA')
        self.assertEqual(fila15['nombre_apellidos'], 'HUECA')
        self.assertTrue(fila15.get('hueca'))
