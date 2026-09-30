"""Sacavacaciones cuando el fijo CAMBIÓ de puesto después de registrar sus vacaciones.

Bug: el reemplazo se buscaba por (puesto del registro de vacaciones, persona). Si luego al fijo
lo movían a otro puesto (ej. de RONDA a LOBBY), el reporte ya no lo reconocía y seguía
mostrando al fijo en vez de su sacavacaciones. Las vacaciones son de la PERSONA: el
sacavacaciones debe salir en el puesto que el fijo tenga ese día."""
import datetime
from django.test import TestCase
from django.utils import timezone

from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion, ReporteVacaciones,
)
from CoreFisica.views.reporte_asistencia_views import _build_reporte_asistencia_data


class SacavacacionesCambioPuestoTests(TestCase):
    def setUp(self):
        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        self.dia = datetime.date(self.anio, self.mes, 10)

        cli = Cliente.objects.create(razon_social='RIVERFRONT SA', nombre_comercial='RIVERFRONT 2')
        inst = Instalacion.objects.create(cliente=cli, nombre='RIVERFRONT 2 MATRIZ')
        self.ronda = Puesto.objects.create(instalacion=inst, nombre='RONDA')
        self.lobby = Puesto.objects.create(instalacion=inst, nombre='LOBBY')
        self.franco = Persona.objects.create(nombres='JACINTO ALBERTO', apellidos='FRANCO VILLEGAS',
                                             cedula='0910000001', tipo='FIJOS')
        self.gladys = Persona.objects.create(nombres='GLADYS MARIA', apellidos='TOMALA CASSAGNE',
                                             cedula='0910000002', tipo='SACAVACACIONES')

        # Hoy Franco está en LOBBY (así sale en el reporte)...
        self.asig_lobby = Asignacion.objects.create(
            persona=self.franco, cliente=cli, instalacion=inst, puesto=self.lobby,
            mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        # ...pero sus vacaciones se registraron cuando estaba en RONDA (otra asignación).
        mes_ant = 12 if self.mes == 1 else self.mes - 1
        anio_ant = self.anio - 1 if self.mes == 1 else self.anio
        self.asig_ronda = Asignacion.objects.create(
            persona=self.franco, cliente=cli, instalacion=inst, puesto=self.ronda,
            mes=mes_ant, anio=anio_ant, estado='ACTIVO',
        )
        ReporteVacaciones.objects.create(
            cliente='RIVERFRONT 2', asignacion=self.asig_ronda,
            persona_sale='JACINTO ALBERTO FRANCO VILLEGAS', persona_sale_ref=self.franco,
            sacavacaciones='GLADYS MARIA TOMALA CASSAGNE', sacavacaciones_ref=self.gladys,
            fecha_desde=self.dia - datetime.timedelta(days=3),
            fecha_hasta=self.dia + datetime.timedelta(days=3), dias=7,
        )

    def _fila_lobby(self, fecha):
        res = _build_reporte_asistencia_data(fecha=fecha.isoformat(), turno=None)
        data = res[0] if isinstance(res, tuple) else res
        return next((r for r in data if r.get('asignacion_id') == self.asig_lobby.id), None)

    def test_sale_el_sacavacaciones_aunque_cambio_de_puesto(self):
        fila = self._fila_lobby(self.dia)
        self.assertIsNotNone(fila)
        self.assertEqual(fila['nombre_apellidos'], 'TOMALA CASSAGNE GLADYS MARIA')

    def test_fuera_de_las_vacaciones_sale_el_fijo(self):
        fila = self._fila_lobby(self.dia + datetime.timedelta(days=5))
        self.assertIsNotNone(fila)
        self.assertEqual(fila['nombre_apellidos'], 'FRANCO VILLEGAS JACINTO ALBERTO')
