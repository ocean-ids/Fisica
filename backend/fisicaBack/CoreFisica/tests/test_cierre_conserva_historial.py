"""Al CERRAR un puesto (la asignación queda estado='INACTIVO'), el historial del
reporte de asistencia de los días PASADOS que ya tenían datos NO debe desaparecer.
Un día pasado SIN datos, en cambio, no reaparece para un puesto cerrado."""
import json
import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion,
    ReporteAsistencia, ReporteAsistenciaHistorial,
)


def _login_token(client, username, password):
    resp = client.post(
        '/api/login/',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json',
    )
    return resp.json().get('access')


class CierreConservaHistorialTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='cierre_user', password='CierrePass123!', email='cierre@example.com'
        )
        self.access = _login_token(self.client, 'cierre_user', 'CierrePass123!')

        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        # Dos días pasados del mes en curso: uno CON datos, otro SIN datos.
        self.dia_con = datetime.date(self.anio, self.mes, 5)
        self.dia_sin = datetime.date(self.anio, self.mes, 6)

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.instalacion, nombre='P1')
        self.persona = Persona.objects.create(
            nombres='ANA', apellidos='UNO', cedula='0111111111', tipo='FIJOS'
        )
        self.asig = Asignacion.objects.create(
            persona=self.persona, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        # Día pasado CON datos: ASISTIÓ (override + historial, como lo hace el guardado real).
        self.rep = ReporteAsistencia.objects.create(
            asignacion=self.asig, persona=self.persona, fecha_reporte=self.dia_con,
            estado='TURNO', estado_asistencia='ASISTIO',
        )
        ReporteAsistenciaHistorial.objects.create(
            reporte=self.rep, asignacion=self.asig, fecha_reporte=self.dia_con,
            estado='TURNO', estado_asistencia='ASISTIO',
        )

    def _fila(self, fecha):
        resp = self.client.get(
            f'/api/reporte-asistencia/?fecha={fecha.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json().get('results', [])
        return next((x for x in data if x.get('asignacion_id') == self.asig.id), None)

    def _cerrar(self):
        # Simula el cierre que deja la asignación INACTIVO (p. ej. cierre de instalación).
        Asignacion.objects.filter(id=self.asig.id).update(estado='INACTIVO')

    def test_dia_con_datos_se_ve_antes_del_cierre(self):
        fila = self._fila(self.dia_con)
        self.assertIsNotNone(fila, 'El día con datos debe verse antes de cerrar')
        self.assertEqual(fila['estado_asistencia'], 'ASISTIO')

    def test_dia_con_datos_se_conserva_tras_cierre(self):
        self._cerrar()
        fila = self._fila(self.dia_con)
        self.assertIsNotNone(fila, 'El historial del día pasado NO debe desaparecer al cerrar')
        self.assertEqual(fila['nombre_apellidos'], 'UNO ANA')
        self.assertEqual(fila['estado_asistencia'], 'ASISTIO')

    def test_dia_sin_datos_no_reaparece_tras_cierre(self):
        # Antes de cerrar, el puesto activo se ve (aunque sin marca).
        self.assertIsNotNone(self._fila(self.dia_sin), 'Activo: el día sin datos se ve')
        self._cerrar()
        # Cerrado y sin datos ese día: no debe salir (no hay historial que preservar).
        self.assertIsNone(
            self._fila(self.dia_sin),
            'Un puesto cerrado no debe reaparecer en días sin datos guardados',
        )
