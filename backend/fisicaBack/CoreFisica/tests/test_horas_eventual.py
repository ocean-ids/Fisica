"""Módulo Eventuales: registro de horas trabajadas por EVENTUALES.

Se valida: catálogo (solo eventuales, con banco, tramos de tarifa), creación, banco vacío si la
persona no lo tiene, valor calculado con la tarifa "Eventuales" (horas + adicionales),
validaciones (solo EVENTUAL, instalación del cliente, puesto de la instalación, horas enteras)
y permisos.
"""
import json

from django.test import TestCase
from django.contrib.auth.models import User

from CoreFisica.models import (
    Persona, Cliente, Instalacion, Puesto, EmpleadoOtrosDatos, HorasEventual, TarifaPago,
)


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class HorasEventualTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='ev_admin', email='e@e.com', password='EvPass123!')
        self.token = _login(self.client, 'ev_admin', 'EvPass123!')
        self.cli = Cliente.objects.create(razon_social='CLI SA', nombre_comercial='CLI')
        self.otro_cli = Cliente.objects.create(razon_social='OTRO SA', nombre_comercial='OTRO')
        self.inst = Instalacion.objects.create(cliente=self.cli, nombre='MATRIZ')
        self.inst_otro = Instalacion.objects.create(cliente=self.otro_cli, nombre='SUCURSAL')
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='GARITA')
        self.puesto_otro = Puesto.objects.create(instalacion=self.inst_otro, nombre='PUERTA')
        self.ev = Persona.objects.create(nombres='JUAN', apellidos='PEREZ', cedula='0911111111', tipo='EVENTUAL')
        EmpleadoOtrosDatos.objects.update_or_create(persona=self.ev, defaults={'banco': 'BANCO PICHINCHA'})
        self.ev_sin_banco = Persona.objects.create(nombres='ANA', apellidos='LOPEZ', cedula='0922222222', tipo='EVENTUAL')
        self.fijo = Persona.objects.create(nombres='LUIS', apellidos='SOTO', cedula='0933333333', tipo='FIJOS')
        # Tarifa "Eventuales" por tramos (igual a Tarifas de Pago).
        for mn, mx, v in [(1, 3, '6.25'), (4, 6, '12.50'), (7, 9, '18.75'), (10, 12, '25.00'), (13, 15, '31.25')]:
            TarifaPago.objects.update_or_create(tipo_servicio='Eventuales', horas_min=mn, horas_max=mx,
                                                defaults={'valor': v})

    def _auth(self, token=None):
        return {'HTTP_AUTHORIZATION': f'Bearer {token or self.token}'}

    def _crear(self, **over):
        data = {
            'fecha': '2026-09-29', 'persona_id': self.ev.id, 'cliente_id': self.cli.id,
            'instalacion_id': self.inst.id, 'puesto_id': self.puesto.id, 'horas': 8,
        }
        data.update(over)
        return self.client.post('/api/horas-eventual/crear/', data=json.dumps(data),
                                content_type='application/json', **self._auth())

    def test_catalogo_solo_eventuales_con_banco(self):
        r = self.client.get('/api/horas-eventual/catalogo/', **self._auth())
        self.assertEqual(r.status_code, 200)
        evs = {e['id']: e for e in r.json()['eventuales']}
        self.assertIn(self.ev.id, evs)
        self.assertNotIn(self.fijo.id, evs)                       # un FIJO no sale
        self.assertEqual(evs[self.ev.id]['banco'], 'BANCO PICHINCHA')
        self.assertEqual(evs[self.ev_sin_banco.id]['banco'], '')  # sin banco -> vacío
        self.assertEqual(len(r.json()['tarifas']), 5)

    def test_crear_y_listar(self):
        r = self._crear(horas=7, horas_adicionales=2)   # 9 h -> tramo 7-9 = 18.75
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual(body['persona'], 'PEREZ JUAN')
        self.assertEqual(body['banco'], 'BANCO PICHINCHA')
        self.assertEqual(body['cliente'], 'CLI')
        self.assertEqual(body['instalacion'], 'MATRIZ')
        self.assertEqual(body['puesto'], 'GARITA')
        self.assertEqual(body['horas'], 7)
        self.assertEqual(body['horas_adicionales'], 2)
        self.assertEqual(body['valor_calculado'], 18.75)
        lista = self.client.get('/api/horas-eventual/?desde=2026-09-01&hasta=2026-09-30', **self._auth()).json()
        self.assertEqual(len(lista), 1)

    def test_eventual_sin_banco_sale_vacio(self):
        r = self._crear(persona_id=self.ev_sin_banco.id)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['banco'], '')

    def test_validaciones(self):
        self.assertEqual(self._crear(persona_id=self.fijo.id).status_code, 400)          # no es EVENTUAL
        self.assertEqual(self._crear(instalacion_id=self.inst_otro.id).status_code, 400)  # otro cliente
        self.assertEqual(self._crear(puesto_id=self.puesto_otro.id).status_code, 400)     # otra instalación
        self.assertEqual(self._crear(horas=0).status_code, 400)
        self.assertEqual(self._crear(horas=30).status_code, 400)
        self.assertEqual(self._crear(horas=7.5).status_code, 400)                   # no entero
        self.assertEqual(self._crear(horas_adicionales=-1).status_code, 400)
        self.assertEqual(self._crear(fecha='').status_code, 400)
        self.assertEqual(HorasEventual.objects.count(), 0)

    def test_editar_y_eliminar(self):
        hid = self._crear().json()['id']
        r = self.client.put(f'/api/horas-eventual/{hid}/', data=json.dumps({
            'fecha': '2026-09-28', 'persona_id': self.ev.id, 'cliente_id': self.cli.id,
            'instalacion_id': self.inst.id, 'puesto_id': None, 'horas': 12,
        }), content_type='application/json', **self._auth())
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['horas'], 12)
        self.assertEqual(r.json()['horas_adicionales'], 0)          # vacío -> 0
        self.assertEqual(r.json()['valor_calculado'], 25.0)         # 12 h -> tramo 10-12
        self.assertEqual(r.json()['puesto'], '')
        r2 = self.client.delete(f'/api/horas-eventual/{hid}/eliminar/', **self._auth())
        self.assertEqual(r2.status_code, 200)
        self.assertFalse(HorasEventual.objects.filter(id=hid).exists())

    def test_sin_tramo_valor_cero(self):
        r = self._crear(horas=16)   # no hay tramo para 16 h
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['valor_calculado'], 0.0)

    def test_sin_permiso(self):
        User.objects.create_user(username='sinperm', password='SinPass123!')
        tok = _login(self.client, 'sinperm', 'SinPass123!')
        self.assertEqual(self.client.get('/api/horas-eventual/', **self._auth(tok)).status_code, 403)
        self.assertEqual(self.client.get('/api/horas-eventual/catalogo/', **self._auth(tok)).status_code, 403)
