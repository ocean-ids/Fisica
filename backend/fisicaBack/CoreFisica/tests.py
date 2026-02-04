from django.test import TestCase
from datetime import date

from .models import Cliente, Instalacion, Puesto, AsignacionSemanal


class SemanasTests(TestCase):
    def test_semanas_mes_valido(self):
        url = '/api/semanas/?mes=2&anio=2026'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('weeks', data)
        self.assertTrue(isinstance(data['weeks'], list))


class AsignacionSemanalPaginationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC', direccion='D')
        self.instalacion = Instalacion.objects.create(cliente=self.cliente, provincia='P', ciudad='C')
        # crear varios puestos
        self.puestos = [Puesto.objects.create(instalacion=self.instalacion, nombre=f'P{i}') for i in range(5)]

    def test_paginacion_asignacion_semanal(self):
        ws = date(2026, 2, 2)
        # crear 5 filas, una por puesto
        for p in self.puestos:
            AsignacionSemanal.objects.create(puesto=p, week_start=ws, mon='')

        url = f'/api/asignacion-semanal/?week_start={ws.isoformat()}&page_size=2'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # estructura paginada de DRF: count, next, previous, results
        self.assertIn('count', data)
        self.assertEqual(data['count'], 5)
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)
        self.assertIsNotNone(data.get('next'))

        # solicitar la tercera página
        resp3 = self.client.get(url + '&page=3')
        self.assertEqual(resp3.status_code, 200)
        d3 = resp3.json()
        self.assertEqual(len(d3['results']), 1)