"""Módulo Eventuales: registro de horas trabajadas por EVENTUALES.

Reglas:
- Horas adicionales = horas trabajadas - horas solicitadas (mínimo 0), calculadas al guardar.
- Rango (tramo) de la tarifa: según las HORAS TRABAJADAS.
- Valor calculado: por defecto tarifa "Eventuales" de ese tramo + bonificación; si se envía un
  valor (corregido a mano), se guarda ese.
- Bonificación opcional. Banco de solo lectura (vacío si la persona no lo tiene).
Además: validaciones, historial y permisos.
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
        EmpleadoOtrosDatos.objects.update_or_create(persona=self.ev, defaults={'banco': 'Banco Pichincha'})
        self.ev_sin_banco = Persona.objects.create(nombres='ANA', apellidos='LOPEZ', cedula='0922222222', tipo='EVENTUAL')
        self.fijo = Persona.objects.create(nombres='LUIS', apellidos='SOTO', cedula='0933333333', tipo='FIJOS')
        # Tarifa "Eventuales" por tramos (igual a Tarifas de Pago).
        for mn, mx, v in [(1, 3, '6.25'), (4, 6, '12.50'), (7, 9, '18.75'), (10, 12, '25.00'), (13, 15, '31.25')]:
            TarifaPago.objects.update_or_create(tipo_servicio='Eventuales', horas_min=mn, horas_max=mx,
                                                defaults={'valor': v})

    def _auth(self, token=None):
        return {'HTTP_AUTHORIZATION': f'Bearer {token or self.token}'}

    def _datos(self, **over):
        data = {
            'fecha': '2026-09-29', 'persona_id': self.ev.id, 'cliente_id': self.cli.id,
            'instalacion_id': self.inst.id, 'puesto_id': self.puesto.id,
            'horas_solicitadas': 4, 'horas': 8,
        }
        data.update(over)
        return data

    def _crear(self, **over):
        return self.client.post('/api/horas-eventual/crear/', data=json.dumps(self._datos(**over)),
                                content_type='application/json', **self._auth())

    def _editar(self, hid, **over):
        return self.client.put(f'/api/horas-eventual/{hid}/', data=json.dumps(self._datos(**over)),
                               content_type='application/json', **self._auth())

    def test_catalogo_solo_eventuales_con_banco_y_tarifas(self):
        r = self.client.get('/api/horas-eventual/catalogo/', **self._auth())
        self.assertEqual(r.status_code, 200)
        evs = {e['id']: e for e in r.json()['eventuales']}
        self.assertIn(self.ev.id, evs)
        self.assertNotIn(self.fijo.id, evs)                       # un FIJO no sale
        self.assertEqual(evs[self.ev.id]['banco'], 'PICHINCHA')
        self.assertEqual(evs[self.ev.id]['banco_codigo'], '10')
        self.assertEqual(evs[self.ev.id]['tipo'], 'EVENTUAL')
        self.assertEqual(evs[self.ev_sin_banco.id]['banco'], '')  # sin banco -> vacío
        self.assertEqual(len(r.json()['tarifas']), 5)

    def test_adicionales_y_valor_con_bonificacion(self):
        # trabajadas 12 -> tramo 10-12 = 25.00; + bono 5 = 30.00 (adicionales = 12 - 8 = 4)
        r = self._crear(horas_solicitadas=8, horas=12, bonificacion='5')
        self.assertEqual(r.status_code, 201, r.content)
        b = r.json()
        self.assertEqual(b['horas_solicitadas'], 8)
        self.assertEqual(b['horas'], 12)
        self.assertEqual(b['horas_adicionales'], 4)      # vacío -> trabajadas - solicitadas
        self.assertEqual(b['bonificacion'], 5.0)
        self.assertEqual(b['rango_horas'], '10-12 h')
        self.assertEqual(b['valor_calculado'], 30.0)     # por defecto: rango + bono
        self.assertEqual(b['persona'], 'PEREZ JUAN')
        self.assertEqual(b['banco'], 'PICHINCHA')
        lista = self.client.get('/api/horas-eventual/?desde=2026-09-29&hasta=2026-09-29', **self._auth()).json()
        self.assertEqual(len(lista), 1)

    def test_horas_adicionales_escritas(self):
        b = self._crear(horas_solicitadas=8, horas=12, horas_adicionales=6).json()
        self.assertEqual(b['horas_adicionales'], 6)      # se guarda lo escrito
        self.assertEqual(b['valor_calculado'], 25.0)     # el valor sigue siendo el del rango (12 h)
        self.assertEqual(self._crear(horas_adicionales=30).status_code, 400)
        self.assertEqual(self._crear(horas_adicionales=-1).status_code, 400)

    def test_valor_corregido_a_mano(self):
        b = self._crear(horas_solicitadas=8, horas=12, bonificacion='5',
                        valor_calculado='20,40', valor_manual=True).json()
        self.assertEqual(b['valor_calculado'], 20.4)     # se guarda lo escrito
        self.assertTrue(b['valor_manual'])
        self.assertEqual(self._crear(valor_calculado='-1', valor_manual=True).status_code, 400)
        self.assertEqual(self._crear(valor_calculado='abc', valor_manual=True).status_code, 400)

    def test_valor_no_manual_se_calcula_solo(self):
        # Sin valor_manual, aunque venga un valor, se usa rango + bonificación (12 h -> 25 + 5).
        b = self._crear(horas=12, bonificacion='5', valor_calculado='0').json()
        self.assertFalse(b['valor_manual'])
        self.assertEqual(b['valor_calculado'], 30.0)

    def test_sin_bonificacion_solo_tarifa(self):
        b = self._crear(horas_solicitadas=4, horas=12).json()   # 12 trabajadas -> 25.00
        self.assertEqual(b['horas_adicionales'], 8)
        self.assertIsNone(b['bonificacion'])
        self.assertEqual(b['valor_calculado'], 25.0)

    def test_trabajo_menos_de_lo_solicitado(self):
        # 8 trabajadas -> tramo 7-9 = 18.75; + bono 3 = 21.75. Adicionales no negativo.
        b = self._crear(horas_solicitadas=10, horas=8, bonificacion='3').json()
        self.assertEqual(b['horas_adicionales'], 0)
        self.assertEqual(b['valor_calculado'], 21.75)

    def test_rango_por_horas_trabajadas(self):
        # 11 trabajadas -> tramo 10-12 = 25.00
        b = self._crear(horas_solicitadas=11, horas=11).json()
        self.assertEqual(b['rango_horas'], '10-12 h')
        self.assertEqual(b['valor_calculado'], 25.0)
        # 8 trabajadas -> tramo 7-9 = 18.75 (las solicitadas no cambian el rango)
        b2 = self._crear(horas_solicitadas=12, horas=8).json()
        self.assertEqual(b2['rango_horas'], '7-9 h')
        self.assertEqual(b2['valor_calculado'], 18.75)

    def test_rango_elegido_a_mano(self):
        t = TarifaPago.objects.get(tipo_servicio='Eventuales', horas_min=13, horas_max=15)
        b = self._crear(horas_solicitadas=11, horas=11, tarifa_id=t.id, bonificacion='1').json()
        self.assertEqual(b['rango_horas'], '13-15 h')          # el elegido, no el de la regla
        self.assertEqual(b['valor_calculado'], 32.25)          # 31.25 + 1
        self.assertEqual(self._crear(tarifa_id=999999).status_code, 400)

    def test_sin_tramo_rango_vacio(self):
        b = self._crear(horas_solicitadas=0, horas=20).json()
        self.assertEqual(b['rango_horas'], '')

    def test_sin_tramo(self):
        b = self._crear(horas_solicitadas=0, horas=20).json()   # 20 h adicionales: no hay tramo
        self.assertEqual(b['horas_adicionales'], 20)
        self.assertEqual(b['valor_calculado'], 0.0)

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
        self.assertEqual(self._crear(horas_solicitadas='').status_code, 400)        # obligatorias
        self.assertEqual(self._crear(horas_solicitadas=-1).status_code, 400)
        self.assertEqual(self._crear(bonificacion='-5').status_code, 400)           # no negativa
        self.assertEqual(self._crear(bonificacion='abc').status_code, 400)
        self.assertEqual(self._crear(fecha='').status_code, 400)
        self.assertEqual(HorasEventual.objects.count(), 0)

    def test_editar_y_eliminar(self):
        hid = self._crear().json()['id']
        r = self._editar(hid, horas_solicitadas=2, horas=12, puesto_id=None, puesto_texto='PUERTA 5',
                         bonificacion='2,50')
        self.assertEqual(r.status_code, 200, r.content)
        b = r.json()
        self.assertEqual(b['horas_adicionales'], 10)
        self.assertEqual(b['bonificacion'], 2.5)              # acepta coma decimal
        self.assertEqual(b['valor_calculado'], 27.5)          # 25.00 (10-12) + 2.50
        self.assertEqual(b['puesto'], 'PUERTA 5')
        r2 = self.client.delete(f'/api/horas-eventual/{hid}/eliminar/', **self._auth())
        self.assertEqual(r2.status_code, 200)
        self.assertFalse(HorasEventual.objects.filter(id=hid).exists())

    def test_historial_quien_creo_y_modifico(self):
        admin = User.objects.get(username='ev_admin')
        admin.first_name, admin.last_name = 'Bryan', 'Cabello'
        admin.save()
        hid = self._crear(horas_solicitadas=4, horas=8).json()['id']          # 4 adic -> 12.50
        body = self._editar(hid, horas_solicitadas=4, horas=12).json()          # 8 adic -> 18.75
        self.assertEqual(body['creado_por'], 'Bryan Cabello')
        self.assertEqual(body['modificado_por'], 'Bryan Cabello')
        self.assertTrue(body['modificado_en'])
        hist = self.client.get(f'/api/horas-eventual/{hid}/historial/', **self._auth()).json()
        self.assertEqual([h['accion'] for h in hist], ['MODIFICADO', 'CREADO'])
        self.assertEqual(hist[0]['usuario'], 'Bryan Cabello')
        self.assertEqual(set(hist[0]['cambios']),
                         {'Horas trabajadas', 'Horas adicionales', 'Rango de horas', 'Valor calculado'})
        self.assertEqual(hist[1]['cambios'], [])
        self.assertEqual(hist[1]['horas'], 8)

    def test_cliente_instalacion_puesto_escritos_a_mano(self):
        n_clientes = Cliente.objects.count()
        r = self._crear(cliente_id=None, instalacion_id=None, puesto_id=None,
                        cliente_texto='CLIENTE NUEVO', instalacion_texto='BODEGA NORTE',
                        puesto_texto='PUERTA 2')
        self.assertEqual(r.status_code, 201, r.content)
        b = r.json()
        self.assertEqual(b['cliente'], 'CLIENTE NUEVO')
        self.assertEqual(b['instalacion'], 'BODEGA NORTE')
        self.assertEqual(b['puesto'], 'PUERTA 2')
        self.assertTrue(b['cliente_libre'] and b['instalacion_libre'] and b['puesto_libre'])
        self.assertIsNone(b['cliente_id'])
        self.assertEqual(Cliente.objects.count(), n_clientes)       # NO se crea el cliente
        # Cliente de la lista + instalación escrita a mano también vale.
        r2 = self._crear(instalacion_id=None, puesto_id=None, instalacion_texto='SEDE TEMPORAL',
                         puesto_texto='GARITA 1')
        self.assertEqual(r2.status_code, 201, r2.content)
        self.assertEqual(r2.json()['cliente'], 'CLI')
        self.assertEqual(r2.json()['instalacion'], 'SEDE TEMPORAL')

    def test_texto_libre_validaciones(self):
        # Sin cliente (ni de la lista ni escrito) -> 400; lo mismo la instalación.
        self.assertEqual(self._crear(cliente_id=None, cliente_texto='  ').status_code, 400)
        self.assertEqual(self._crear(instalacion_id=None, instalacion_texto='').status_code, 400)
        # Cliente escrito + instalación de la lista -> no corresponde.
        self.assertEqual(self._crear(cliente_id=None, cliente_texto='X').status_code, 400)
        # Puesto obligatorio: ni de la lista ni escrito -> 400.
        self.assertEqual(self._crear(puesto_id=None, puesto_texto='').status_code, 400)

    def test_sin_permiso(self):
        User.objects.create_user(username='sinperm', password='SinPass123!')
        tok = _login(self.client, 'sinperm', 'SinPass123!')
        self.assertEqual(self.client.get('/api/horas-eventual/', **self._auth(tok)).status_code, 403)
        self.assertEqual(self.client.get('/api/horas-eventual/catalogo/', **self._auth(tok)).status_code, 403)
        self.assertEqual(self.client.get('/api/horas-eventual/1/historial/', **self._auth(tok)).status_code, 403)
        self.assertEqual(self.client.get('/api/horas-eventual/exportar-excel/', **self._auth(tok)).status_code, 403)

    def test_exportar_excel_datos_bancarios_del_dia(self):
        import io as _io
        from openpyxl import load_workbook
        od = self.ev.otros_datos
        od.tipo_cuenta, od.numero_cuenta = 'AHORROS', '0037794584'
        od.save()
        self._crear(horas_solicitadas=8, horas=12)                  # JUAN PEREZ
        fila = self.client.get('/api/horas-eventual/?desde=2026-09-29&hasta=2026-09-29', **self._auth()).json()[0]
        self.assertEqual((fila['banco_codigo'], fila['tipo_cuenta'], fila['numero_cuenta'], fila['banco']),
                         ('10', 'AHORROS', '0037794584', 'PICHINCHA'))
        self._crear(horas=4)                                        # JUAN otra vez: una sola fila
        self._crear(persona_id=self.ev_sin_banco.id, horas=8)       # ANA LOPEZ, sin banco
        self._crear(fecha='2026-09-30', horas=8)                    # otro día: no sale
        r = self.client.get('/api/horas-eventual/exportar-excel/?fecha=2026-09-29', **self._auth())
        self.assertEqual(r.status_code, 200)
        self.assertIn('EVENTUALES 29-09-2026.xlsx', r['Content-Disposition'])
        ws = load_workbook(_io.BytesIO(r.content)).active
        self.assertEqual([c.value for c in ws[1]], ['NOMBRE', 'CUENTA', 'BANCO', 'TIPO', 'CEDULA', 'VALOR'])
        self.assertEqual(ws.max_row, 3)             # encabezado + 2 personas (sin fila de totales)
        # Ordenados por nombre: LOPEZ ANA antes que PEREZ JUAN.
        ana = [c.value for c in ws[2]]
        self.assertEqual(ana[:5], ['LOPEZ ANA', None, None, None, '0922222222'])   # sin datos bancarios
        juan = [c.value for c in ws[3]]
        self.assertEqual(juan[:5], ['PEREZ JUAN', '0037794584', 'PICHINCHA', 'AHORROS', '0911111111'])
        # Sumarizado del día de JUAN: 12 trabajadas (tramo 10-12 = 25.00) + 4 trabajadas (4-6 = 12.50)
        self.assertEqual(juan[5], 25.0 + 12.5)
        # Con búsqueda: solo quien coincide.
        r = self.client.get('/api/horas-eventual/exportar-excel/?fecha=2026-09-29&q=lopez', **self._auth())
        ws = load_workbook(_io.BytesIO(r.content)).active
        self.assertEqual(ws.max_row, 2)             # encabezado + LOPEZ ANA
        self.assertEqual(ws.cell(2, 1).value, 'LOPEZ ANA')

    def test_rango_de_fechas_lista_y_excel(self):
        for dia in ('2026-09-21', '2026-09-22', '2026-09-25', '2026-09-29', '2026-09-30'):
            self._crear(fecha=dia, horas=8)
        lista = self.client.get('/api/horas-eventual/?desde=2026-09-22&hasta=2026-09-29', **self._auth()).json()
        self.assertEqual(sorted(f['fecha'] for f in lista), ['2026-09-22', '2026-09-25', '2026-09-29'])
        r = self.client.get('/api/horas-eventual/exportar-excel/?desde=2026-09-22&hasta=2026-09-29', **self._auth())
        self.assertEqual(r.status_code, 200)
        self.assertIn('EVENTUALES 22-09-2026 AL 29-09-2026.xlsx', r['Content-Disposition'])

    def test_excel_rango_suma_por_persona(self):
        import io as _io
        from openpyxl import load_workbook
        # JUAN trabaja 3 días del rango y 1 fuera; ANA 1 día.
        self._crear(fecha='2026-09-22', horas_solicitadas=8, horas=8)                       # 18.75
        self._crear(fecha='2026-09-25', horas_solicitadas=8, horas=12, bonificacion='5')   # 25.00 + 5
        self._crear(fecha='2026-09-29', horas_solicitadas=4, horas=4)                       # 12.50
        self._crear(fecha='2026-09-21', horas_solicitadas=8, horas=8)                       # fuera
        self._crear(persona_id=self.ev_sin_banco.id, fecha='2026-09-23', horas=8)
        r = self.client.get('/api/horas-eventual/exportar-excel/?desde=2026-09-22&hasta=2026-09-29', **self._auth())
        ws = load_workbook(_io.BytesIO(r.content)).active
        self.assertEqual(ws.max_row, 3)             # encabezado + 2 personas (sin fila de totales)
        juan = next([c.value for c in ws[i]] for i in (2, 3) if ws.cell(i, 1).value == 'PEREZ JUAN')
        self.assertEqual(juan[5], 18.75 + 30.0 + 12.5)               # valor sumado del rango (incluye el bono)
        self.assertEqual(len(juan), 6)

    # ---------- Turno (Diurno / Nocturno) ----------
    def test_turno_por_defecto_diurno_y_se_guarda_nocturno(self):
        self.assertEqual(self._crear().json()['turno'], 'Diurno')
        self.assertEqual(self._crear(turno='nocturno').json()['turno'], 'Nocturno')
        self.assertEqual(self._crear(turno='cualquiera').json()['turno'], 'Diurno')   # inválido: Diurno

    def test_listado_y_excel_filtran_por_turno_y_sin_turno_es_ambos(self):
        import io as _io
        from openpyxl import load_workbook
        self._crear(turno='Diurno')                                          # JUAN, diurno
        self._crear(persona_id=self.ev_sin_banco.id, turno='Nocturno')       # ANA, nocturno
        base = '/api/horas-eventual/?desde=2026-09-29&hasta=2026-09-29'
        self.assertEqual(len(self.client.get(base, **self._auth()).json()), 2)           # ambos
        self.assertEqual([f['persona'] for f in self.client.get(base + '&turno=Nocturno', **self._auth()).json()],
                         ['LOPEZ ANA'])
        self.assertEqual([f['persona'] for f in self.client.get(base + '&turno=Diurno', **self._auth()).json()],
                         ['PEREZ JUAN'])
        ex = '/api/horas-eventual/exportar-excel/?fecha=2026-09-29'
        self.assertEqual(load_workbook(_io.BytesIO(self.client.get(ex, **self._auth()).content)).active.max_row, 3)
        r = self.client.get(ex + '&turno=Nocturno', **self._auth())
        self.assertEqual(load_workbook(_io.BytesIO(r.content)).active.max_row, 2)        # encabezado + ANA

    def test_editar_cambia_el_turno(self):
        rid = self._crear().json()['id']
        r = self.client.put(f'/api/horas-eventual/{rid}/', data=json.dumps(self._datos(turno='Nocturno')),
                            content_type='application/json', **self._auth())
        self.assertEqual(r.json()['turno'], 'Nocturno')

    # ---------- Eliminar persona ----------
    def test_eliminar_eventual_con_horas_explica_el_motivo(self):
        self._crear()                                                   # JUAN PEREZ ya tiene horas
        r = self.client.delete(f'/api/eliminar-persona/{self.ev.id}/', **self._auth())
        self.assertEqual(r.status_code, 409, r.content)
        self.assertIn('registros asociados', r.json()['error'])
        self.assertTrue(Persona.objects.filter(id=self.ev.id).exists())   # no se borró nada

    def test_eliminar_persona_sin_registros_funciona(self):
        r = self.client.delete(f'/api/eliminar-persona/{self.ev_sin_banco.id}/', **self._auth())
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(Persona.objects.filter(id=self.ev_sin_banco.id).exists())
