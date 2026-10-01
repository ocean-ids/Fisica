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
    def test_editar_en_el_mes_actual_se_pasa_a_los_meses_siguientes(self):
        self._armar_meses()
        alinear_meses(self.mes, self.anio)                                 # parten alineados
        # Se cambia la persona del puesto P1 en el mes actual: A sale, C entra.
        r = self.client.put(f'/api/editar-servicio/{self.bA.id}/',
                            data=json.dumps({'persona': self.C.id}), content_type='application/json', **self.auth)
        self.assertEqual(r.status_code, 200, r.content)
        # C debería quedar en P1 el mes siguiente; A (que ya no está en el mes base) se desactiva.
        self.assertEqual(self._siguiente(self.C).puesto_id, self.p1.id)
        self.assertEqual(self._siguiente(self.A).estado, 'INACTIVO')

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

    def test_eliminar_en_el_mes_actual_desactiva_la_fila_del_mes_siguiente(self):
        self._armar_meses()
        alinear_meses(self.mes, self.anio)
        r = self.client.delete(f'/api/eliminar-asignacion/{self.bB.id}/', **self.auth)
        self.assertIn(r.status_code, (200, 204), r.content)
        self.assertEqual(self._siguiente(self.B).estado, 'INACTIVO')


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
