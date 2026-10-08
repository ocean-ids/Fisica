"""Servicios Adicionales: los ADICIONALES del Reporte de Guardia (que salen de la asistencia) en un rango de
fechas, con filtro de turno y búsqueda, y su Excel. Sin valores. Tiene su PROPIO permiso de solo lectura
(view_servicioadicional), independiente del Reporte de Guardia."""
import datetime
import io
import json

import openpyxl
from django.contrib.auth.models import Permission, User
from django.test import TestCase

from CoreFisica.models import ReporteGuardia

D = datetime.date


class ServiciosAdicionalesTests(TestCase):

    def setUp(self):
        User.objects.create_superuser(username='sa_user', email='e@e.com', password='SaPass123!x')
        self.auth = self._token('sa_user', 'SaPass123!x')
        crear = ReporteGuardia.objects.create
        crear(fecha=D(2026, 10, 1), turno='Diurno', seccion='ADICIONALES', cliente='CLIENTE A', puesto='GARITA 1',
              persona_nombre='JUAN PEREZ LOPEZ', proviene='FIJOS', auto=True)
        crear(fecha=D(2026, 10, 2), turno='Nocturno', seccion='ADICIONALES', cliente='CLIENTE B', puesto='RONDA',
              persona_nombre='ANA RUIZ MORA', proviene='EVENTUAL', auto=False)
        crear(fecha=D(2026, 10, 5), turno='Diurno', seccion='ADICIONALES', cliente='CLIENTE C', puesto='LOBBY',
              persona_nombre='LUIS SOTO VERA', proviene='RETEN', auto=True)
        # Otras secciones no salen.
        crear(fecha=D(2026, 10, 1), turno='Diurno', seccion='DOBLADAS', cliente='CLIENTE A', puesto='GARITA 1',
              persona_nombre='OTRO', valor=20)
        crear(fecha=D(2026, 10, 1), turno='Diurno', seccion='FALTOS', cliente='CLIENTE A', puesto='GARITA 1',
              persona_nombre='FALTO')

    def _token(self, username, password):
        tok = self.client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                               content_type='application/json').json().get('access')
        return {'HTTP_AUTHORIZATION': f'Bearer {tok}'}

    def _listar(self, **params):
        return self.client.get('/api/servicios-adicionales/', params, **self.auth)

    def test_solo_adicionales_del_rango(self):
        r = self._listar(desde='2026-10-01', hasta='2026-10-02')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([f['persona_nombre'] for f in r.json()], ['JUAN PEREZ LOPEZ', 'ANA RUIZ MORA'])
        f = r.json()[0]
        self.assertEqual(set(f), {'id', 'fecha', 'turno', 'cliente', 'puesto', 'persona_nombre', 'proviene'})

    def test_un_solo_dia(self):
        self.assertEqual(len(self._listar(fecha='2026-10-05').json()), 1)

    def test_filtro_de_turno_y_busqueda(self):
        self.assertEqual(len(self._listar(desde='2026-10-01', hasta='2026-10-31', turno='Nocturno').json()), 1)
        r = self._listar(desde='2026-10-01', hasta='2026-10-31', q='reten lobby')
        self.assertEqual([f['persona_nombre'] for f in r.json()], ['LUIS SOTO VERA'])

    def test_sin_fechas_o_rango_muy_largo(self):
        self.assertEqual(self._listar().status_code, 400)
        self.assertEqual(self._listar(desde='2025-01-01', hasta='2026-10-31').status_code, 400)

    def test_permiso_propio_de_solo_lectura(self):
        User.objects.create_user(username='sin_perm', password='SinPerm123!x')
        self.auth = self._token('sin_perm', 'SinPerm123!x')
        self.assertEqual(self._listar(fecha='2026-10-01').status_code, 403)
        u = User.objects.get(username='sin_perm')
        # El permiso del Reporte de Guardia ya no basta: el módulo tiene el suyo.
        u.user_permissions.add(Permission.objects.get(codename='view_reporteguardia'))
        self.assertEqual(self._listar(fecha='2026-10-01').status_code, 403)
        u.user_permissions.add(Permission.objects.get(codename='view_servicioadicional'))
        self.assertEqual(self._listar(fecha='2026-10-01').status_code, 200)
        self.assertEqual(self.client.get('/api/servicios-adicionales/exportar-excel/', {'fecha': '2026-10-01'},
                                         **self.auth).status_code, 200)

    def test_solo_existe_el_permiso_de_ver(self):
        self.assertEqual(sorted(Permission.objects.filter(content_type__model='servicioadicional')
                                .values_list('codename', flat=True)), ['view_servicioadicional'])

    def test_la_migracion_lo_da_a_quien_ve_el_reporte_de_guardia(self):
        import importlib
        from django.apps import apps
        from django.contrib.auth.models import Group
        mig = importlib.import_module('CoreFisica.migrations.0208_permiso_servicios_adicionales')
        guardia = Permission.objects.get(codename='view_reporteguardia')
        propio = Permission.objects.get(codename='view_servicioadicional')
        g = Group.objects.create(name='CONSOLA_TEST')
        g.permissions.add(guardia)
        u = User.objects.create_user(username='con_guardia', password='x')
        u.user_permissions.add(guardia)
        otro = User.objects.create_user(username='sin_guardia', password='x')
        mig.asignar(apps, None)
        self.assertIn(propio, g.permissions.all())
        self.assertIn(propio, u.user_permissions.all())
        self.assertNotIn(propio, otro.user_permissions.all())

    def test_excel_en_dos_pestanas_diurno_y_nocturno(self):
        r = self.client.get('/api/servicios-adicionales/exportar-excel/',
                            {'desde': '2026-10-01', 'hasta': '2026-10-31'}, **self.auth)
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertEqual(wb.sheetnames, ['DIURNO', 'NOCTURNO'])
        diurno = list(wb['DIURNO'].iter_rows(values_only=True))
        self.assertEqual(diurno[0], ('Nº', 'FECHA', 'CLIENTE', 'PUESTO', 'NOMBRES Y APELLIDOS', 'PROVIENE'))
        self.assertEqual(diurno[1], (1, '01/10/2026', 'CLIENTE A', 'GARITA 1', 'JUAN PEREZ LOPEZ', 'FIJOS'))
        self.assertEqual(len(diurno), 3)                   # cabecera + 2 diurnos
        nocturno = list(wb['NOCTURNO'].iter_rows(values_only=True))
        self.assertEqual(nocturno[1], (1, '02/10/2026', 'CLIENTE B', 'RONDA', 'ANA RUIZ MORA', 'EVENTUAL'))
        self.assertEqual(len(nocturno), 2)

    def test_excel_con_un_turno_solo_esa_pestana(self):
        r = self.client.get('/api/servicios-adicionales/exportar-excel/',
                            {'desde': '2026-10-01', 'hasta': '2026-10-31', 'turno': 'Nocturno'}, **self.auth)
        self.assertEqual(openpyxl.load_workbook(io.BytesIO(r.content)).sheetnames, ['NOCTURNO'])

    def test_sale_lo_que_viene_de_la_asistencia(self):
        """Un ADICIONAL marcado en la asistencia llega al Reporte de Guardia y de ahí a este módulo."""
        from unittest import mock
        from CoreFisica.models import Asignacion, Cliente, Instalacion, Persona, Puesto
        cli = Cliente.objects.create(razon_social='X SA', nombre_comercial='CLIENTE X')
        inst = Instalacion.objects.create(cliente=cli, nombre='INST X', codigo='X1')
        puesto = Puesto.objects.create(instalacion=inst, nombre='PUESTO X')
        titular = Persona.objects.create(nombres='TITU', apellidos='LAR', cedula='0910000801', tipo='FIJOS')
        rem = Persona.objects.create(nombres='PEDRO', apellidos='ADICIONAL', cedula='0910000802', tipo='FIJOS')
        asig = Asignacion.objects.create(persona=titular, cliente=cli, instalacion=inst, puesto=puesto, mes=10,
                                         anio=2026, estado='ACTIVO', recurring=True, start_date=D(2026, 10, 1))
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={asig.id: 'D'}):
            r = self.client.put(f'/api/reporte-asistencia/{asig.id}/', data=json.dumps(
                {'fecha': '2026-10-07', 'turno': 'Diurno', 'estado': 'ADICIONAL', 'estado_asistencia': 'ASISTIO',
                 'reemplazo_id': rem.id}), content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        filas = self._listar(fecha='2026-10-07').json()
        self.assertEqual(len(filas), 1)
        self.assertIn('PEDRO', filas[0]['persona_nombre'])
        self.assertEqual(filas[0]['turno'], 'Diurno')
