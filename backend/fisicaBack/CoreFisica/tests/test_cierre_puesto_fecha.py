"""Cierre de puesto / instalación con corte al día: sale HASTA EL DÍA DEL CIERRE INCLUIDO, desde el día siguiente
ya no, y no se proyecta a los meses siguientes (ni al generar el mes siguiente). Los días anteriores al cierre
siguen saliendo aunque no tengan asistencia marcada."""
import datetime
import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from CoreFisica.models import Asignacion, Cliente, Instalacion, Persona, Puesto

D = datetime.date


class CierrePuestoFechaTests(TestCase):

    def setUp(self):
        User.objects.create_superuser(username='cp_user', email='e@e.com', password='CpPass123!x')
        tok = self.client.post('/api/login/', data=json.dumps({'username': 'cp_user', 'password': 'CpPass123!x'}),
                               content_type='application/json').json().get('access')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {tok}'}
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        self.inst = Instalacion.objects.create(cliente=cli, nombre='I', codigo='Z9')
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='P')
        self.persona = Persona.objects.create(nombres='ANA', apellidos='PEREZ', cedula='0910009999', tipo='FIJOS')
        self.asig = Asignacion.objects.create(persona=self.persona, cliente=cli, instalacion=self.inst,
                                              puesto=self.puesto, mes=9, anio=2026, estado='ACTIVO', recurring=True,
                                              start_date=D(2026, 9, 1), end_date=None)
        self.vacante = Asignacion.objects.create(persona=None, cliente=cli, instalacion=self.inst,
                                                 puesto=self.puesto, mes=9, anio=2026, estado='ACTIVO',
                                                 recurring=True, start_date=D(2026, 9, 1), end_date=None)

    def _sale(self, fecha):
        """Filas del puesto que salen ese día en el Reporte de Asistencia (Diurno)."""
        ids = list(Asignacion.objects.filter(puesto=self.puesto).values_list('id', flat=True))
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={i: 'D' for i in ids}):
            d = self.client.get('/api/reporte-asistencia/', {'fecha': fecha.isoformat(), 'turno': 'Diurno'},
                                **self.auth).json()
        return len([f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('asignacion_id') in ids])

    def _cerrar_puesto(self, fecha):
        from CoreFisica.views.novedad_puesto_views import _aplicar_estado_puesto
        _aplicar_estado_puesto(self.puesto, 'CIERRE', fecha)

    def test_cierre_de_puesto_sale_hasta_el_dia_del_cierre_incluido(self):
        self._cerrar_puesto(D(2026, 9, 15))
        self.assertEqual(self._sale(D(2026, 9, 10)), 2)     # persona + vacante
        self.assertEqual(self._sale(D(2026, 9, 15)), 2)     # el día del cierre todavía sale
        self.assertEqual(self._sale(D(2026, 9, 16)), 0)
        self.assertEqual(self._sale(D(2026, 9, 30)), 0)

    def test_cierre_el_dia_1_sale_solo_ese_dia(self):
        self._cerrar_puesto(D(2026, 9, 1))
        self.assertEqual(self._sale(D(2026, 9, 1)), 2)
        self.assertEqual(self._sale(D(2026, 9, 2)), 0)

    def test_el_mes_siguiente_no_proyecta_el_puesto_cerrado(self):
        from CoreFisica.asignaciones_meses import alinear_meses
        self._cerrar_puesto(D(2026, 9, 15))
        alinear_meses(9, 2026, 1, crear_meses=True)
        self.assertFalse(Asignacion.objects.filter(puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO').exists())
        self.assertEqual(self._sale(D(2026, 10, 5)), 0)

    def test_filas_futuras_ya_creadas_quedan_inactivas(self):
        from CoreFisica.asignaciones_meses import alinear_meses
        alinear_meses(9, 2026, 1, crear_meses=True)          # octubre ya existía antes del cierre
        self.assertTrue(Asignacion.objects.filter(puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO').exists())
        self._cerrar_puesto(D(2026, 9, 15))
        self.assertFalse(Asignacion.objects.filter(puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO').exists())
        alinear_meses(9, 2026, 1, crear_meses=True)          # volver a generar no lo revive
        self.assertFalse(Asignacion.objects.filter(puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO').exists())
        self.assertEqual(self._sale(D(2026, 10, 5)), 0)

    def test_un_puesto_abierto_se_sigue_proyectando(self):
        from CoreFisica.asignaciones_meses import alinear_meses
        alinear_meses(9, 2026, 1, crear_meses=True)
        self.assertTrue(Asignacion.objects.filter(puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO',
                                                  persona=self.persona).exists())

    def test_cerrar_instalacion_conserva_los_dias_anteriores(self):
        r = self.client.post(f'/api/cerrar-instalacion/{self.inst.id}/', data=json.dumps({'fecha': '2026-09-15'}),
                             content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._sale(D(2026, 9, 10)), 2)     # sin asistencia marcada, igual sale
        self.assertEqual(self._sale(D(2026, 9, 15)), 2)
        self.assertEqual(self._sale(D(2026, 9, 16)), 0)
        self.puesto.refresh_from_db()
        self.inst.refresh_from_db()
        self.assertFalse(self.puesto.activo)
        self.assertFalse(self.inst.activo)

    def test_cerrar_instalacion_sin_fecha_cierra_hoy(self):
        from django.utils import timezone
        hoy = timezone.localdate()
        Asignacion.objects.filter(id__in=[self.asig.id, self.vacante.id]).update(
            mes=hoy.month, anio=hoy.year, start_date=hoy.replace(day=1))
        r = self.client.post(f'/api/cerrar-instalacion/{self.inst.id}/', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self.asig.refresh_from_db()
        self.assertEqual(self.asig.end_date, hoy)
        self.assertEqual(self.asig.estado, 'ACTIVO')

    def test_reabrir_despues_del_cierre_deja_una_vacante_desde_la_apertura(self):
        from CoreFisica.asignaciones_meses import alinear_meses
        from CoreFisica.views.novedad_puesto_views import _aplicar_estado_puesto
        alinear_meses(9, 2026, 1, crear_meses=True)
        self._cerrar_puesto(D(2026, 9, 15))
        _aplicar_estado_puesto(self.puesto, 'APERTURA', D(2026, 10, 10))
        self.puesto.refresh_from_db()
        self.assertTrue(self.puesto.activo)
        vac = Asignacion.objects.filter(puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO', persona__isnull=True)
        self.assertEqual(vac.count(), 1)
        self.assertEqual(vac.first().start_date, D(2026, 10, 10))
        self.assertEqual(self._sale(D(2026, 10, 5)), 0)
        self.assertEqual(self._sale(D(2026, 10, 12)), 1)

    def test_reabrir_conserva_los_dias_antes_del_cierre(self):
        from CoreFisica.views.novedad_puesto_views import _aplicar_estado_puesto
        self._cerrar_puesto(D(2026, 9, 15))
        _aplicar_estado_puesto(self.puesto, 'APERTURA', D(2026, 10, 10))
        self.assertEqual(self._sale(D(2026, 9, 10)), 2)     # persona + vacante, como antes del cierre
        self.assertEqual(self._sale(D(2026, 9, 20)), 0)

    def test_cerrar_y_reabrir_en_el_mismo_mes(self):
        from CoreFisica.views.novedad_puesto_views import _aplicar_estado_puesto
        self._cerrar_puesto(D(2026, 9, 15))
        _aplicar_estado_puesto(self.puesto, 'APERTURA', D(2026, 9, 20))
        self.assertEqual(self._sale(D(2026, 9, 10)), 2)     # antes del cierre: persona + vacante
        self.assertEqual(self._sale(D(2026, 9, 17)), 0)     # cerrado
        self.assertEqual(self._sale(D(2026, 9, 22)), 1)     # reabierto: vacante nueva


class LimpiarPuestosCerradosTests(CierrePuestoFechaTests):
    """Comando limpiar_puestos_cerrados: corrige los puestos que se cerraron ANTES de la corrección (seguían
    saliendo como vacante y proyectándose a los meses siguientes)."""

    def _como_quedaba_antes(self):
        """Cierre viejo el 15/09: persona hasta el 14, vacante sin corte y octubre con filas ACTIVAS."""
        from CoreFisica.asignaciones_meses import alinear_meses
        from CoreFisica.models import NovedadPuesto
        alinear_meses(9, 2026, 1, crear_meses=True)
        NovedadPuesto.objects.create(puesto=self.puesto, instalacion=self.inst, fecha=D(2026, 9, 15), novedad='CIERRE')
        Puesto.objects.filter(id=self.puesto.id).update(activo=False)
        Asignacion.objects.filter(id=self.asig.id).update(end_date=D(2026, 9, 14))
        Asignacion.objects.filter(puesto=self.puesto, mes=10).update(persona=None)

    def _correr(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('limpiar_puestos_cerrados', *args, stdout=out)
        return out.getvalue()

    def test_antes_seguia_saliendo(self):
        self._como_quedaba_antes()
        self.assertEqual(self._sale(D(2026, 9, 20)), 1)      # la vacante seguía saliendo después del cierre
        self.assertEqual(self._sale(D(2026, 10, 5)), 2)      # y se proyectaba a octubre

    def test_la_prueba_no_guarda_nada(self):
        self._como_quedaba_antes()
        salida = self._correr('--dry-run', '--detalle')
        self.assertIn('no se guardó nada', salida)
        self.assertIn('1 puestos corregidos', salida)
        self.assertEqual(self._sale(D(2026, 10, 5)), 2)

    def test_corrige_el_cierre_viejo(self):
        self._como_quedaba_antes()
        salida = self._correr()
        self.assertIn('2 filas de meses futuros desactivadas', salida)
        self.assertEqual(self._sale(D(2026, 9, 10)), 2)      # antes del cierre: igual que siempre
        self.assertEqual(self._sale(D(2026, 9, 15)), 1)      # el día del cierre: la vacante (la persona ya cortaba el 14)
        self.assertEqual(self._sale(D(2026, 9, 20)), 0)
        self.assertEqual(self._sale(D(2026, 10, 5)), 0)
        self.assertIn('0 puestos corregidos', self._correr())  # repetirlo no cambia nada

    def test_puesto_cerrado_sin_novedad_corta_hoy(self):
        from django.utils import timezone
        hoy = timezone.localdate()
        Asignacion.objects.filter(id__in=[self.asig.id, self.vacante.id]).update(
            mes=hoy.month, anio=hoy.year, start_date=hoy.replace(day=1))
        Puesto.objects.filter(id=self.puesto.id).update(activo=False)
        self._correr()
        self.asig.refresh_from_db()
        self.assertEqual((self.asig.estado, self.asig.end_date), ('ACTIVO', hoy))

    def test_no_toca_puestos_abiertos(self):
        self._correr()
        self.asig.refresh_from_db()
        self.assertIsNone(self.asig.end_date)
