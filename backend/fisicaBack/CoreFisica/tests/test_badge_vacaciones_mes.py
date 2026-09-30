"""Badge de Vacaciones en Asignaciones: se muestra en el MES de las vacaciones aunque ya
hayan pasado (sirve de referencia); en otro mes no sale."""
import datetime
import json

from django.contrib.auth.models import User
from django.test import TestCase

from CoreFisica.models import Asignacion, Cliente, Instalacion, Persona, Puesto, ReporteVacaciones


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class BadgeVacacionesMesTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='vac_user', email='e@e.com', password='VacPass123!')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'vac_user', 'VacPass123!')}"}
        cli = Cliente.objects.create(razon_social='CLI SA', nombre_comercial='CLI')
        inst = Instalacion.objects.create(cliente=cli, nombre='MATRIZ')
        puesto = Puesto.objects.create(instalacion=inst, nombre='GARITA')
        self.fijo = Persona.objects.create(nombres='JUAN', apellidos='PEREZ', cedula='0911111119', tipo='FIJOS')
        for mes in (1, 3):
            Asignacion.objects.create(persona=self.fijo, cliente=cli, instalacion=inst, puesto=puesto,
                                      mes=mes, anio=2026, estado='ACTIVO')
        # Vacaciones que ya pasaron (enero 2026).
        ReporteVacaciones.objects.create(persona_sale='JUAN PEREZ', persona_sale_ref=self.fijo,
                                         fecha_desde=datetime.date(2026, 1, 5),
                                         fecha_hasta=datetime.date(2026, 1, 15), dias=11)

    def _vacaciones(self, mes):
        r = self.client.get(f'/api/asignaciones/{mes}/2026/', **self.auth)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        filas = data if isinstance(data, list) else (data.get('results') or data.get('asignaciones') or [])
        fila = next(f for f in filas if f.get('persona') == self.fijo.id
                    or (f.get('persona_detalle') or {}).get('id') == self.fijo.id)
        return fila.get('vacaciones')

    def test_sale_en_su_mes_aunque_ya_pasaron(self):
        v = self._vacaciones(1)
        self.assertIsNotNone(v)
        self.assertEqual((v['desde'], v['hasta']), ('2026-01-05', '2026-01-15'))

    def test_no_sale_en_otro_mes(self):
        self.assertIsNone(self._vacaciones(3))
