"""Servicios Adicionales (formato FR-REPORTE DE PUESTO ADICIONAL): crear desde la asistencia o a mano, editar,
lista por rango de fechas, Excel por día con Diurno y Nocturno, y permisos (el PRECIO solo con su permiso)."""
import datetime
import importlib
import io
import json

import openpyxl
from django.apps import apps
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

from CoreFisica.models import Asignacion, Cliente, Instalacion, Persona, Puesto

D = datetime.date


class ServiciosAdicionalesTests(TestCase):

    def setUp(self):
        User.objects.create_superuser(username='sa_admin', email='e@e.com', password='SaPass123!x')
        self.cli = Cliente.objects.create(razon_social='PECHICHAL SA', nombre_comercial='PECHICHAL')
        self.inst = Instalacion.objects.create(cliente=self.cli, nombre='COMPAÑIA AGRICOLA PECHICHAL', codigo='G15')
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='GARITA')
        titular = Persona.objects.create(nombres='TITU', apellidos='LAR', cedula='0910000801', tipo='FIJOS')
        self.asig = Asignacion.objects.create(persona=titular, cliente=self.cli, instalacion=self.inst,
                                              puesto=self.puesto, mes=10, anio=2026, estado='ACTIVO',
                                              recurring=True, start_date=D(2026, 10, 1))
        self.auth = self._token('sa_admin', 'SaPass123!x')

    def _token(self, username, password):
        tok = self.client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                               content_type='application/json').json().get('access')
        return {'HTTP_AUTHORIZATION': f'Bearer {tok}'}

    def _usuario(self, *codenames):
        u = User.objects.create_user(username='consola', password='Consola123!x')
        for c in codenames:
            u.user_permissions.add(Permission.objects.get(codename=c))
        self.auth = self._token('consola', 'Consola123!x')
        return u

    def _crear(self, **datos):
        base = {'fecha': '2026-10-07', 'turno': 'Diurno', 'instalacion_id': self.inst.id, 'cantidad': 1,
                'horas': 12, 'hora_ingreso': '07:00', 'hora_salida': '19:00', 'solicitado_por': 'gilda arevalo',
                'recibido_por': 'rosa jimenez', 'medio': 'correo'}
        base.update(datos)
        return self.client.post('/api/servicios-adicionales/crear/', data=json.dumps(base),
                                content_type='application/json', **self.auth)

    def _lista(self, **params):
        return self.client.get('/api/servicios-adicionales/', params, **self.auth)

    def test_crear_y_listar(self):
        r = self._crear()
        self.assertEqual(r.status_code, 201, r.content)
        f = self._lista(fecha='2026-10-07').json()[0]
        self.assertEqual((f['cliente_texto'], f['cliente'], f['cantidad'], f['horas'], f['horario']),
                         ('COMPAÑIA AGRICOLA PECHICHAL', 'PECHICHAL', 1, 12.0, '07:00 - 19:00'))
        self.assertEqual((f['solicitado_por'], f['recibido_por'], f['medio']),
                         ('GILDA AREVALO', 'ROSA JIMENEZ', 'CORREO'))

    def test_validaciones(self):
        self.assertEqual(self._crear(instalacion_id=None).status_code, 400)          # sin cliente
        self.assertEqual(self._crear(cantidad=0).status_code, 400)
        self.assertEqual(self._crear(hora_ingreso='7h').status_code, 400)
        self.assertEqual(self._crear(turno='Tarde').status_code, 400)

    def test_prellenar_desde_la_asistencia_y_no_duplicar(self):
        prellenar = lambda: self.client.get('/api/servicios-adicionales/prellenar/', {
            'fecha': '2026-10-07', 'turno': 'Diurno', 'asignacion_id': self.asig.id}, **self.auth).json()
        r = prellenar()
        self.assertFalse(r['existe'])
        self.assertEqual((r['registro']['cliente_id'], r['registro']['instalacion_id']), (self.cli.id, self.inst.id))
        self.assertEqual(self._crear(asignacion_id=self.asig.id).status_code, 201)
        self.assertEqual(self._crear(asignacion_id=self.asig.id).status_code, 409)    # misma fila, fecha y turno
        self.assertEqual(self._crear(asignacion_id=self.asig.id, turno='Nocturno').status_code, 201)
        self.assertTrue(prellenar()['existe'])

    def test_consola_crea_y_edita_pero_no_pone_precio(self):
        self._usuario('view_servicioadicional', 'add_servicioadicional', 'change_servicioadicional')
        r = self._crear(precio=50)
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.json()['precio'])                                         # el precio se ignora
        sid = r.json()['id']
        r = self.client.put(f'/api/servicios-adicionales/{sid}/', data=json.dumps({'cantidad': 2, 'precio': 80}),
                            content_type='application/json', **self.auth)
        self.assertEqual((r.status_code, r.json()['cantidad'], r.json()['precio']), (200, 2, None))

    def test_solo_el_permiso_de_precio_pone_el_precio(self):
        sid = self._crear().json()['id']
        self._usuario('view_servicioadicional', 'editar_precio_servicioadicional')
        r = self.client.put(f'/api/servicios-adicionales/{sid}/', data=json.dumps({'precio': '45.50', 'cantidad': 9}),
                            content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()['precio'], r.json()['cantidad']), (45.5, 1))      # sin editar: solo el precio

    def test_sin_permisos(self):
        self._usuario()
        self.assertEqual(self._lista(fecha='2026-10-07').status_code, 403)
        self.assertEqual(self._crear().status_code, 403)

    def test_solo_ver_no_crea(self):
        self._usuario('view_servicioadicional')
        self.assertEqual(self._lista(fecha='2026-10-07').status_code, 200)
        self.assertEqual(self._crear().status_code, 403)

    def test_rango_turno_y_busqueda(self):
        self._crear(fecha='2026-10-01')
        self._crear(fecha='2026-10-02', turno='Nocturno', solicitado_por='pablo chavez')
        self._crear(fecha='2026-11-01')
        self.assertEqual(len(self._lista(desde='2026-10-01', hasta='2026-10-31').json()), 2)
        self.assertEqual(len(self._lista(desde='2026-10-01', hasta='2026-10-31', turno='Nocturno').json()), 1)
        self.assertEqual(len(self._lista(desde='2026-10-01', hasta='2026-10-31', q='chavez').json()), 1)
        self.assertEqual(self._lista().status_code, 400)

    def test_excel_formato_fr_por_dia(self):
        self._crear(fecha='2026-10-07', precio=30)
        self._crear(fecha='2026-10-07', turno='Nocturno', hora_ingreso='19:00', hora_salida='07:00')
        self._crear(fecha='2026-10-08', cantidad=2)
        r = self.client.get('/api/servicios-adicionales/exportar-excel/',
                            {'desde': '2026-10-07', 'hasta': '2026-10-09'}, **self.auth)
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertEqual(wb.sheetnames, ['07-10-2026', '08-10-2026'])              # un día por pestaña
        valores = [c for fila in wb['07-10-2026'].iter_rows(values_only=True) for c in fila if c not in (None, '')]
        for esperado in ('FR-REPORTE DE PUESTO ADICIONAL', 'TURNO DIURNO', 'TURNO NOCTURNO', 'CLIENTE', 'C', 'H',
                         'HORARIO', 'SOLICITADO POR', 'RECIBIDO POR', 'MEDIO', 'PRECIO', 'ELABORA:', 'REVISA:',
                         'AUTORIZA:', 'Miércoles, 7 de octubre de 2026', '07:00 - 19:00', '19:00 - 07:00', 30):
            self.assertIn(esperado, valores)

    def test_excel_sin_registros_trae_la_hoja_vacia(self):
        r = self.client.get('/api/servicios-adicionales/exportar-excel/', {'fecha': '2026-10-20'}, **self.auth)
        self.assertEqual(openpyxl.load_workbook(io.BytesIO(r.content)).sheetnames, ['20-10-2026'])

    def test_la_migracion_da_crear_y_editar_a_consola_y_no_el_precio(self):
        mig = importlib.import_module('CoreFisica.migrations.0209_servicio_adicional_formulario')
        g = Group.objects.create(name='CONSOLA_TEST')
        g.permissions.add(Permission.objects.get(codename='change_reporteasistencia'))
        mig.asignar(apps, None)
        cods = set(g.permissions.filter(content_type__model='servicioadicional').values_list('codename', flat=True))
        self.assertEqual(cods, {'view_servicioadicional', 'add_servicioadicional', 'change_servicioadicional'})
