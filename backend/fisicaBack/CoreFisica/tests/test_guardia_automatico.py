"""Reporte de Guardia: se llena SOLO al guardar la asistencia.

- Guardar la asistencia (FALTO / reemplazo ADICIONAL...) crea las filas automáticas.
- Las ediciones a mano de una fila se conservan al volver a guardar.
- Una fila automática ELIMINADA a mano no reaparece al volver a guardar la asistencia.
- "Regenerar desde asistencia" (respaldo) sí vuelve a traer todo, incluso lo eliminado.
- Las filas manuales (auto=False) no se tocan.
"""
import datetime
import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from CoreFisica.models import (
    Asignacion, Cliente, Instalacion, Persona, Puesto, ReporteAsistencia,
    ReporteGuardia, ReporteGuardiaOculta,
)

FECHA = datetime.date(2026, 9, 29)


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class GuardiaAutomaticoTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='gd_user', email='e@e.com', password='GdPass123!')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'gd_user', 'GdPass123!')}"}
        cli = Cliente.objects.create(razon_social='CLI SA', nombre_comercial='CLI')
        inst = Instalacion.objects.create(cliente=cli, nombre='MATRIZ')
        puesto = Puesto.objects.create(instalacion=inst, nombre='GARITA')
        self.titular = Persona.objects.create(nombres='JUAN', apellidos='PEREZ', cedula='0911111118', tipo='FIJOS')
        self.reemplazo = Persona.objects.create(nombres='LUIS', apellidos='SOTO', cedula='0922222228', tipo='SACAFRANCO')
        self.asig = Asignacion.objects.create(persona=self.titular, cliente=cli, instalacion=inst, puesto=puesto,
                                              mes=9, anio=2026, estado='ACTIVO')
        # El turno sale del calendario D/N: se fija a Diurno para esa asignación.
        p = mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                       return_value={self.asig.id: 'D'})
        p.start()
        self.addCleanup(p.stop)

    def _guardar_asistencia(self, **data):
        body = {'fecha': FECHA.isoformat()}
        body.update(data)
        r = self.client.put(f'/api/reporte-asistencia/{self.asig.id}/', data=json.dumps(body),
                            content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)

    def _filas(self, **filtro):
        return ReporteGuardia.objects.filter(fecha=FECHA, **filtro)

    def test_guardar_falto_crea_la_fila_sola(self):
        self.assertEqual(self._filas().count(), 0)
        self._guardar_asistencia(estado_asistencia='FALTO')
        faltos = self._filas(seccion='FALTOS')
        self.assertEqual(faltos.count(), 1)
        self.assertTrue(faltos.first().auto)
        self.assertEqual(faltos.first().persona_ref_id, self.titular.id)

    def test_dejar_de_ser_falto_quita_la_fila(self):
        self._guardar_asistencia(estado_asistencia='FALTO')
        self._guardar_asistencia(estado_asistencia='ASISTIO')
        self.assertEqual(self._filas(seccion='FALTOS').count(), 0)

    def test_edicion_a_mano_se_conserva_al_guardar_otra_vez(self):
        self._guardar_asistencia(estado_asistencia='FALTO')
        fila = self._filas(seccion='FALTOS').get()
        r = self.client.put(f'/api/reporte-guardia/{fila.id}/', data=json.dumps({'motivo': 'ENFERMEDAD'}),
                            content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self._guardar_asistencia(estado_asistencia='FALTO')       # se guarda otra vez
        self.assertEqual(self._filas(seccion='FALTOS').get().motivo, 'ENFERMEDAD')

    def test_fila_eliminada_a_mano_no_reaparece(self):
        self._guardar_asistencia(estado_asistencia='FALTO')
        fila = self._filas(seccion='FALTOS').get()
        r = self.client.delete(f'/api/reporte-guardia/{fila.id}/eliminar/', **self.auth)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self._filas(seccion='FALTOS').count(), 0)
        self.assertEqual(ReporteGuardiaOculta.objects.count(), 1)
        # Se vuelve a guardar la asistencia del mismo día: la fila NO reaparece.
        self._guardar_asistencia(estado_asistencia='FALTO')
        self.assertEqual(self._filas(seccion='FALTOS').count(), 0)

    def test_regenerar_vuelve_a_traer_lo_eliminado(self):
        self._guardar_asistencia(estado_asistencia='FALTO')
        fila = self._filas(seccion='FALTOS').get()
        self.client.delete(f'/api/reporte-guardia/{fila.id}/eliminar/', **self.auth)
        r = self.client.post('/api/reporte-guardia/regenerar/', data=json.dumps({'fecha': FECHA.isoformat()}),
                             content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._filas(seccion='FALTOS').count(), 1)
        self.assertEqual(ReporteGuardiaOculta.objects.count(), 0)

    def test_marca_obsoleta_se_limpia_cuando_deja_de_ser_falto(self):
        self._guardar_asistencia(estado_asistencia='FALTO')
        fila = self._filas(seccion='FALTOS').get()
        self.client.delete(f'/api/reporte-guardia/{fila.id}/eliminar/', **self.auth)
        self._guardar_asistencia(estado_asistencia='ASISTIO')     # ya no hay falto
        self.assertEqual(ReporteGuardiaOculta.objects.count(), 0)
        self._guardar_asistencia(estado_asistencia='FALTO')       # falto otra vez: la fila vuelve
        self.assertEqual(self._filas(seccion='FALTOS').count(), 1)

    def test_filas_manuales_no_se_tocan(self):
        manual = ReporteGuardia.objects.create(fecha=FECHA, turno='Diurno', seccion='APOYO', cliente='CLI',
                                               puesto='GARITA', persona_nombre='ALGUIEN', auto=False)
        self._guardar_asistencia(estado_asistencia='FALTO')
        self.assertTrue(ReporteGuardia.objects.filter(id=manual.id).exists())
        # Eliminar una fila manual no deja marca (se borra del todo).
        self.client.delete(f'/api/reporte-guardia/{manual.id}/eliminar/', **self.auth)
        self.assertFalse(ReporteGuardia.objects.filter(id=manual.id).exists())
        self.assertEqual(ReporteGuardiaOculta.objects.count(), 0)

    def test_reemplazo_adicional_crea_adicionales(self):
        self._guardar_asistencia(estado='ADICIONAL', reemplazo_id=self.reemplazo.id)
        ad = self._filas(seccion='ADICIONALES')
        self.assertEqual(ad.count(), 1)
        self.assertEqual(ad.first().persona_ref_id, self.reemplazo.id)
