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

    def test_pdf_formato_fr_una_pagina_por_dia(self):
        self._crear(fecha='2026-10-07', precio=30)
        self._crear(fecha='2026-10-08', turno='Nocturno')
        r = self.client.get('/api/servicios-adicionales/exportar-pdf/', {'desde': '2026-10-07', 'hasta': '2026-10-09'},
                            **self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        import re
        self.assertEqual(len(re.findall(rb'/Type\s*/Page[^s]', r.content)), 2)     # 2 días con registros

    def test_pdf_sin_permiso(self):
        self._usuario()
        self.assertEqual(self.client.get('/api/servicios-adicionales/exportar-pdf/', {'fecha': '2026-10-07'},
                                         **self.auth).status_code, 403)


class AdicionalDesdeLaAsistenciaTests(ServiciosAdicionalesTests):
    """Guardar la asistencia como ADICIONAL crea el servicio adicional INCOMPLETO (aunque no llenen el formulario);
    si deja de ser ADICIONAL y nadie lo completó, se quita. Y el comando pasa los adicionales que ya existían."""

    def setUp(self):
        super().setUp()
        from CoreFisica.models import PuestoHorario
        PuestoHorario.objects.create(puesto=self.puesto, dia=D(2026, 10, 7).weekday() + 1, turno='Diurno',
                                     hora_ingreso=datetime.time(7), hora_salida=datetime.time(19))
        self.rem = Persona.objects.create(nombres='PEDRO', apellidos='ADIC', cedula='0910000802', tipo='FIJOS')

    def _guardar(self, **datos):
        from unittest import mock
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={self.asig.id: 'D'}):
            r = self.client.put(f'/api/reporte-asistencia/{self.asig.id}/', data=json.dumps(
                {'fecha': '2026-10-07', 'turno': 'Diurno', **datos}), content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)

    def _registros(self):
        from CoreFisica.models import ServicioAdicional
        return list(ServicioAdicional.objects.filter(asignacion=self.asig, fecha=D(2026, 10, 7)))

    def test_guardar_como_adicional_lo_crea_incompleto(self):
        self._guardar(estado='ADICIONAL', estado_asistencia='ASISTIO', reemplazo_id=self.rem.id)
        regs = self._registros()
        self.assertEqual(len(regs), 1)
        sa = regs[0]
        self.assertEqual((sa.turno, sa.instalacion_id, sa.cantidad, sa.horas), ('Diurno', self.inst.id, 1, 12))
        self.assertEqual((sa.hora_ingreso, sa.hora_salida), (datetime.time(7), datetime.time(19)))
        self.assertEqual((sa.solicitado_por, sa.recibido_por, sa.medio, sa.precio), ('', '', '', None))
        self._guardar(estado='ADICIONAL', estado_asistencia='ASISTIO', reemplazo_id=self.rem.id)
        self.assertEqual(len(self._registros()), 1)                           # no se duplica

    def test_si_deja_de_ser_adicional_se_quita_solo_si_no_lo_completaron(self):
        self._guardar(estado='ADICIONAL', estado_asistencia='ASISTIO', reemplazo_id=self.rem.id)
        self._guardar(estado='TURNO', estado_asistencia='ASISTIO', reemplazo_id=None)
        self.assertEqual(self._registros(), [])
        self._guardar(estado='ADICIONAL', estado_asistencia='ASISTIO', reemplazo_id=self.rem.id)
        sa = self._registros()[0]
        sa.solicitado_por = 'GILDA'
        sa.save()
        self._guardar(estado='TURNO', estado_asistencia='ASISTIO', reemplazo_id=None)
        self.assertEqual(len(self._registros()), 1)                           # completado: se conserva

    def test_el_comando_pasa_los_que_ya_existian(self):
        from io import StringIO
        from django.core.management import call_command
        from CoreFisica.models import ReporteAsistencia, ReporteGuardia, ServicioAdicional
        ra = ReporteAsistencia.objects.create(asignacion=self.asig, fecha_reporte=D(2026, 10, 7))
        ReporteGuardia.objects.create(fecha=D(2026, 10, 7), turno='Diurno', seccion='ADICIONALES', cliente='PECHICHAL',
                                      puesto='GARITA', persona_nombre='PEDRO ADIC', reporte_asistencia=ra, auto=True)
        ReporteGuardia.objects.create(fecha=D(2026, 10, 6), turno='Nocturno', seccion='ADICIONALES', cliente='pechichal',
                                      puesto='X', persona_nombre='A MANO', auto=False)
        ReporteGuardia.objects.create(fecha=D(2026, 10, 6), turno='Nocturno', seccion='ADICIONALES', cliente='PECHICHAL',
                                      puesto='Y', persona_nombre='A MANO 2', auto=False)
        ReporteGuardia.objects.create(fecha=D(2026, 10, 6), turno='Diurno', seccion='ADICIONALES', cliente='NO EXISTE',
                                      puesto='Z', persona_nombre='?', auto=False)
        out = StringIO()
        call_command('pasar_adicionales_existentes', '--dry-run', stdout=out)
        self.assertEqual(ServicioAdicional.objects.count(), 0)                # la prueba no guarda
        out = StringIO()
        call_command('pasar_adicionales_existentes', stdout=out)
        texto = out.getvalue()
        self.assertIn('1 pasados desde la asistencia', texto)
        self.assertIn('1 pasados desde filas a mano', texto)
        self.assertIn('1 omitidos (cliente no encontrado)', texto)
        sa = ServicioAdicional.objects.get(asignacion=self.asig)
        self.assertEqual((sa.horas, sa.hora_ingreso), (12, datetime.time(7)))
        self.assertEqual(ServicioAdicional.objects.get(asignacion__isnull=True).cantidad, 2)   # 2 filas a mano
        out = StringIO()
        call_command('pasar_adicionales_existentes', stdout=out)              # repetirlo no duplica
        self.assertEqual(ServicioAdicional.objects.count(), 2)


class AdicionalManualTests(TestCase):
    """Adicional agregado con el botón de la asistencia: cliente / instalación / puesto de la lista o escritos a mano,
    guardia obligatorio; sale como fila en el Reporte de Asistencia y en el Reporte de Guardia (ADICIONALES)."""

    def setUp(self):
        User.objects.create_superuser(username='am_admin', email='e@e.com', password='AmPass123!x')
        tok = self.client.post('/api/login/', data=json.dumps({'username': 'am_admin', 'password': 'AmPass123!x'}),
                               content_type='application/json').json().get('access')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {tok}'}
        self.guardia = Persona.objects.create(nombres='MARIO', apellidos='TORRES ARIAS', cedula='0910000811', tipo='RETEN')

    def _crear(self, **datos):
        base = {'fecha': '2026-10-07', 'turno': 'Diurno', 'cliente_texto': 'feria del hogar', 'puesto_texto': 'stand 4',
                'persona_id': self.guardia.id, 'cantidad': 1, 'horas': 8, 'hora_ingreso': '08:00', 'hora_salida': '16:00'}
        base.update(datos)
        return self.client.post('/api/servicios-adicionales/crear/', data=json.dumps(base),
                                content_type='application/json', **self.auth)

    def _guardia(self):
        from CoreFisica.models import ReporteGuardia
        return list(ReporteGuardia.objects.filter(seccion='ADICIONALES', fecha=D(2026, 10, 7)))

    def test_cliente_y_puesto_escritos_a_mano(self):
        r = self._crear()
        self.assertEqual(r.status_code, 201, r.content)
        f = r.json()
        self.assertEqual((f['cliente_texto'], f['puesto'], f['persona'], f['manual']),
                         ('FERIA DEL HOGAR', 'STAND 4', 'TORRES ARIAS MARIO', True))

    def test_sin_guardia_no_va_al_reporte_de_guardia(self):
        sid = self._crear(persona_id=None).json()['id']
        self.assertEqual(self._guardia(), [])
        self.client.put(f'/api/servicios-adicionales/{sid}/', data=json.dumps({'persona_id': self.guardia.id}),
                        content_type='application/json', **self.auth)
        self.assertEqual(len(self._guardia()), 1)                         # al ponerle guardia, aparece

    def test_crea_su_fila_en_el_reporte_de_guardia_y_la_actualiza(self):
        sid = self._crear().json()['id']
        filas = self._guardia()
        self.assertEqual(len(filas), 1)
        g = filas[0]
        self.assertEqual((g.turno, g.cliente, g.puesto, g.persona_nombre, g.proviene, g.auto),
                         ('Diurno', 'FERIA DEL HOGAR', 'STAND 4', 'MARIO TORRES ARIAS', 'RETEN', False))
        self.client.put(f'/api/servicios-adicionales/{sid}/', data=json.dumps({'turno': 'Nocturno', 'puesto_texto': 'stand 9'}),
                        content_type='application/json', **self.auth)
        g = self._guardia()[0]
        self.assertEqual((g.turno, g.puesto), ('Nocturno', 'STAND 9'))
        # Regenerar el reporte de guardia no la borra (es manual).
        from CoreFisica.views.reporte_guardia_views import regenerar_guardia_dia
        regenerar_guardia_dia(D(2026, 10, 7))
        self.assertEqual(len(self._guardia()), 1)

    def test_eliminar_borra_tambien_la_fila_de_guardia(self):
        sid = self._crear().json()['id']
        r = self.client.delete(f'/api/servicios-adicionales/{sid}/eliminar/', **self.auth)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self._guardia(), [])

    def test_sale_como_fila_en_el_reporte_de_asistencia(self):
        sid = self._crear().json()['id']
        d = self.client.get('/api/reporte-asistencia/', {'fecha': '2026-10-07', 'turno': 'Diurno'}, **self.auth).json()
        filas = [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('servicio_adicional_id') == sid]
        self.assertEqual(len(filas), 1)
        f = filas[0]
        self.assertEqual((f['cliente'], f['puesto'], f['reemplazo'], f['nombre_apellidos'], f['estado'], f['horario'], f['codigo']),
                         ('FERIA DEL HOGAR', 'STAND 4', 'TORRES ARIAS MARIO', '', 'ADICIONAL', '08:00 - 16:00', ''))
        d = self.client.get('/api/reporte-asistencia/', {'fecha': '2026-10-07', 'turno': 'Nocturno'}, **self.auth).json()
        self.assertFalse([f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('servicio_adicional_id') == sid])

    def test_con_cliente_de_la_lista(self):
        cli = Cliente.objects.create(razon_social='X SA', nombre_comercial='CLIENTE X')
        inst = Instalacion.objects.create(cliente=cli, nombre='INST X', codigo='X9')
        r = self._crear(cliente_texto='', instalacion_id=inst.id)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((r.json()['cliente'], r.json()['cliente_texto']), ('CLIENTE X', 'INST X'))
        self.assertEqual(self._guardia()[0].cliente, 'CLIENTE X')

    def test_los_que_salen_de_la_asistencia_no_se_eliminan_aqui(self):
        cli = Cliente.objects.create(razon_social='Y SA', nombre_comercial='Y')
        inst = Instalacion.objects.create(cliente=cli, nombre='INST Y')
        puesto = Puesto.objects.create(instalacion=inst, nombre='P')
        tit = Persona.objects.create(nombres='T', apellidos='T', cedula='0910000812', tipo='FIJOS')
        asig = Asignacion.objects.create(persona=tit, cliente=cli, instalacion=inst, puesto=puesto, mes=10, anio=2026,
                                         estado='ACTIVO', start_date=D(2026, 10, 1))
        sid = self._crear(asignacion_id=asig.id, instalacion_id=inst.id, cliente_texto='', persona_id=None).json()['id']
        r = self.client.delete(f'/api/servicios-adicionales/{sid}/eliminar/', **self.auth)
        self.assertEqual(r.status_code, 400)
