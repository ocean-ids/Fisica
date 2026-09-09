"""Vigencia por fecha al cambiar el guardia de un puesto:
los días pasados conservan a la persona anterior; de la fecha del cambio en adelante, la nueva."""
import json
import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion,
    ReporteAsistencia, AsignacionPersonaPeriodo,
)


def _login_token(client, username, password):
    resp = client.post(
        '/api/login/',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json',
    )
    return resp.json().get('access')


class VigenciaPersonaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='vig_user', password='VigPass123!', email='vig@example.com'
        )
        self.access = _login_token(self.client, 'vig_user', 'VigPass123!')

        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        self.dia5 = datetime.date(self.anio, self.mes, 5)
        self.dia15 = datetime.date(self.anio, self.mes, 15)
        self.dia20 = datetime.date(self.anio, self.mes, 20)
        self.mes_inicio = datetime.date(self.anio, self.mes, 1)

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.instalacion, nombre='P1')
        self.a = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111', tipo='FIJOS')
        self.b = Persona.objects.create(nombres='BETO', apellidos='DOS', cedula='0222222222', tipo='FIJOS')

        self.asig = Asignacion.objects.create(
            persona=self.a, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        # Un día pasado (día 5) con ANA marcada FALTÓ.
        self.rep5 = ReporteAsistencia.objects.create(
            asignacion=self.asig, persona=self.a, fecha_reporte=self.dia5,
            estado='TURNO', estado_asistencia='FALTO',
        )

    def _cambiar_a_beto(self):
        return self.client.put(
            f'/api/editar-servicio/{self.asig.id}/',
            data=json.dumps({'persona': self.b.id, 'fecha_cambio': self.dia15.isoformat()}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        )

    def test_periodos_se_crean_correctamente(self):
        resp = self._cambiar_a_beto()
        self.assertEqual(resp.status_code, 200)

        periodos = list(AsignacionPersonaPeriodo.objects.filter(asignacion=self.asig).order_by('desde'))
        self.assertEqual(len(periodos), 2)
        # ANA: desde inicio de mes hasta el día antes del cambio (día 14).
        self.assertEqual(periodos[0].persona_id, self.a.id)
        self.assertEqual(periodos[0].desde, self.mes_inicio)
        self.assertEqual(periodos[0].hasta, self.dia15 - datetime.timedelta(days=1))
        # BETO: desde el día del cambio, sin fin.
        self.assertEqual(periodos[1].persona_id, self.b.id)
        self.assertEqual(periodos[1].desde, self.dia15)
        self.assertIsNone(periodos[1].hasta)

    def test_dia_pasado_conserva_asistencia_de_ana(self):
        self._cambiar_a_beto()
        self.rep5.refresh_from_db()
        # El registro del día 5 NO se resetea: sigue ANA y FALTÓ.
        self.assertEqual(self.rep5.persona_id, self.a.id)
        self.assertEqual(self.rep5.estado_asistencia, 'FALTO')

    def test_reporte_resuelve_persona_por_fecha(self):
        self._cambiar_a_beto()

        # Día pasado (5) -> ANA UNO
        r5 = self.client.get(
            f'/api/reporte-asistencia/?fecha={self.dia5.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        ).json()
        fila5 = next((x for x in r5.get('results', []) if x.get('asignacion_id') == self.asig.id), None)
        self.assertIsNotNone(fila5, 'La asignación debe aparecer en el día 5')
        self.assertEqual(fila5['nombre_apellidos'], 'ANA UNO')

        # Día del cambio en adelante (20) -> BETO DOS
        r20 = self.client.get(
            f'/api/reporte-asistencia/?fecha={self.dia20.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        ).json()
        fila20 = next((x for x in r20.get('results', []) if x.get('asignacion_id') == self.asig.id), None)
        self.assertIsNotNone(fila20, 'La asignación debe aparecer en el día 20')
        self.assertEqual(fila20['nombre_apellidos'], 'BETO DOS')
