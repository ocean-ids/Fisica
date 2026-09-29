"""El Excel del Reporte de Asistencia trae una pestaña DIURNO y otra NOCTURNO POR CADA DÍA
del mes, del día 1 hasta el día SELECCIONADO (sin días futuros)."""
import io
import json

from django.test import TestCase
from django.contrib.auth.models import User
from openpyxl import load_workbook


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class ExcelPestanasPorDiaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='xls_user', email='e@e.com', password='XlsPass123!'
        )
        self.access = _login(self.client, 'xls_user', 'XlsPass123!')

    def test_una_pestana_por_dia_hasta_el_seleccionado(self):
        # Día seleccionado = 3 -> hojas DIURNO/NOCTURNO de los días 1, 2 y 3 (6 hojas).
        r = self.client.get(
            '/api/reporte-asistencia/exportar-excel/?fecha=2026-09-03',
            HTTP_AUTHORIZATION=f'Bearer {self.access}'
        )
        self.assertEqual(r.status_code, 200)
        wb = load_workbook(io.BytesIO(r.content))
        nombres = wb.sheetnames

        # Deben estar las 6 hojas esperadas.
        for d in (1, 2, 3):
            self.assertIn(f'DIURNO {d}', nombres)
            self.assertIn(f'NOCTURNO {d}', nombres)
        self.assertEqual(len(nombres), 6)

        # NO deben existir días futuros del mes.
        self.assertNotIn('DIURNO 4', nombres)
        self.assertNotIn('NOCTURNO 4', nombres)

    def test_primer_dia_solo_dos_pestanas(self):
        r = self.client.get(
            '/api/reporte-asistencia/exportar-excel/?fecha=2026-09-01',
            HTTP_AUTHORIZATION=f'Bearer {self.access}'
        )
        self.assertEqual(r.status_code, 200)
        wb = load_workbook(io.BytesIO(r.content))
        self.assertEqual(wb.sheetnames, ['DIURNO 1', 'NOCTURNO 1'])
