"""Los meses SIGUIENTES de Asignaciones siguen al mes base.

Problema: al importar, el sistema copia las asignaciones a los meses siguientes, pero esas
copias no se actualizaban al editar el mes base (octubre quedaba con una foto vieja de
septiembre). Ahora:
- `alinear_meses` / comando `continuar_meses_desde` los alinea (registros, orden, cronograma).
- crear / editar / eliminar una asignación del mes ACTUAL se pasa solo a los meses siguientes.
- editar una asignación ya no la deja abierta (end_date vacío): se acota al fin de su mes.
"""
import datetime
import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from CoreFisica.asignaciones_meses import (
    alinear_meses, escribir_mes, sumar_meses, tokens_mes, ultimo_dia,
)
from CoreFisica.models import (
    Asignacion, AsignacionSemanal, Cliente, Instalacion, Persona, Puesto,
)


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class AsignacionesMesesTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='am_user', email='e@e.com', password='AmPass123!')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'am_user', 'AmPass123!')}"}
        hoy = timezone.localdate()
        self.anio, self.mes = hoy.year, hoy.month            # mes base = el mes ACTUAL
        self.sig_anio, self.sig_mes = sumar_meses(self.anio, self.mes, 1)

        self.cli = Cliente.objects.create(razon_social='CLI SA', nombre_comercial='CLI')
        self.inst = Instalacion.objects.create(cliente=self.cli, nombre='MATRIZ')
        self.p1 = Puesto.objects.create(instalacion=self.inst, nombre='P1')
        self.p2 = Puesto.objects.create(instalacion=self.inst, nombre='P2')
        self.p3 = Puesto.objects.create(instalacion=self.inst, nombre='P3')
        mk = lambda n, c, t='FIJOS': Persona.objects.create(nombres=n, apellidos='X', cedula=c, tipo=t)
        self.A, self.B = mk('A', '0900000001'), mk('B', '0900000002')
        self.C, self.D = mk('C', '0900000003'), mk('D', '0900000004')
        self.R = mk('R', '0900000005', 'RETEN')

    def _asig(self, persona, puesto, mes, anio, orden=0, estado='ACTIVO'):
        return Asignacion.objects.create(
            persona=persona, cliente=self.cli, instalacion=self.inst, puesto=puesto, mes=mes, anio=anio,
            orden=orden, estado=estado, recurring=True,
            start_date=datetime.date(anio, mes, 1),
            end_date=datetime.date(anio, mes, ultimo_dia(anio, mes)))

    def _siguiente(self, persona):
        return Asignacion.objects.filter(persona=persona, mes=self.sig_mes, anio=self.sig_anio).first()

    def _armar_meses(self):
        """Mes base (actual): A@P1, B@P2, C@P3.  Mes siguiente (foto vieja): A@P2, B@P1, D@P3 + RETEN."""
        self.bA = self._asig(self.A, self.p1, self.mes, self.anio, orden=1)
        self.bB = self._asig(self.B, self.p2, self.mes, self.anio, orden=2)
        self.bC = self._asig(self.C, self.p3, self.mes, self.anio, orden=3)
        self.tA = self._asig(self.A, self.p2, self.sig_mes, self.sig_anio, orden=7)
        self.tB = self._asig(self.B, self.p1, self.sig_mes, self.sig_anio, orden=8)
        self.tD = self._asig(self.D, self.p3, self.sig_mes, self.sig_anio, orden=9)
        self.tR = self._asig(self.R, self.p3, self.sig_mes, self.sig_anio, orden=10)

    # ---------------- registros ----------------
    def test_alinear_deja_el_mes_siguiente_igual_al_base(self):
        self._armar_meses()
        alinear_meses(self.mes, self.anio)
        a, b, c = self._siguiente(self.A), self._siguiente(self.B), self._siguiente(self.C)
        self.assertEqual((a.puesto_id, a.orden), (self.p1.id, 1))          # A vuelve a P1
        self.assertEqual((b.puesto_id, b.orden), (self.p2.id, 2))          # B vuelve a P2
        self.assertIsNotNone(c)                                            # C no existía: se crea
        self.assertEqual((c.puesto_id, c.estado), (self.p3.id, 'ACTIVO'))
        self.assertEqual(self._siguiente(self.D).estado, 'INACTIVO')       # D ya no está: sobraba
        # El RETEN que solo existe en el mes siguiente NO se toca.
        self.tR.refresh_from_db()
        self.assertEqual(self.tR.estado, 'ACTIVO')

    def test_se_puede_repetir_sin_cambios(self):
        self._armar_meses()
        alinear_meses(self.mes, self.anio)
        segunda = alinear_meses(self.mes, self.anio)
        cambios = sum(v for _, _, r in segunda for k, v in r.items() if 'sin resolver' not in k and 'no continuados' not in k)
        self.assertEqual(cambios, 0)

    def test_no_borra_nada(self):
        self._armar_meses()
        antes = Asignacion.objects.count()
        alinear_meses(self.mes, self.anio)
        self.assertGreaterEqual(Asignacion.objects.count(), antes)         # solo crea / desactiva

    # ---------------- cronograma ----------------
    def test_el_cronograma_continua_donde_termino_el_mes_base(self):
        self._armar_meses()
        ciclo = ['D', 'D', 'N', 'N', 'F', 'F']
        n_base = ultimo_dia(self.anio, self.mes)
        base = [ciclo[i % 6] for i in range(n_base)]
        escribir_mes(self.bA, self.anio, self.mes, base)
        # El mes siguiente tiene el ciclo con la fase equivocada (foto vieja).
        n_sig = ultimo_dia(self.sig_anio, self.sig_mes)
        escribir_mes(self.tA, self.sig_anio, self.sig_mes, [ciclo[(i + 3) % 6] for i in range(n_sig)])
        alinear_meses(self.mes, self.anio)
        tA = self._siguiente(self.A)
        filas = {r.week_start: r for r in AsignacionSemanal.objects.filter(asignacion=tA)}
        esperado = [ciclo[(n_base + i) % 6] for i in range(n_sig)]
        self.assertEqual(tokens_mes(filas, self.sig_anio, self.sig_mes), esperado)

    def test_cronograma_con_cambios_a_mano_no_se_toca(self):
        self._armar_meses()
        ciclo = ['D', 'D', 'N', 'N', 'F', 'F']
        n_base, n_sig = ultimo_dia(self.anio, self.mes), ultimo_dia(self.sig_anio, self.sig_mes)
        escribir_mes(self.bA, self.anio, self.mes, [ciclo[i % 6] for i in range(n_base)])
        manual = [ciclo[(i + 3) % 6] for i in range(n_sig)]
        manual[4] = 'V'                                                    # una vacación escrita a mano
        escribir_mes(self.tA, self.sig_anio, self.sig_mes, manual)
        alinear_meses(self.mes, self.anio)
        tA = self._siguiente(self.A)
        filas = {r.week_start: r for r in AsignacionSemanal.objects.filter(asignacion=tA)}
        self.assertEqual(tokens_mes(filas, self.sig_anio, self.sig_mes), manual)

    # ---------------- comando ----------------
    def test_comando_prueba_no_guarda_y_luego_si(self):
        self._armar_meses()
        out = StringIO()
        call_command('continuar_meses_desde', '--mes', str(self.mes), '--anio', str(self.anio), '--dry-run', stdout=out)
        self.assertIn('PRUEBA', out.getvalue())
        self.assertEqual(self._siguiente(self.A).puesto_id, self.p2.id)    # nada cambió
        call_command('continuar_meses_desde', '--mes', str(self.mes), '--anio', str(self.anio), stdout=StringIO())
        self.assertEqual(self._siguiente(self.A).puesto_id, self.p1.id)

    # ---------------- propagación automática ----------------
    def test_editar_en_el_mes_actual_no_toca_el_mes_siguiente(self):
        # Ya NO se copia en vivo: el mes siguiente se crea al cambiar de mes (cierre_de_mes).
        self._armar_meses()
        alinear_meses(self.mes, self.anio)                                 # parten alineados
        r = self.client.put(f'/api/editar-servicio/{self.bA.id}/',
                            data=json.dumps({'persona': self.C.id}), content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._siguiente(self.A).puesto_id, self.p1.id)    # A sigue igual en el mes siguiente
        self.assertEqual(self._siguiente(self.A).estado, 'ACTIVO')
        self.assertEqual(self._siguiente(self.C).puesto_id, self.p3.id)    # C sigue en su puesto del mes siguiente

    def test_editar_ya_no_deja_la_asignacion_abierta(self):
        self._armar_meses()
        Asignacion.objects.filter(pk=self.bA.pk).update(end_date=None)     # fila "abierta"
        r = self.client.put(f'/api/editar-servicio/{self.bA.id}/', data=json.dumps({'orden': 5}),
                            content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self.bA.refresh_from_db()
        self.assertEqual(self.bA.end_date, datetime.date(self.anio, self.mes, ultimo_dia(self.anio, self.mes)))

    def test_editar_un_mes_pasado_no_se_propaga(self):
        ant_anio, ant_mes = sumar_meses(self.anio, self.mes, -1)
        pasado = self._asig(self.A, self.p1, ant_mes, ant_anio, orden=1)
        actual = self._asig(self.A, self.p1, self.mes, self.anio, orden=1)
        r = self.client.put(f'/api/editar-servicio/{pasado.id}/', data=json.dumps({'puesto': self.p2.id, 'persona': self.A.id}),
                            content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        actual.refresh_from_db()
        self.assertEqual(actual.puesto_id, self.p1.id)                     # el mes actual no se pisó

    def test_eliminar_en_el_mes_actual_no_toca_el_mes_siguiente(self):
        self._armar_meses()
        alinear_meses(self.mes, self.anio)
        r = self.client.delete(f'/api/eliminar-asignacion/{self.bB.id}/', **self.auth)
        self.assertIn(r.status_code, (200, 204), r.content)
        self.assertEqual(self._siguiente(self.B).estado, 'ACTIVO')         # el mes siguiente no se tocó

    def test_reordenar_filas_no_toca_el_mes_siguiente(self):
        self._armar_meses()
        alinear_meses(self.mes, self.anio)
        r = self.client.post('/api/guardar-orden-asignacion/', data=json.dumps({
            'mes': self.mes, 'anio': self.anio,
            'ordenes': [{'id': self.bA.id, 'orden': 50}, {'id': self.bB.id, 'orden': 40}]}),
            content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        self.bA.refresh_from_db()
        self.assertEqual(self.bA.orden, 50)                                # en el mes actual sí se guarda
        self.assertEqual(self._siguiente(self.A).orden, 1)                 # el mes siguiente conserva el suyo


class SacafrancoMesesTests(TestCase):
    """Los sacafranco del mes siguiente quedan en la misma vista y orden que en el mes base."""

    def setUp(self):
        from CoreFisica.models import SacafrancoFila, VistaCanton
        self.SacafrancoFila = SacafrancoFila
        hoy = timezone.localdate()
        self.anio, self.mes = hoy.year, hoy.month
        self.sig_anio, self.sig_mes = sumar_meses(self.anio, self.mes, 1)
        self.v1 = VistaCanton.objects.create(nombre='V1', tipo='canton')
        self.v2 = VistaCanton.objects.create(nombre='V2', tipo='canton')
        mk = lambda n, c: Persona.objects.create(nombres=n, apellidos='S', cedula=c, tipo='SACAFRANCO')
        self.s1, self.s2, self.s3 = mk('S1', '0910000001'), mk('S2', '0910000002'), mk('S3', '0910000003')
        # Mes base
        self.b1 = SacafrancoFila.objects.create(mes=self.mes, anio=self.anio, persona=self.s1, orden=3, vista=self.v1)
        self.b2 = SacafrancoFila.objects.create(mes=self.mes, anio=self.anio, persona=self.s2, orden=4, vista=self.v1)
        # Mes siguiente (foto vieja): S1 en otra vista y orden; S3 solo existe aquí; S2 no existe.
        self.t1 = SacafrancoFila.objects.create(mes=self.sig_mes, anio=self.sig_anio, persona=self.s1, orden=9, vista=self.v2)
        self.t3 = SacafrancoFila.objects.create(mes=self.sig_mes, anio=self.sig_anio, persona=self.s3, orden=1, vista=self.v2)
        # Para que el mes siguiente "exista" en Asignaciones (el alineador solo revisa meses con datos).
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        inst = Instalacion.objects.create(cliente=cli, nombre='I')
        pu = Puesto.objects.create(instalacion=inst, nombre='PU')
        per = Persona.objects.create(nombres='F', apellidos='F', cedula='0910000009', tipo='FIJOS')
        for mes, anio in ((self.mes, self.anio), (self.sig_mes, self.sig_anio)):
            Asignacion.objects.create(persona=per, cliente=cli, instalacion=inst, puesto=pu, mes=mes, anio=anio,
                                      estado='ACTIVO', recurring=True)

    def _fila(self, persona):
        return self.SacafrancoFila.objects.filter(persona=persona, mes=self.sig_mes, anio=self.sig_anio).first()

    def test_misma_vista_orden_y_se_crean_los_que_faltan(self):
        alinear_meses(self.mes, self.anio)
        f1 = self._fila(self.s1)
        self.assertEqual((f1.vista_id, f1.orden), (self.v1.id, 3))        # igual que el mes base
        f2 = self._fila(self.s2)
        self.assertIsNotNone(f2)                                          # S2 no existía: se crea
        self.assertEqual((f2.vista_id, f2.orden), (self.v1.id, 4))

    def test_el_que_solo_esta_en_el_mes_siguiente_no_se_borra_por_defecto(self):
        alinear_meses(self.mes, self.anio)
        self.assertIsNotNone(self._fila(self.s3))                         # solo se informa

    def test_se_puede_quitar_el_sobrante_si_se_pide(self):
        alinear_meses(self.mes, self.anio, quitar_sacafranco_sobrantes=True)
        self.assertIsNone(self._fila(self.s3))

    def test_en_modo_parcial_no_toca_sacafranco(self):
        alinear_meses(self.mes, self.anio, personas={999999}, puestos=set())
        self.assertEqual(self._fila(self.s1).vista_id, self.v2.id)        # sin cambios


class SoloDelMesSiguienteTests(TestCase):
    """Retenes / sacavacaciones / sacafranco que solo existen en el mes siguiente."""
    setUp = AsignacionesMesesTests.setUp
    _asig = AsignacionesMesesTests._asig

    def _armar(self):
        # Mes base: el puesto P1 está VACANTE (persona vacía) y A está en P2.
        Asignacion.objects.create(persona=None, cliente=self.cli, instalacion=self.inst, puesto=self.p1,
                                  mes=self.mes, anio=self.anio, estado='ACTIVO', recurring=True, es_hueca=True,
                                  start_date=datetime.date(self.anio, self.mes, 1))
        self._asig(self.A, self.p2, self.mes, self.anio, orden=1)
        # Mes siguiente: A está bien, pero un RETEN (R) ocupa P1 que en el base es vacante.
        self._asig(self.A, self.p2, self.sig_mes, self.sig_anio, orden=1)
        self.tR = self._asig(self.R, self.p1, self.sig_mes, self.sig_anio, orden=2)

    def test_por_defecto_no_se_toca_al_reten(self):
        self._armar()
        alinear_meses(self.mes, self.anio)
        self.tR.refresh_from_db()
        self.assertEqual(self.tR.estado, 'ACTIVO')

    def test_con_la_opcion_se_desactiva_y_el_puesto_vuelve_a_ser_vacante(self):
        self._armar()
        alinear_meses(self.mes, self.anio, quitar_solo_octubre=True)
        self.tR.refresh_from_db()
        self.assertEqual(self.tR.estado, 'INACTIVO')
        vacantes = Asignacion.objects.filter(puesto=self.p1, mes=self.sig_mes, anio=self.sig_anio,
                                             persona__isnull=True, estado='ACTIVO')
        self.assertEqual(vacantes.count(), 1)

    def test_se_puede_conservar_a_una_persona(self):
        self._armar()
        alinear_meses(self.mes, self.anio, quitar_solo_octubre=True, conservar_personas={self.R.id})
        self.tR.refresh_from_db()
        self.assertEqual(self.tR.estado, 'ACTIVO')

    def test_quien_esta_en_los_dos_meses_nunca_se_quita(self):
        self._armar()
        self._asig(self.R, self.p3, self.mes, self.anio, orden=3)           # R también está en el mes base
        self.tR.puesto = self.p3
        self.tR.save()
        alinear_meses(self.mes, self.anio, quitar_solo_octubre=True)
        self.tR.refresh_from_db()
        self.assertEqual(self.tR.estado, 'ACTIVO')

    def test_el_comando_acepta_la_opcion_y_conservar(self):
        self._armar()
        call_command('continuar_meses_desde', '--mes', str(self.mes), '--anio', str(self.anio),
                     '--quitar-solo-octubre', '--conservar', self.R.cedula, stdout=StringIO())
        self.tR.refresh_from_db()
        self.assertEqual(self.tR.estado, 'ACTIVO')



class VistaPorTipoExclusivaTests(TestCase):
    """La pestaña "por tipo de persona" (ej. RETEN) es EXCLUSIVA: esas personas no salen en las demás."""

    def setUp(self):
        from CoreFisica.models import SacafrancoFila, VistaCanton
        User.objects.create_superuser(username='vt_user', email='e@e.com', password='VtPass123!')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'vt_user', 'VtPass123!')}"}
        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        self.cli = Cliente.objects.create(razon_social='CLI SA', nombre_comercial='CLI')
        inst = Instalacion.objects.create(cliente=self.cli, nombre='MATRIZ')
        puesto = Puesto.objects.create(instalacion=inst, nombre='P1')
        self.fijo = Persona.objects.create(nombres='F', apellidos='FIJO', cedula='0920000001', tipo='FIJOS')
        self.reten = Persona.objects.create(nombres='R', apellidos='RETEN', cedula='0920000002', tipo='RETEN')
        for per in (self.fijo, self.reten):
            Asignacion.objects.create(persona=per, cliente=self.cli, instalacion=inst, puesto=puesto,
                                      mes=self.mes, anio=self.anio, estado='ACTIVO', recurring=True,
                                      start_date=datetime.date(self.anio, self.mes, 1))
        self.vista_cliente = VistaCanton.objects.create(nombre='EMPRESA', tipo='cliente', clientes=[self.cli.id])
        self.vista_tipo = VistaCanton.objects.create(nombre='RETEN', tipo='persona_tipo', tipos=['RETEN'])
        self.fila_saca = SacafrancoFila.objects.create(mes=self.mes, anio=self.anio, persona=self.reten, orden=1)

    def _personas(self, params):
        r = self.client.get(f'/api/asignaciones/{self.mes}/{self.anio}/', params, **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        res = r.json().get('results', [])
        return {(f['persona'].get('id') if isinstance(f['persona'], dict) else f['persona']) for f in res if f.get('persona')}

    def test_el_reten_ya_no_sale_en_la_vista_de_empresa(self):
        personas = self._personas({'cliente_ids': str(self.cli.id)})
        self.assertIn(self.fijo.id, personas)
        self.assertNotIn(self.reten.id, personas)

    def test_el_reten_sale_en_su_propia_pestana(self):
        self.assertEqual(self._personas({'tipos': 'RETEN'}), {self.reten.id})

    def test_sin_pestana_por_tipo_todo_sigue_igual(self):
        self.vista_tipo.delete()
        personas = self._personas({'cliente_ids': str(self.cli.id)})
        self.assertEqual(personas, {self.fijo.id, self.reten.id})

    def test_el_sacafranco_reten_sale_solo_en_su_pestana(self):
        def filas(vista_id):
            r = self.client.get('/api/sacafranco-filas/', {'mes': self.mes, 'anio': self.anio, 'vista_id': vista_id}, **self.auth)
            self.assertEqual(r.status_code, 200, r.content)
            d = r.json()
            lista = d if isinstance(d, list) else (d.get('results') or [])
            return {f.get('id') for f in lista}
        self.assertNotIn(self.fila_saca.id, filas(self.vista_cliente.id))      # en otra vista: no sale
        self.assertIn(self.fila_saca.id, filas(self.vista_tipo.id))            # en su pestaña: sí


class SacafrancoDesactivadoTests(TestCase):
    """Las filas de sacafranco de personas DESACTIVADAS no se muestran (igual que en asignaciones)."""

    def test_no_sale_el_sacafranco_con_la_ficha_desactivada(self):
        from CoreFisica.models import SacafrancoFila
        User.objects.create_superuser(username='sd_user', email='e@e.com', password='SdPass123!')
        auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'sd_user', 'SdPass123!')}"}
        hoy = timezone.localdate()
        activo = Persona.objects.create(nombres='A', apellidos='ACTIVO', cedula='0930000001', tipo='SACAFRANCO')
        baja = Persona.objects.create(nombres='B', apellidos='BAJA', cedula='0930000002', tipo='SACAFRANCO', estado_empleado='LIQUIDADO')
        f1 = SacafrancoFila.objects.create(mes=hoy.month, anio=hoy.year, persona=activo, orden=1)
        f2 = SacafrancoFila.objects.create(mes=hoy.month, anio=hoy.year, persona=baja, orden=2)
        f3 = SacafrancoFila.objects.create(mes=hoy.month, anio=hoy.year, persona=None, orden=3)   # fila vacía
        r = self.client.get('/api/sacafranco-filas/', {'mes': hoy.month, 'anio': hoy.year}, **auth)
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        ids = {f.get('id') for f in (d if isinstance(d, list) else (d.get('results') or []))}
        self.assertIn(f1.id, ids)
        self.assertIn(f3.id, ids)           # las filas vacías se mantienen
        self.assertNotIn(f2.id, ids)        # la persona desactivada no sale



class PersonasDesactivadasTests(TestCase):
    """Desactivar a una persona (LIQUIDADO / SUSPENDIDO) la quita de Asignaciones del mes actual en adelante."""

    def setUp(self):
        from CoreFisica.models import SacafrancoFila
        self.SacafrancoFila = SacafrancoFila
        User.objects.create_superuser(username='pd_user', email='e@e.com', password='PdPass123!')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'pd_user', 'PdPass123!')}"}
        hoy = timezone.localdate()
        self.anio, self.mes = hoy.year, hoy.month
        self.sig_anio, self.sig_mes = sumar_meses(self.anio, self.mes, 1)
        self.ant_anio, self.ant_mes = sumar_meses(self.anio, self.mes, -1)
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        self.inst = Instalacion.objects.create(cliente=cli, nombre='I')
        self.cli = cli
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='P1', cantidad_puestos=1)

    def _asig(self, persona, mes, anio, estado='ACTIVO'):
        return Asignacion.objects.create(persona=persona, cliente=self.cli, instalacion=self.inst, puesto=self.puesto,
                                         mes=mes, anio=anio, estado=estado, recurring=True,
                                         start_date=datetime.date(anio, mes, 1))

    def test_al_desactivar_sale_del_mes_actual_en_adelante_y_no_toca_el_pasado(self):
        p = Persona.objects.create(nombres='X', apellidos='FIJO', cedula='0940000001', tipo='FIJOS')
        pasado = self._asig(p, self.ant_mes, self.ant_anio)
        actual = self._asig(p, self.mes, self.anio)
        futuro = self._asig(p, self.sig_mes, self.sig_anio)
        p.estado_empleado = 'LIQUIDADO'
        p.save()
        for a in (pasado, actual, futuro):
            a.refresh_from_db()
        self.assertEqual(pasado.estado, 'ACTIVO')            # historial: no se toca
        self.assertEqual(actual.estado, 'INACTIVO')
        self.assertEqual(futuro.estado, 'INACTIVO')

    def test_sirve_para_cualquier_tipo(self):
        for i, tipo in enumerate(('SACAFRANCO', 'RETEN', 'SACAVACACIONES', 'SUPERVISOR EVENTUAL')):
            p = Persona.objects.create(nombres='X', apellidos=tipo, cedula=f'095000000{i}', tipo=tipo)
            a = self._asig(p, self.sig_mes, self.sig_anio)
            p.estado_empleado = 'SUSPENDIDO'
            p.save()
            a.refresh_from_db()
            self.assertEqual(a.estado, 'INACTIVO', tipo)

    def test_se_eliminan_sus_filas_de_sacafranco_menos_las_que_tienen_asistencia(self):
        from CoreFisica.models import SacafrancoAsistencia
        p = Persona.objects.create(nombres='S', apellidos='SACA', cedula='0960000001', tipo='SACAFRANCO')
        sin_historial = self.SacafrancoFila.objects.create(mes=self.sig_mes, anio=self.sig_anio, persona=p, orden=1)
        con_historial = self.SacafrancoFila.objects.create(mes=self.mes, anio=self.anio, persona=p, orden=1)
        SacafrancoAsistencia.objects.create(sacafranco_fila=con_historial, fecha=datetime.date(self.anio, self.mes, 1),
                                            estado_asistencia='ASISTIO')
        pasada = self.SacafrancoFila.objects.create(mes=self.ant_mes, anio=self.ant_anio, persona=p, orden=1)
        p.estado_empleado = 'LIQUIDADO'
        p.save()
        self.assertFalse(self.SacafrancoFila.objects.filter(pk=sin_historial.pk).exists())   # se elimina
        self.assertTrue(self.SacafrancoFila.objects.filter(pk=con_historial.pk).exists())    # tiene asistencia: se conserva
        self.assertTrue(self.SacafrancoFila.objects.filter(pk=pasada.pk).exists())           # mes pasado: no se toca

    def test_una_persona_activa_no_se_toca(self):
        p = Persona.objects.create(nombres='A', apellidos='ACTIVA', cedula='0970000001', tipo='FIJOS')
        a = self._asig(p, self.sig_mes, self.sig_anio)
        p.nombres = 'A2'
        p.save()
        a.refresh_from_db()
        self.assertEqual(a.estado, 'ACTIVO')

    def test_la_desactivada_no_ocupa_cupo_ni_bloquea_al_asignar(self):
        # Datos viejos: la persona ya estaba desactivada con su asignación todavía ACTIVA (se fuerza sin pasar por save()).
        baja = Persona.objects.create(nombres='B', apellidos='BAJA', cedula='0980000001', tipo='FIJOS')
        self._asig(baja, self.mes, self.anio)
        Persona.objects.filter(pk=baja.pk).update(estado_empleado='LIQUIDADO', is_active=False)
        nuevo = Persona.objects.create(nombres='N', apellidos='NUEVO', cedula='0980000002', tipo='FIJOS')
        r = self.client.get(f'/api/puestos-ocupacion/{self.mes}/{self.anio}/', **self.auth)
        if r.status_code == 200:
            self.assertNotIn(str(self.puesto.id), r.json().get('ocupacion', {}))
        r = self.client.post('/api/asignar-servicio/', data=json.dumps({
            'persona': nuevo.id, 'cliente': self.cli.id, 'instalacion': self.inst.id, 'puesto': self.puesto.id,
            'mes': self.mes, 'anio': self.anio}), content_type='application/json', **self.auth)
        self.assertIn(r.status_code, (200, 201), r.content)      # antes: "ya alcanzó su cantidad máxima"

    def test_el_comando_en_prueba_no_guarda(self):
        p = Persona.objects.create(nombres='C', apellidos='CMD', cedula='0990000001', tipo='FIJOS')
        a = self._asig(p, self.sig_mes, self.sig_anio)
        Persona.objects.filter(pk=p.pk).update(estado_empleado='LIQUIDADO', is_active=False)
        out = StringIO()
        call_command('limpiar_personas_desactivadas', '--dry-run', stdout=out)
        a.refresh_from_db()
        self.assertEqual(a.estado, 'ACTIVO')
        self.assertIn('PRUEBA', out.getvalue())
        call_command('limpiar_personas_desactivadas', stdout=StringIO())
        a.refresh_from_db()
        self.assertEqual(a.estado, 'INACTIVO')


class CicloDeContinuacionTests(TestCase):
    """El cronograma continúa con el ciclo exacto del mes o, si tiene cambios a mano, el de sus últimos días."""

    def test_ciclo_exacto_de_todo_el_mes(self):
        from CoreFisica.asignaciones_meses import ciclo_de_continuacion
        ciclo = ['D', 'D', 'N', 'N', 'F', 'F']
        tokens = [ciclo[i % 6] for i in range(30)]
        self.assertEqual(ciclo_de_continuacion(tokens), (ciclo, 0))

    def test_con_cambios_a_mano_usa_el_ciclo_de_los_ultimos_dias(self):
        from CoreFisica.asignaciones_meses import ciclo_de_continuacion
        ciclo = ['D', 'D', 'N', 'N', 'F', 'F']
        tokens = ['V', 'V'] + [ciclo[(j - 2) % 6] for j in range(2, 30)]       # 2 días de vacaciones al inicio
        res = ciclo_de_continuacion(tokens)
        self.assertIsNotNone(res)
        c, ancla = res
        for g in range(30, 40):                                              # los días siguientes siguen el ciclo
            self.assertEqual(c[(g - ancla) % len(c)], ciclo[(g - 2) % 6])

    def test_sin_patron_claro_no_se_continua(self):
        from CoreFisica.asignaciones_meses import ciclo_de_continuacion
        irregular = ['D', 'N', 'F', 'V', 'D', 'D', 'N', 'F', 'X', 'D', 'N', 'F', 'N', 'D', 'F', 'D', 'D', 'N', 'V', 'F',
                     'X', 'N', 'N', 'D', 'F', 'D', 'V', 'N', 'F', 'D']
        self.assertIsNone(ciclo_de_continuacion(irregular))
        # Un mes de 24 horas todos los días ('V') es un ciclo válido de un solo turno.
        self.assertEqual(ciclo_de_continuacion(['V'] * 30), (['V'], 0))

    def test_con_vacios_no_se_inventa_nada(self):
        from CoreFisica.asignaciones_meses import ciclo_de_continuacion
        self.assertIsNone(ciclo_de_continuacion([''] * 30))


class CierreDeMesTests(TestCase):
    """El mes que falta del horizonte (actual + siguiente) se crea desde el estado FINAL del anterior."""
    ANIO, MES = 2031, 3

    def setUp(self):
        from CoreFisica.models import SacafrancoFila, VistaCanton
        self.SacafrancoFila = SacafrancoFila
        self.sig_anio, self.sig_mes = sumar_meses(self.ANIO, self.MES, 1)
        self.hoy = datetime.date(self.ANIO, self.MES, 15)
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        self.cli = cli
        self.inst = Instalacion.objects.create(cliente=cli, nombre='I')
        self.p1 = Puesto.objects.create(instalacion=self.inst, nombre='P1')
        self.p2 = Puesto.objects.create(instalacion=self.inst, nombre='P2')
        self.p3 = Puesto.objects.create(instalacion=self.inst, nombre='P3')
        self.p4 = Puesto.objects.create(instalacion=self.inst, nombre='P4')

        def mk(n, c, **kw):
            return Persona.objects.create(nombres=n, apellidos='X', cedula=c, tipo='FIJOS', **kw)

        self.A, self.B = mk('A', '0910000011'), mk('B', '0910000012')
        self.baja = mk('BAJA', '0910000013', estado_empleado='LIQUIDADO')
        self.n = ultimo_dia(self.ANIO, self.MES)
        self.ciclo = ['D', 'D', 'N', 'N', 'F', 'F']
        self.aA = self._asig(self.A, self.p1, 5)
        self.aB = self._asig(self.B, self.p2, 6)
        self.aBaja = self._asig(self.baja, self.p3, 7)
        self.vac = self._asig(None, self.p4, 8)
        escribir_mes(self.aA, self.ANIO, self.MES, [self.ciclo[i % 6] for i in range(self.n)])
        escribir_mes(self.vac, self.ANIO, self.MES, [self.ciclo[i % 6] for i in range(self.n)])   # la vacante también tiene cronograma
        escribir_mes(self.aB, self.ANIO, self.MES, ['V', 'V'] + [self.ciclo[(j - 2) % 6] for j in range(2, self.n)])
        self.vista = VistaCanton.objects.create(nombre='V1', tipo='canton')
        self.sa = Persona.objects.create(nombres='S', apellidos='SACA', cedula='0910000014', tipo='SACAFRANCO')
        self.sbaja = Persona.objects.create(nombres='SB', apellidos='SACA', cedula='0910000015', tipo='SACAFRANCO',
                                            estado_empleado='LIQUIDADO')
        SacafrancoFila.objects.create(mes=self.MES, anio=self.ANIO, persona=self.sa, orden=3, vista=self.vista)
        SacafrancoFila.objects.create(mes=self.MES, anio=self.ANIO, persona=self.sbaja, orden=4, vista=self.vista)

    def _asig(self, persona, puesto, orden):
        return Asignacion.objects.create(
            persona=persona, cliente=self.cli, instalacion=self.inst, puesto=puesto, mes=self.MES, anio=self.ANIO,
            orden=orden, estado='ACTIVO', recurring=True, es_hueca=persona is None,
            start_date=datetime.date(self.ANIO, self.MES, 1),
            end_date=datetime.date(self.ANIO, self.MES, self.n))

    def _sig(self, persona=None, puesto=None):
        qs = Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio)
        return qs.filter(persona=persona).first() if persona else qs.filter(persona__isnull=True, puesto=puesto).first()

    def _tokens_sig(self, asig):
        filas = {r.week_start: r for r in AsignacionSemanal.objects.filter(asignacion=asig)}
        return tokens_mes(filas, self.sig_anio, self.sig_mes)

    def test_crea_el_mes_siguiente_desde_el_final_del_actual(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        creados = asegurar_horizonte(hoy=self.hoy, meses_adelante=1)
        self.assertEqual([(a, m) for a, m, _ in creados], [(self.sig_anio, self.sig_mes)])
        a = self._sig(self.A)
        self.assertEqual((a.puesto_id, a.orden, a.estado), (self.p1.id, 5, 'ACTIVO'))
        self.assertEqual(self._sig(self.B).puesto_id, self.p2.id)
        self.assertIsNotNone(self._sig(puesto=self.p4))                         # la vacante también pasa
        self.assertIsNone(self._sig(self.baja))                                 # la persona desactivada NO

    def test_el_cronograma_continua_la_secuencia(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        asegurar_horizonte(hoy=self.hoy, meses_adelante=1)
        n_sig = ultimo_dia(self.sig_anio, self.sig_mes)
        self.assertEqual(self._tokens_sig(self._sig(self.A)), [self.ciclo[(self.n + i) % 6] for i in range(n_sig)])
        # B tuvo vacaciones a mano al inicio: continúa con la secuencia en que quedó el mes.
        self.assertEqual(self._tokens_sig(self._sig(self.B)), [self.ciclo[(self.n + i - 2) % 6] for i in range(n_sig)])

    def test_la_vacante_tambien_continua_su_cronograma(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        asegurar_horizonte(hoy=self.hoy, meses_adelante=1)
        n_sig = ultimo_dia(self.sig_anio, self.sig_mes)
        self.assertEqual(self._tokens_sig(self._sig(puesto=self.p4)),
                         [self.ciclo[(self.n + i) % 6] for i in range(n_sig)])

    def test_los_sacafranco_pasan_con_su_vista_y_orden_menos_los_desactivados(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        asegurar_horizonte(hoy=self.hoy, meses_adelante=1)
        f = self.SacafrancoFila.objects.filter(mes=self.sig_mes, anio=self.sig_anio, persona=self.sa).first()
        self.assertEqual((f.vista_id, f.orden), (self.vista.id, 3))
        self.assertFalse(self.SacafrancoFila.objects.filter(mes=self.sig_mes, anio=self.sig_anio, persona=self.sbaja).exists())

    def test_es_idempotente_y_no_toca_un_mes_que_ya_existe(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        asegurar_horizonte(hoy=self.hoy, meses_adelante=1)
        a = self._sig(self.A)
        Asignacion.objects.filter(pk=a.pk).update(orden=99)                      # alguien lo cambió en el mes nuevo
        self.assertEqual(asegurar_horizonte(hoy=self.hoy, meses_adelante=1), [])                   # segunda vez: no hace nada
        a.refresh_from_db()
        self.assertEqual(a.orden, 99)

    def test_si_falta_el_mes_actual_se_crea_desde_el_anterior(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        # "Hoy" ya es el mes siguiente, pero ese mes todavía no existe (falló el cierre de la noche anterior).
        hoy = datetime.date(self.sig_anio, self.sig_mes, 1)
        creados = asegurar_horizonte(hoy=hoy)
        meses_creados = [(a, m) for a, m, _ in creados]
        self.assertIn((self.sig_anio, self.sig_mes), meses_creados)         # el mes actual se creó
        a = self._sig(self.A)
        self.assertEqual((a.puesto_id, a.orden), (self.p1.id, 5))

    def test_sin_mes_base_no_crea_nada(self):
        from CoreFisica.asignaciones_meses import asegurar_horizonte
        self.assertEqual(asegurar_horizonte(hoy=datetime.date(2040, 1, 10), meses_adelante=1), [])

    def test_por_defecto_el_horizonte_es_solo_el_mes_actual(self):
        from CoreFisica.asignaciones_meses import MESES_ADELANTE, asegurar_horizonte
        self.assertEqual(MESES_ADELANTE, 0)
        self.assertEqual(asegurar_horizonte(hoy=self.hoy), [])            # el mes actual existe: nada que hacer
        self.assertFalse(Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio).exists())

    def test_el_comando_en_un_dia_normal_no_crea_el_mes_siguiente(self):
        out = StringIO()
        call_command('cierre_de_mes', '--hoy', '2031-03-15', stdout=out)
        self.assertFalse(Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio).exists())
        self.assertIn('solo se verifica', out.getvalue())

    def test_el_comando_el_ultimo_dia_genera_el_mes_siguiente(self):
        call_command('cierre_de_mes', '--hoy', '2031-03-31', '--dry-run', stdout=StringIO())
        self.assertFalse(Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio).exists())   # prueba: no guarda
        out = StringIO()
        call_command('cierre_de_mes', '--hoy', '2031-03-31', stdout=out)
        self.assertTrue(Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio).exists())
        self.assertIn('MES SIGUIENTE', out.getvalue())
        a = self._sig(self.A)
        self.assertEqual((a.puesto_id, a.orden), (self.p1.id, 5))
        n_sig = ultimo_dia(self.sig_anio, self.sig_mes)
        self.assertEqual(self._tokens_sig(a), [self.ciclo[(self.n + i) % 6] for i in range(n_sig)])

    def test_el_comando_con_siguiente_realinea_una_copia_vieja(self):
        call_command('cierre_de_mes', '--hoy', '2031-03-31', stdout=StringIO())
        a = self._sig(self.A)
        Asignacion.objects.filter(pk=a.pk).update(orden=99)                    # copia desactualizada
        call_command('cierre_de_mes', '--hoy', '2031-03-15', stdout=StringIO())   # dia normal: no la toca
        a.refresh_from_db()
        self.assertEqual(a.orden, 99)
        call_command('cierre_de_mes', '--hoy', '2031-03-15', '--siguiente', '--dry-run', stdout=StringIO())
        a.refresh_from_db()
        self.assertEqual(a.orden, 99)                                          # en prueba no cambia nada
        call_command('cierre_de_mes', '--hoy', '2031-03-15', '--siguiente', stdout=StringIO())
        a.refresh_from_db()
        self.assertEqual(a.orden, 5)

    def test_el_cierre_deja_el_mes_siguiente_igual_al_final_del_actual_sin_restos_de_una_copia_vieja(self):
        """Una persona protegida (retén) y un sacafranco vacío que SOLO traía la copia vieja del mes
        siguiente se quitan; las vacantes quedan con el mismo orden que en el mes que termina."""
        from CoreFisica.models import SacafrancoFila
        call_command('cierre_de_mes', '--hoy', '2031-03-31', stdout=StringIO())      # crea el mes siguiente
        reten = Persona.objects.create(nombres='R', apellidos='RETEN', cedula='0910000020', tipo='RETEN')
        sig_p = Puesto.objects.get(pk=self.p4.pk)
        Asignacion.objects.create(
            persona=reten, cliente=self.cli, instalacion=self.inst, puesto=sig_p, mes=self.sig_mes, anio=self.sig_anio,
            orden=77, estado='ACTIVO', recurring=True,
            start_date=datetime.date(self.sig_anio, self.sig_mes, 1), end_date=datetime.date(self.sig_anio, self.sig_mes, 28))
        SacafrancoFila.objects.create(mes=self.sig_mes, anio=self.sig_anio, persona=None, orden=500, vista=self.vista)
        Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio, persona__isnull=True, puesto=self.p4).update(orden=999)
        call_command('cierre_de_mes', '--hoy', '2031-03-31', stdout=StringIO())      # el cierre vuelve a alinear
        sig = Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio, estado='ACTIVO')
        self.assertFalse(sig.filter(persona=reten).exists())                          # el retén de la copia vieja ya no está
        self.assertEqual(sig.get(persona__isnull=True, puesto=self.p4).orden, self.vac.orden)   # la vacante, con su orden
        self.assertFalse(SacafrancoFila.objects.filter(mes=self.sig_mes, anio=self.sig_anio, orden=500).exists())

    def test_el_cierre_copia_los_sacafranco_vacios_del_mes_que_termina(self):
        from CoreFisica.models import SacafrancoFila
        SacafrancoFila.objects.create(mes=self.MES, anio=self.ANIO, persona=None, orden=9, vista=self.vista)
        call_command('cierre_de_mes', '--hoy', '2031-03-31', stdout=StringIO())
        call_command('cierre_de_mes', '--hoy', '2031-03-31', stdout=StringIO())      # repetir no duplica
        vac = SacafrancoFila.objects.filter(mes=self.sig_mes, anio=self.sig_anio, persona__isnull=True)
        self.assertEqual([(f.orden, f.vista_id) for f in vac], [(9, self.vista.id)])


class ImportacionHorizonteTests(TestCase):
    def test_por_defecto_proyecta_solo_el_mes_importado(self):
        from types import SimpleNamespace
        from CoreFisica.views.importar_puestos_asignaciones import _meses_proyeccion
        self.assertEqual(_meses_proyeccion(SimpleNamespace(GET={}, POST={})), 0)
        self.assertEqual(_meses_proyeccion(SimpleNamespace(GET={'meses': '0'}, POST={})), 0)
        self.assertEqual(_meses_proyeccion(SimpleNamespace(GET={'meses': '3'}, POST={})), 3)


class PrepararMesSiguienteTests(TestCase):
    """Pasar al mes siguiente desde la pantalla lo arma desde el mes actual (sin preguntar)."""

    def setUp(self):
        from CoreFisica.asignaciones_meses import sumar_meses, ultimo_dia
        User.objects.create_superuser(username='pm_user', email='e@e.com', password='PmPass123!')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'pm_user', 'PmPass123!')}"}
        User.objects.create_user(username='pm_lee', email='l@e.com', password='PmPass123!')
        self.hoy = timezone.localdate()
        self.sig_anio, self.sig_mes = sumar_meses(self.hoy.year, self.hoy.month, 1)
        self.otro_anio, self.otro_mes = sumar_meses(self.hoy.year, self.hoy.month, 2)
        cli = Cliente.objects.create(razon_social='C SA', nombre_comercial='C')
        inst = Instalacion.objects.create(cliente=cli, nombre='I')
        puesto = Puesto.objects.create(instalacion=inst, nombre='P')
        self.persona = Persona.objects.create(nombres='A', apellidos='A', cedula='0910000030', tipo='FIJOS')
        self.asig = Asignacion.objects.create(
            persona=self.persona, cliente=cli, instalacion=inst, puesto=puesto, mes=self.hoy.month,
            anio=self.hoy.year, orden=7, estado='ACTIVO', recurring=True, start_date=self.hoy.replace(day=1),
            end_date=self.hoy.replace(day=ultimo_dia(self.hoy.year, self.hoy.month)))

    def _llamar(self, mes, anio, auth=None):
        return self.client.post('/api/asignaciones/preparar-mes-siguiente/', data=json.dumps({'mes': mes, 'anio': anio}),
                                content_type='application/json', **(auth or self.auth))

    def _sig(self):
        return Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio, persona=self.persona).first()

    def test_arma_el_mes_siguiente_y_lo_vuelve_a_armar_cada_vez(self):
        r = self._llamar(self.sig_mes, self.sig_anio)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()['preparado'])
        self.assertEqual(self._sig().orden, 7)
        Asignacion.objects.filter(pk=self.asig.pk).update(orden=3)          # el mes actual cambió
        self._llamar(self.sig_mes, self.sig_anio)                           # vuelve a pasar al mes siguiente
        self.assertEqual(self._sig().orden, 3)

    def test_otro_mes_no_se_toca(self):
        r = self._llamar(self.otro_mes, self.otro_anio)
        self.assertFalse(r.json()['preparado'])
        self.assertFalse(Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio).exists())
        self.assertFalse(Asignacion.objects.filter(mes=self.otro_mes, anio=self.otro_anio).exists())

    def test_sin_permiso_de_editar_no_hace_nada(self):
        tok = {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, 'pm_lee', 'PmPass123!')}"}
        self.assertEqual(self._llamar(self.sig_mes, self.sig_anio, tok).status_code, 403)
        self.assertFalse(Asignacion.objects.filter(mes=self.sig_mes, anio=self.sig_anio).exists())
