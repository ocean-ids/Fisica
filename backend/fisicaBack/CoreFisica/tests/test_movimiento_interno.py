"""Movimiento interno en el Reporte de Asistencia:

Para UN día se puede poner otro guardia (persona_cobertura) en un puesto, SOLO en el
reporte de ese día, sin tocar la Asignación. Si ese guardia es titular de otro puesto
ese mes, la fila se marca con `movimiento_interno=True` (para el badge)."""
import json
import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion,
    ReporteAsistencia, ReporteAsistenciaHistorial,
    SacafrancoFila, SacafrancoAsistencia,
)
from CoreFisica.views.reporte_asistencia_views import _build_reporte_asistencia_data


class MovimientoInternoTests(TestCase):
    def setUp(self):
        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        self.dia = datetime.date(self.anio, self.mes, 5)   # día pasado del mes en curso

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.inst_a = Instalacion.objects.create(cliente=self.cliente)
        self.inst_b = Instalacion.objects.create(cliente=self.cliente)
        self.puesto_a = Puesto.objects.create(instalacion=self.inst_a, nombre='PUESTO A')
        self.puesto_b = Puesto.objects.create(instalacion=self.inst_b, nombre='PUESTO B')

        self.juan = Persona.objects.create(nombres='JUAN', apellidos='TITULAR', cedula='0111111111', tipo='FIJOS')
        self.pedro = Persona.objects.create(nombres='PEDRO', apellidos='PEREZ', cedula='0222222222', tipo='FIJOS')
        self.libre = Persona.objects.create(nombres='LUIS', apellidos='LIBRE', cedula='0333333333', tipo='FIJOS')

        # Juan es titular del puesto A; Pedro es titular del puesto B (ese mes).
        self.asig_a = Asignacion.objects.create(
            persona=self.juan, cliente=self.cliente, instalacion=self.inst_a,
            puesto=self.puesto_a, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        self.asig_b = Asignacion.objects.create(
            persona=self.pedro, cliente=self.cliente, instalacion=self.inst_b,
            puesto=self.puesto_b, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )

    def _override_cobertura(self, persona):
        """Guarda para el día un override de asig_a con persona_cobertura = persona."""
        rep = ReporteAsistencia.objects.create(
            asignacion=self.asig_a, persona=self.juan, fecha_reporte=self.dia,
            estado='TURNO', estado_asistencia='ASISTIO', persona_cobertura=persona,
        )
        ReporteAsistenciaHistorial.objects.create(
            reporte=rep, asignacion=self.asig_a, fecha_reporte=self.dia,
            estado='TURNO', estado_asistencia='ASISTIO', persona_cobertura=persona,
        )

    def _fila_a(self):
        res = _build_reporte_asistencia_data(fecha=self.dia.isoformat(), turno=None)
        data = res[0] if isinstance(res, tuple) else res
        return next((r for r in data if r.get('asignacion_id') == self.asig_a.id), None)

    def test_guardia_de_otro_puesto_muestra_badge(self):
        # Pedro (titular del puesto B) cubre el puesto A ese día -> movimiento interno.
        self._override_cobertura(self.pedro)
        fila = self._fila_a()
        self.assertIsNotNone(fila)
        self.assertEqual(fila['nombre_apellidos'], 'PEREZ PEDRO')   # muestra al guardia del día
        self.assertTrue(fila['movimiento_interno'])                  # badge encendido

    def test_guardia_sacafranco_marca_badge(self):
        # Un SACAFRANCO (opera por su ficha, sin Asignacion) también cuenta como
        # movimiento interno al ponerlo como guardia del día.
        saca = Persona.objects.create(nombres='SARA', apellidos='SACA', cedula='0444444444', tipo='SACAFRANCO')
        self._override_cobertura(saca)
        fila = self._fila_a()
        self.assertIsNotNone(fila)
        self.assertEqual(fila['nombre_apellidos'], 'SACA SARA')
        self.assertTrue(fila['movimiento_interno'])

    def test_guardia_sin_puesto_no_marca_badge(self):
        # Luis no es titular de ningún puesto ese mes: se muestra su nombre, pero SIN badge.
        self._override_cobertura(self.libre)
        fila = self._fila_a()
        self.assertIsNotNone(fila)
        self.assertEqual(fila['nombre_apellidos'], 'LIBRE LUIS')
        self.assertFalse(fila['movimiento_interno'])

    def test_no_cambia_la_asignacion(self):
        # El movimiento interno es solo del reporte: la asignación sigue con Juan.
        self._override_cobertura(self.pedro)
        self._fila_a()
        self.asig_a.refresh_from_db()
        self.assertEqual(self.asig_a.persona_id, self.juan.id)

    def test_sin_cobertura_muestra_titular(self):
        # Sin persona_cobertura, la fila muestra al titular y sin badge.
        fila = self._fila_a()
        self.assertIsNotNone(fila)
        self.assertEqual(fila['nombre_apellidos'], 'TITULAR JUAN')
        self.assertFalse(fila['movimiento_interno'])

    def test_solo_afecta_ese_dia(self):
        # El movimiento interno del día 5 NO afecta al día 6: ese día vuelve el titular.
        self._override_cobertura(self.pedro)   # guardia del día SOLO para self.dia (día 5)

        # Día 5: sale Pedro (movimiento interno).
        f5 = self._fila_a()
        self.assertEqual(f5['nombre_apellidos'], 'PEREZ PEDRO')
        self.assertTrue(f5['movimiento_interno'])

        # Día 6: sin cobertura ese día -> vuelve el titular, sin badge.
        dia6 = datetime.date(self.anio, self.mes, 6)
        res = _build_reporte_asistencia_data(fecha=dia6.isoformat(), turno=None)
        data = res[0] if isinstance(res, tuple) else res
        f6 = next((r for r in data if r.get('asignacion_id') == self.asig_a.id), None)
        self.assertIsNotNone(f6)
        self.assertEqual(f6['nombre_apellidos'], 'TITULAR JUAN')
        self.assertFalse(f6['movimiento_interno'])

    def test_guardado_por_endpoint_persiste(self):
        # Reproduce el flujo del diálogo: PUT al endpoint con persona_cobertura_id.
        User.objects.create_superuser(username='mi_user', password='MiPass123!', email='m@e.com')
        resp = self.client.post('/api/login/',
                                data=json.dumps({'username': 'mi_user', 'password': 'MiPass123!'}),
                                content_type='application/json')
        access = resp.json().get('access')

        payload = {
            'estado': None,
            'estado_asistencia': 'ASISTIO',
            'reemplazo_id': None,
            'descripcion': None,
            'hueca': False,
            'hueca_motivo': None,
            'fecha': self.dia.isoformat(),
            'persona_cobertura_id': self.pedro.id,
        }
        r = self.client.put(f'/api/reporte-asistencia/{self.asig_a.id}/',
                            data=json.dumps(payload), content_type='application/json',
                            HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertIn(r.status_code, (200, 201))

        # La respuesta trae el nombre efectivo y el flag (para refrescar la tabla al instante).
        body = r.json()
        self.assertEqual(body.get('nombre_apellidos'), 'PEREZ PEDRO')
        self.assertTrue(body.get('movimiento_interno'))
        self.assertEqual(body.get('persona_cobertura_id'), self.pedro.id)

        # Se guardó en la BD (override + historial).
        ov = ReporteAsistencia.objects.get(asignacion=self.asig_a)
        self.assertEqual(ov.persona_cobertura_id, self.pedro.id)
        h = ReporteAsistenciaHistorial.objects.filter(
            asignacion=self.asig_a, fecha_reporte=self.dia).order_by('-creado_en').first()
        self.assertIsNotNone(h)
        self.assertEqual(h.persona_cobertura_id, self.pedro.id)

        # Y el reporte de ese día lo refleja (con badge).
        fila = self._fila_a()
        self.assertEqual(fila['nombre_apellidos'], 'PEREZ PEDRO')
        self.assertTrue(fila['movimiento_interno'])

    def test_sacafranco_guardado_por_endpoint_persiste(self):
        # Movimiento interno en una fila de SACAFRANCO: se guarda por su fila (no toca
        # la ficha del sacafranco) y la respuesta trae nombre efectivo + flag.
        User.objects.create_superuser(username='sf_user', password='SfPass123!', email='s@e.com')
        resp = self.client.post('/api/login/',
                                data=json.dumps({'username': 'sf_user', 'password': 'SfPass123!'}),
                                content_type='application/json')
        access = resp.json().get('access')

        titular_saca = Persona.objects.create(nombres='TITU', apellidos='SACA', cedula='0555555555', tipo='SACAFRANCO')
        fila = SacafrancoFila.objects.create(persona=titular_saca, mes=self.mes, anio=self.anio)

        payload = {
            'fecha': self.dia.isoformat(),
            'estado_asistencia': 'ASISTIO',
            'persona_cobertura_id': self.pedro.id,   # fijo de otro puesto cubre ese día
        }
        r = self.client.put(f'/api/reporte-asistencia/sacafranco/{fila.id}/',
                            data=json.dumps(payload), content_type='application/json',
                            HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertIn(r.status_code, (200, 201))
        body = r.json()
        self.assertEqual(body.get('nombre_apellidos'), 'PEREZ PEDRO')
        self.assertTrue(body.get('movimiento_interno'))

        sa = SacafrancoAsistencia.objects.get(sacafranco_fila=fila, fecha=self.dia)
        self.assertEqual(sa.persona_cobertura_id, self.pedro.id)
        # La ficha del sacafranco NO cambió (sigue su titular).
        fila.refresh_from_db()
        self.assertEqual(fila.persona_id, titular_saca.id)
