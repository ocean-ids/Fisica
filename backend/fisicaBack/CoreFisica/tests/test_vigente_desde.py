"""Historial por día (fecha de alta del puesto):

Una asignación con `vigente_desde` NO debe aparecer en la reportería de asistencia en
fechas ANTERIORES a su alta, pero SÍ desde esa fecha en adelante. Una asignación sin
`vigente_desde` (NULL) se comporta como antes: visible todo el mes (sin corte)."""
import json
import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion, AsignacionPersonaPeriodo,
)


def _login_token(client, username, password):
    resp = client.post(
        '/api/login/',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json',
    )
    return resp.json().get('access')


class VigenteDesdeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='vd_user', password='VdPass123!', email='vd@example.com'
        )
        self.access = _login_token(self.client, 'vd_user', 'VdPass123!')

        hoy = timezone.localdate()
        # Mes en curso (fechas pasadas respecto a hoy para caer en la rama de fecha pasada).
        self.mes, self.anio = hoy.month, hoy.year
        self.dia5 = datetime.date(self.anio, self.mes, 5)    # ANTES del alta
        self.dia15 = datetime.date(self.anio, self.mes, 15)  # fecha de alta
        self.dia20 = datetime.date(self.anio, self.mes, 20)  # DESPUÉS del alta

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.instalacion, nombre='P1')
        self.a = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111', tipo='FIJOS')

        # Puesto creado a mitad de mes: alta el día 15.
        self.asig = Asignacion.objects.create(
            persona=self.a, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
            vigente_desde=self.dia15,
        )

    def _reporte(self, fecha):
        return self.client.get(
            f'/api/reporte-asistencia/?fecha={fecha.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        ).json()

    def _fila(self, data):
        return next((x for x in data.get('results', []) if x.get('asignacion_id') == self.asig.id), None)

    def test_no_aparece_antes_del_alta(self):
        # Día 5 (antes del alta del 15): la asignación NO debe salir.
        self.assertIsNone(self._fila(self._reporte(self.dia5)))

    def test_aparece_desde_el_alta_en_adelante(self):
        # Día 20 (después del alta del 15): la asignación SÍ debe salir.
        self.assertIsNotNone(self._fila(self._reporte(self.dia20)))

    def test_sin_vigente_desde_aparece_todo_el_mes(self):
        # Sin fecha de alta (NULL) = comportamiento anterior: visible incluso el día 5.
        self.asig.vigente_desde = None
        self.asig.save(update_fields=['vigente_desde'])
        self.assertIsNotNone(self._fila(self._reporte(self.dia5)))


class GrillaAsignacionesPorDiaTests(TestCase):
    """La grilla de Asignaciones (/asignaciones/<mes>/<anio>/) con ?dia= muestra el estado
    histórico de ese día: oculta puestos no creados aún y resuelve persona/hueca por período.
    Sin ?dia= la grilla se comporta igual que antes (estado actual)."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='gd_user', password='GdPass123!', email='gd@example.com'
        )
        self.access = _login_token(self.client, 'gd_user', 'GdPass123!')

        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        self.mes_inicio = datetime.date(self.anio, self.mes, 1)
        self.dia5 = datetime.date(self.anio, self.mes, 5)
        self.dia15 = datetime.date(self.anio, self.mes, 15)
        self.dia20 = datetime.date(self.anio, self.mes, 20)

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.instalacion, nombre='P1')
        self.a = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111',
                                        tipo='FIJOS', estado_empleado='ACTIVO')

        # Estado ACTUAL: el puesto es HUECA (persona=None) desde el día 15.
        self.asig = Asignacion.objects.create(
            persona=None, cliente=self.cliente, instalacion=self.instalacion,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
            es_hueca=True,
        )
        # Historial de períodos: ANA del 1 al 14; HUECA (None) del 15 en adelante.
        AsignacionPersonaPeriodo.objects.create(
            asignacion=self.asig, persona=self.a, desde=self.mes_inicio,
            hasta=self.dia15 - datetime.timedelta(days=1),
        )
        AsignacionPersonaPeriodo.objects.create(
            asignacion=self.asig, persona=None, desde=self.dia15, hasta=None,
        )

    def _grid(self, dia=None):
        url = f'/api/asignaciones/{self.mes}/{self.anio}/?lite=true'
        if dia:
            url += f'&dia={dia.isoformat()}'
        return self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.access}').json()

    def _results(self, data):
        return data.get('results', []) if isinstance(data, dict) else data

    def _fila(self, data):
        return next((x for x in self._results(data) if x.get('id') == self.asig.id), None)

    def test_dia_antes_del_cambio_muestra_a_ana(self):
        fila = self._fila(self._grid(self.dia5))
        self.assertIsNotNone(fila)
        self.assertIsNotNone(fila.get('persona_detalle'))
        self.assertEqual(fila['persona_detalle']['apellidos'], 'UNO')
        self.assertFalse(fila['es_hueca'])

    def test_dia_del_cambio_en_adelante_es_hueca(self):
        fila = self._fila(self._grid(self.dia20))
        self.assertIsNotNone(fila)
        self.assertIsNone(fila.get('persona_detalle'))
        self.assertTrue(fila['es_hueca'])

    def test_sin_dia_muestra_estado_actual(self):
        # Sin ?dia: estado actual (HUECA, sin persona), igual que antes.
        fila = self._fila(self._grid())
        self.assertIsNotNone(fila)
        self.assertIsNone(fila.get('persona_detalle'))
        self.assertTrue(fila['es_hueca'])

    def test_puesto_nuevo_no_aparece_antes_de_su_alta(self):
        # Un puesto creado a mitad de mes (vigente_desde=15) no sale en el día 5.
        puesto2 = Puesto.objects.create(instalacion=self.instalacion, nombre='P2')
        nuevo = Asignacion.objects.create(
            persona=self.a, cliente=self.cliente, instalacion=self.instalacion,
            puesto=puesto2, mes=self.mes, anio=self.anio, estado='ACTIVO',
            vigente_desde=self.dia15,
        )
        ids5 = [x.get('id') for x in self._results(self._grid(self.dia5))]
        ids20 = [x.get('id') for x in self._results(self._grid(self.dia20))]
        self.assertNotIn(nuevo.id, ids5)
        self.assertIn(nuevo.id, ids20)
