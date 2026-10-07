"""Reporte de Asistencia: el horario que se muestra sigue la D / N de la persona ese día.

El horario de noche cruza la medianoche y el de día no. Si el puesto solo tiene uno de los dos, a la
persona del otro turno se le muestra el reverso (19:00 - 07:00 / 07:00 - 19:00). Un horario guardado
como "nocturno" que en realidad es de día se trata como de día.
"""
import datetime
import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from CoreFisica.models import Asignacion, Cliente, Instalacion, Persona, Puesto, PuestoHorario
from CoreFisica.views.reporte_asistencia_views import _horas_de_turno

T = datetime.time


class HorasDeTurnoTests(SimpleTestCase):
    DIA = (T(7, 0), T(19, 0), 'Diurno')
    NOCHE = (T(19, 0), T(7, 0), 'Nocturno')

    def test_el_puesto_tiene_el_horario_del_turno(self):
        self.assertEqual(_horas_de_turno([self.DIA, self.NOCHE], 'Nocturno'), (T(19, 0), T(7, 0)))
        self.assertEqual(_horas_de_turno([self.DIA, self.NOCHE], 'Diurno'), (T(7, 0), T(19, 0)))

    def test_solo_de_dia_y_la_persona_de_noche_se_da_la_vuelta(self):
        self.assertEqual(_horas_de_turno([self.DIA], 'Nocturno'), (T(19, 0), T(7, 0)))

    def test_solo_de_noche_y_la_persona_de_dia_se_da_la_vuelta(self):
        self.assertEqual(_horas_de_turno([self.NOCHE], 'Diurno'), (T(7, 0), T(19, 0)))

    def test_se_respeta_una_excepcion_guardada(self):
        self.assertEqual(_horas_de_turno([self.DIA, (T(18, 0), T(6, 0), 'Nocturno')], 'Nocturno'), (T(18, 0), T(6, 0)))
        self.assertEqual(_horas_de_turno([(T(18, 0), T(6, 0), 'Nocturno')], 'Nocturno'), (T(18, 0), T(6, 0)))

    def test_un_nocturno_mal_cargado_con_horas_de_dia_se_trata_como_de_dia(self):
        mal = (T(7, 0), T(19, 0), 'Nocturno')
        self.assertEqual(_horas_de_turno([mal], 'Nocturno'), (T(19, 0), T(7, 0)))
        self.assertEqual(_horas_de_turno([mal], 'Diurno'), (T(7, 0), T(19, 0)))

    def test_24_horas_y_sin_datos_no_se_tocan(self):
        self.assertIsNone(_horas_de_turno([(T(7, 0), T(7, 0), 'Ambos')], 'Nocturno'))
        self.assertIsNone(_horas_de_turno([(None, None, 'Diurno')], 'Nocturno'))
        self.assertIsNone(_horas_de_turno([], 'Nocturno'))

    def test_un_bloque_corto_no_se_invierte(self):
        self.assertIsNone(_horas_de_turno([(T(16, 0), T(21, 0), 'Diurno')], 'Nocturno'))


class HorarioEnElReporteTests(TestCase):
    FECHA = datetime.date(2026, 9, 29)

    def setUp(self):
        User.objects.create_superuser(username='hr_user', email='e@e.com', password='HrPass123!')
        tok = self.client.post('/api/login/', data=json.dumps({'username': 'hr_user', 'password': 'HrPass123!'}),
                               content_type='application/json').json().get('access')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {tok}'}
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        inst = Instalacion.objects.create(cliente=cli, nombre='I')
        self.puesto = Puesto.objects.create(instalacion=inst, nombre='P')
        PuestoHorario.objects.create(puesto=self.puesto, dia=self.FECHA.weekday() + 1, turno='Diurno',
                                     hora_ingreso=T(7, 0), hora_salida=T(19, 0))
        persona = Persona.objects.create(nombres='A', apellidos='A', cedula='0910000040', tipo='FIJOS')
        self.asig = Asignacion.objects.create(persona=persona, cliente=cli, instalacion=inst, puesto=self.puesto,
                                              mes=9, anio=2026, estado='ACTIVO', recurring=True,
                                              start_date=datetime.date(2026, 9, 1), end_date=datetime.date(2026, 9, 30))

    def _horario(self, letra, turno):
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={self.asig.id: letra}):
            r = self.client.get('/api/reporte-asistencia/', {'fecha': self.FECHA.isoformat(), 'turno': turno}, **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        filas = d.get('results', d) if isinstance(d, dict) else d
        filas = [f for f in filas if f.get('asignacion_id') == self.asig.id]
        return filas[0]['horario'] if filas else None

    def test_el_puesto_solo_de_dia_muestra_19_07_a_quien_trabaja_de_noche(self):
        self.assertEqual(self._horario('N', 'Nocturno'), '19:00 - 07:00')

    def test_quien_trabaja_de_dia_sigue_viendo_07_19(self):
        self.assertEqual(self._horario('D', 'Diurno'), '07:00 - 19:00')

    def test_la_fila_trae_apellidos_y_nombres_por_separado(self):
        """Para mostrar los apellidos arriba y los nombres abajo."""
        Persona.objects.filter(cedula='0910000040').update(apellidos='TATAMUES AGUIRRE', nombres='DIEGO ARMANDO')
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={self.asig.id: 'D'}):
            r = self.client.get('/api/reporte-asistencia/', {'fecha': self.FECHA.isoformat(), 'turno': 'Diurno'}, **self.auth)
        d = r.json()
        fila = [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('asignacion_id') == self.asig.id][0]
        self.assertEqual(fila['nombre_apellidos'], 'TATAMUES AGUIRRE DIEGO ARMANDO')
        self.assertEqual((fila['apellidos_txt'], fila['nombres_txt']), ('TATAMUES AGUIRRE', 'DIEGO ARMANDO'))


class SacafrancoNoDuplicadoTests(TestCase):
    """Una fila de sacafranco de SEPTIEMBRE con semanas proyectadas a octubre no debe hacer salir al
    sacafranco duplicado en el reporte de un día de octubre (cada mes tiene su propia fila)."""

    def test_el_sacafranco_sale_una_sola_vez(self):
        from CoreFisica.models import SacafrancoFila, SacafrancoFilaSemanal, Instalacion as Inst
        User.objects.create_superuser(username='sd_user', email='e@e.com', password='SdPass123!')
        tok = self.client.post('/api/login/', data=json.dumps({'username': 'sd_user', 'password': 'SdPass123!'}),
                               content_type='application/json').json().get('access')
        auth = {'HTTP_AUTHORIZATION': f'Bearer {tok}'}
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        Inst.objects.create(cliente=cli, nombre='ISLA', codigo='P2')
        persona = Persona.objects.create(nombres='JOSE', apellidos='FARFAN', cedula='0910000050', tipo='SACAFRANCO')
        dia = datetime.date(2026, 10, 5)                                   # lunes
        for mes, anio in ((9, 2026), (10, 2026)):
            fila = SacafrancoFila.objects.create(mes=mes, anio=anio, persona=persona, orden=1)
            SacafrancoFilaSemanal.objects.create(sacafranco_fila=fila, week_start=datetime.date(2026, 10, 1),
                                                 mon='DP2', tue='DP2', wed='DP2', thu='DP2', fri='DP2', sat='DP2', sun='DP2')
        r = self.client.get('/api/reporte-asistencia/', {'fecha': dia.isoformat(), 'turno': 'Diurno'}, **auth)
        d = r.json()
        filas = [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('sacafranco_fila_id')]
        self.assertEqual(len(filas), 1, [f.get('sacafranco_fila_id') for f in filas])
        self.assertEqual(SacafrancoFila.objects.get(id=filas[0]['sacafranco_fila_id']).mes, 10)    # la de octubre


class PuestoCerradoNoSaleTests(HorarioEnElReporteTests):
    """Un puesto CERRADO (INACTIVO) solo sale en un día si ese día tiene datos REALES guardados; un registro
    vacío generado por defecto no lo hace aparecer."""

    def _filas_del_puesto(self):
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={self.asig.id: 'D'}):
            r = self.client.get('/api/reporte-asistencia/', {'fecha': self.FECHA.isoformat(), 'turno': 'Diurno'}, **self.auth)
        d = r.json()
        return [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('asignacion_id') == self.asig.id]

    def test_inactivo_con_registro_vacio_no_sale(self):
        from CoreFisica.models import ReporteAsistencia
        Asignacion.objects.filter(id=self.asig.id).update(estado='INACTIVO')
        ReporteAsistencia.objects.update_or_create(asignacion=self.asig, defaults={'fecha_reporte': self.FECHA, 'estado': 'TURNO'})
        self.assertEqual(self._filas_del_puesto(), [])

    def test_inactivo_con_datos_reales_ese_dia_si_sale(self):
        from CoreFisica.models import ReporteAsistencia
        Asignacion.objects.filter(id=self.asig.id).update(estado='INACTIVO')
        ReporteAsistencia.objects.update_or_create(
            asignacion=self.asig, defaults={'fecha_reporte': self.FECHA, 'estado': 'TURNO', 'estado_asistencia': 'FALTO'})
        self.assertEqual(len(self._filas_del_puesto()), 1)


class BaseTarde24hTests(HorarioEnElReporteTests):
    """DB / NB en un FIJO lo muestran en BASE; T y V solas en un SACAFRANCO lo ponen en BASE; T cuenta en Diurno
    y V en Diurno y Nocturno; en la Guardia la T va en Diurno y la V en el turno del filtro desde el que se guarda."""

    def _fila(self, letra, token, turno):
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={self.asig.id: letra}), \
             mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_raw_for_date',
                        return_value={self.asig.id: token}):
            r = self.client.get('/api/reporte-asistencia/', {'fecha': self.FECHA.isoformat(), 'turno': turno}, **self.auth)
        d = r.json()
        filas = [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('asignacion_id') == self.asig.id]
        return filas[0] if filas else None

    def test_fijo_con_db_sale_en_base(self):
        f = self._fila('D', 'DB', 'Diurno')
        self.assertEqual((f['codigo'], f['cliente'], f['puesto_tipo']), ('BASE', 'SEGURIDAD FISICA', 'DIA BASE'))

    def test_fijo_con_nb_sale_en_base_de_noche(self):
        f = self._fila('N', 'NB', 'Nocturno')
        self.assertEqual((f['codigo'], f['puesto_tipo']), ('BASE', 'NOCHE BASE'))

    def test_fijo_normal_no_cambia(self):
        f = self._fila('D', 'D', 'Diurno')
        self.assertNotEqual(f['codigo'], 'BASE')

    def test_el_sacafranco_acepta_t_sola_en_base_y_no_la_v(self):
        from CoreFisica.views.asignacion_semanal_views import _parse_sacafranco_token
        self.assertEqual(_parse_sacafranco_token('T')[:3], ('base_free', 'Tarde', 'BASE'))
        self.assertEqual(_parse_sacafranco_token('V')[0], 'invalid')
        self.assertEqual(_parse_sacafranco_token('DB')[:3], ('base_free', 'Diurno', 'BASE'))

    def test_turno_de_la_guardia(self):
        from CoreFisica.views.reporte_asistencia_views import _turno_guardia
        self.assertEqual((_turno_guardia('D'), _turno_guardia('N'), _turno_guardia('T')), ('Diurno', 'Nocturno', 'Diurno'))
        self.assertEqual((_turno_guardia('V', 'Nocturno'), _turno_guardia('V', 'Diurno'), _turno_guardia('V')), ('Nocturno', 'Diurno', 'Diurno'))
        self.assertEqual(_turno_guardia('F'), '')

    def test_la_v_sale_en_diurno_y_en_nocturno_y_la_t_en_diurno(self):
        self.assertIsNotNone(self._fila('V', 'V', 'Diurno'))
        self.assertIsNotNone(self._fila('V', 'V', 'Nocturno'))
        self.assertIsNotNone(self._fila('T', 'T', 'Diurno'))
        self.assertIsNone(self._fila('T', 'T', 'Nocturno'))


class BusquedaNominativoTests(HorarioEnElReporteTests):
    """Buscar un nominativo (ej. G3) trae ESE nominativo exacto, no G30, G31..."""

    def test_nominativo_exacto(self):
        Instalacion.objects.filter(id=self.asig.instalacion_id).update(codigo='G3')
        cli = Cliente.objects.create(razon_social='D SA', nombre_comercial='D')
        inst30 = Instalacion.objects.create(cliente=cli, nombre='OTRA', codigo='G30')
        p30 = Puesto.objects.create(instalacion=inst30, nombre='P30')
        per = Persona.objects.create(nombres='B', apellidos='B', cedula='0910000041', tipo='FIJOS')
        a30 = Asignacion.objects.create(persona=per, cliente=cli, instalacion=inst30, puesto=p30, mes=9, anio=2026,
                                        estado='ACTIVO', recurring=True,
                                        start_date=datetime.date(2026, 9, 1), end_date=datetime.date(2026, 9, 30))
        with mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                        return_value={self.asig.id: 'D', a30.id: 'D'}):
            r = self.client.get('/api/reporte-asistencia/', {'fecha': self.FECHA.isoformat(), 'q': 'g3'}, **self.auth)
        d = r.json()
        filas = d.get('results', d) if isinstance(d, dict) else d
        self.assertEqual({f.get('codigo') for f in filas}, {'G3'})


class SacafrancoTardeTests(TestCase):
    """La T (tarde) del sacafranco: sale en BASE como TARDE BASE, en el filtro Diurno, y no en Nocturno."""
    FECHA = datetime.date(2026, 10, 5)

    def setUp(self):
        from CoreFisica.models import SacafrancoFila, SacafrancoFilaSemanal
        User.objects.create_superuser(username='st_user', email='e@e.com', password='StPass123!')
        tok = self.client.post('/api/login/', data=json.dumps({'username': 'st_user', 'password': 'StPass123!'}),
                               content_type='application/json').json().get('access')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {tok}'}
        p = Persona.objects.create(nombres='T', apellidos='TARDE', cedula='0910000060', tipo='SACAFRANCO')
        self.fila = SacafrancoFila.objects.create(mes=10, anio=2026, persona=p, orden=1)
        SacafrancoFilaSemanal.objects.create(sacafranco_fila=self.fila, week_start=datetime.date(2026, 10, 1),
                                             mon='T', tue='T', wed='T', thu='T', fri='T', sat='T', sun='T')

    def _filas(self, turno):
        r = self.client.get('/api/reporte-asistencia/', {'fecha': self.FECHA.isoformat(), 'turno': turno}, **self.auth)
        d = r.json()
        return [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('sacafranco_fila_id') == self.fila.id]

    def test_t_sale_en_diurno_como_tarde_base(self):
        f = self._filas('Diurno')
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]['codigo'], f[0]['puesto'], f[0]['turno']), ('BASE', 'TARDE BASE', 'Tarde'))
        self.assertEqual(self._filas('Nocturno'), [])

    def test_la_guardia_de_la_t_va_en_diurno(self):
        from CoreFisica.views.reporte_asistencia_views import _saca_guardia_ctx
        self.assertEqual(_saca_guardia_ctx(self.fila, self.FECHA), ('Diurno', 'SEGURIDAD FISICA', ''))

    def test_t_con_nominativo_cubre_ese_puesto_en_diurno(self):
        from CoreFisica.models import SacafrancoFilaSemanal
        from CoreFisica.views.asignacion_semanal_views import _parse_sacafranco_token
        self.assertEqual(_parse_sacafranco_token('TG15')[:3], ('coverage', 'Tarde', 'G15'))
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='CLIENTE T')
        Instalacion.objects.create(cliente=cli, nombre='INST T', codigo='G15')
        SacafrancoFilaSemanal.objects.filter(sacafranco_fila=self.fila).update(mon='TG15')
        f = self._filas('Diurno')
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]['codigo'], f[0]['cliente'], f[0]['turno']), ('G15', 'CLIENTE T', 'Tarde'))
        self.assertEqual(self._filas('Nocturno'), [])

    def test_el_cronograma_acepta_t_y_t_con_nominativo(self):
        cli = Cliente.objects.create(razon_social='C2 SA', nombre_comercial='C2')
        Instalacion.objects.create(cliente=cli, nombre='INST 16', codigo='G16')
        from CoreFisica.models import SacafrancoFila
        hoy = datetime.date.today()
        ws = hoy.replace(day=1)
        fila = SacafrancoFila.objects.create(mes=hoy.month, anio=hoy.year, persona=self.fila.persona, orden=2)
        for token in ('T', 'TG16'):
            r = self.client.post('/api/sacafranco-fila-semanal/guardar/', data=json.dumps(
                {'sacafranco_fila': fila.id, 'week_start': ws.isoformat(), 'mon': token}),
                content_type='application/json', **self.auth)
            self.assertIn(r.status_code, (200, 201), (token, r.content))


class Asistencia24hIndependienteTests(HorarioEnElReporteTests):
    """24 horas (V): el Diurno y el Nocturno tienen cada uno su asistencia. Marcar FALTÓ en el Diurno no cambia el
    Nocturno (ni al revés); un registro anterior sin turno sale en los dos hasta que se cambie."""

    def _v(self):
        return mock.patch('CoreFisica.views.reporte_asistencia_views._calendar_dnf_for_date',
                          return_value={self.asig.id: 'V'})

    def _guardar(self, turno, **datos):
        with self._v():
            r = self.client.put(f'/api/reporte-asistencia/{self.asig.id}/',
                                data=json.dumps({'fecha': self.FECHA.isoformat(), 'turno': turno, **datos}),
                                content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)

    def _filas(self, turno=None):
        params = {'fecha': self.FECHA.isoformat()}
        if turno:
            params['turno'] = turno
        with self._v():
            d = self.client.get('/api/reporte-asistencia/', params, **self.auth).json()
        return [f for f in (d.get('results', d) if isinstance(d, dict) else d) if f.get('asignacion_id') == self.asig.id]

    def _estado(self, turno):
        f = self._filas(turno)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['turno_registro'], turno)
        return f[0]['estado_asistencia']

    def test_falto_en_diurno_no_cambia_el_nocturno(self):
        self._guardar('Diurno', estado_asistencia='FALTO')
        self.assertEqual(self._estado('Diurno'), 'FALTO')
        self.assertIn(self._estado('Nocturno'), (None, ''))
        self._guardar('Nocturno', estado_asistencia='ASISTIO', estado='TURNO')
        self.assertEqual(self._estado('Diurno'), 'FALTO')
        self.assertEqual(self._estado('Nocturno'), 'ASISTIO')

    def test_un_cambio_parcial_no_arrastra_lo_del_otro_turno(self):
        self._guardar('Diurno', estado_asistencia='FALTO', descripcion='ENFERMO')
        self._guardar('Nocturno', row_color='#fff8b3')
        f = self._filas('Nocturno')[0]
        self.assertIn(f['estado_asistencia'], (None, ''))
        self.assertIn(f['descripcion'] or '', ('',))

    def test_sin_filtro_salen_las_dos_filas(self):
        self._guardar('Diurno', estado_asistencia='FALTO')
        self.assertEqual(sorted(f['turno_registro'] for f in self._filas()), ['Diurno', 'Nocturno'])

    def test_un_registro_anterior_sin_turno_sale_en_los_dos(self):
        from CoreFisica.models import ReporteAsistencia, ReporteAsistenciaHistorial
        ra = ReporteAsistencia.objects.create(asignacion=self.asig, fecha_reporte=self.FECHA,
                                              estado_asistencia='ASISTIO')
        ReporteAsistenciaHistorial.objects.create(reporte=ra, asignacion=self.asig, fecha_reporte=self.FECHA,
                                                  estado_asistencia='ASISTIO')
        self.assertEqual((self._estado('Diurno'), self._estado('Nocturno')), ('ASISTIO', 'ASISTIO'))
        self._guardar('Nocturno', estado_asistencia='FALTO')
        self.assertEqual((self._estado('Diurno'), self._estado('Nocturno')), ('ASISTIO', 'FALTO'))

    def test_la_guardia_tiene_un_falto_por_turno(self):
        from CoreFisica.models import ReporteGuardia
        from CoreFisica.views.reporte_guardia_views import regenerar_guardia_dia
        self._guardar('Diurno', estado_asistencia='FALTO')
        self._guardar('Nocturno', estado_asistencia='FALTO')
        faltos = lambda: sorted(ReporteGuardia.objects.filter(fecha=self.FECHA, seccion='FALTOS')
                                .values_list('turno', flat=True))
        self.assertEqual(faltos(), ['Diurno', 'Nocturno'])
        self._guardar('Diurno', estado_asistencia='ASISTIO', estado='TURNO')
        self.assertEqual(faltos(), ['Nocturno'])
        with self._v():
            regenerar_guardia_dia(self.FECHA)
        self.assertEqual(faltos(), ['Nocturno'])

    def test_excel_y_pdf_ponen_cada_fila_24h_en_su_hoja(self):
        from CoreFisica.views.reporte_asistencia_views import _rows_por_jornada
        filas = [{'turno': 'Veinticuatro', 'turno_registro': 'Diurno', 'id': 1},
                 {'turno': 'Veinticuatro', 'turno_registro': 'Nocturno', 'id': 2},
                 {'turno': 'Diurno', 'turno_registro': '', 'id': 3},
                 {'turno': 'Nocturno', 'turno_registro': '', 'id': 4},
                 {'turno': 'Veinticuatro', 'id': 5}]
        self.assertEqual([f['id'] for f in _rows_por_jornada(filas, 'Diurno')], [1, 3, 5])
        self.assertEqual([f['id'] for f in _rows_por_jornada(filas, 'Nocturno')], [2, 4, 5])

    def test_consolidado_sin_turno_cuenta_una_vez_a_la_de_24h(self):
        from CoreFisica.views.consolidado_views import _una_fila_24h
        filas = [{'turno_registro': 'Diurno'}, {'turno_registro': 'Nocturno'}, {'turno_registro': ''}]
        self.assertEqual(len(_una_fila_24h(filas, None)), 2)
        self.assertEqual(len(_una_fila_24h(filas, 'Nocturno')), 3)
