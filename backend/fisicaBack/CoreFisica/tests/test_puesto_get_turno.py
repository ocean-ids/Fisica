"""Puesto.get_turno(): da el mismo turno que antes y, si los horarios ya vienen cargados (prefetch), no consulta
la base de datos otra vez por cada puesto."""
import datetime

from django.test import TestCase

from CoreFisica.models import Cliente, Instalacion, Puesto, PuestoHorario

T = datetime.time


class PuestoGetTurnoTests(TestCase):

    def setUp(self):
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        self.inst = Instalacion.objects.create(cliente=cli, nombre='I')

    def _puesto(self, *turnos):
        p = Puesto.objects.create(instalacion=self.inst, nombre=f'P{Puesto.objects.count()}')
        for i, t in enumerate(turnos):
            PuestoHorario.objects.create(puesto=p, dia=i + 1, turno=t, hora_ingreso=T(7, 0), hora_salida=T(19, 0))
        return p

    def test_los_resultados_de_siempre(self):
        casos = [
            ((), None),
            (('Diurno', 'Diurno'), 'Diurno'),
            (('Nocturno',), 'Nocturno'),
            ((' diurno ',), 'Diurno'),           # mayúsculas y espacios no importan
            (('Ambos',), 'Ambos'),
            (('Diurno', 'Nocturno'), 'Mixto'),
            (('', 'Nocturno'), 'Nocturno'),      # un horario sin turno no cuenta
        ]
        for turnos, esperado in casos:
            p = self._puesto(*turnos)
            self.assertEqual(Puesto.objects.get(id=p.id).get_turno(), esperado, turnos)

    def test_24h_se_muestra_como_24h(self):
        p = self._puesto('Ambos')
        self.assertEqual(Puesto.objects.get(id=p.id).get_turno_display(), '24H')

    def test_con_horarios_cargados_no_hace_consultas_por_puesto(self):
        for _ in range(5):
            self._puesto('Diurno', 'Diurno')
        puestos = list(Puesto.objects.prefetch_related('horarios'))
        with self.assertNumQueries(0):
            for p in puestos:
                p.get_turno()
                p.get_turno_display()
