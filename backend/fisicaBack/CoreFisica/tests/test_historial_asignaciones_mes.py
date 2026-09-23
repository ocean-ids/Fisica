"""Historial del mes en Asignaciones: los movimientos (crear/editar/eliminar) de las
asignaciones de un mes salen agrupados por día, tomados del AuditLog."""
import json
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

import datetime
from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Persona, Asignacion, AuditLog, AsignacionPersonaPeriodo,
    AsignacionCalendarioLog, AsignacionSemanal,
)


def _login_token(client, username, password):
    resp = client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                       content_type='application/json')
    return resp.json().get('access')


class HistorialAsignacionesMesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='hm_user', password='HmPass123!', email='h@e.com')
        self.access = _login_token(self.client, 'hm_user', 'HmPass123!')
        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year
        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.inst = Instalacion.objects.create(cliente=self.cliente)
        self.puesto = Puesto.objects.create(instalacion=self.inst, nombre='P1')
        self.persona = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111', tipo='FIJOS')
        # Crear (CREATE) y luego editar (UPDATE) -> dos movimientos en el AuditLog.
        self.asig = Asignacion.objects.create(
            persona=self.persona, cliente=self.cliente, instalacion=self.inst,
            puesto=self.puesto, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )
        self.asig.orden = 5
        self.asig.save()

    def test_historial_agrupa_por_dia(self):
        # Confirmar que el AuditLog registró los movimientos de esta asignación.
        self.assertTrue(
            AuditLog.objects.filter(modelo='Asignacion', objeto_repr__contains=f"({self.mes}/{self.anio})").exists()
        )

        r = self.client.get(f'/api/asignaciones/historial-mes/{self.mes}/{self.anio}/',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['mes'], self.mes)
        self.assertGreaterEqual(body['total'], 1)
        self.assertTrue(len(body['dias']) >= 1)
        # El día de hoy debe tener items con hora/usuario/accion/detalle.
        hoy_iso = timezone.localdate().isoformat()
        dia_hoy = next((d for d in body['dias'] if d['fecha'] == hoy_iso), None)
        self.assertIsNotNone(dia_hoy)
        item = dia_hoy['items'][0]
        for k in ('hora', 'usuario', 'accion', 'accion_key', 'puesto', 'persona'):
            self.assertIn(k, item)
        # Campos estructurados: el puesto y la persona salen en columnas separadas.
        self.assertTrue(any(it['puesto'] == 'P1' for it in dia_hoy['items']))

    def test_cambio_de_guardia_muestra_antes_y_despues(self):
        # Períodos: ANA (titular) hasta el 14; BETO desde el 15 -> cambio "ANA → BETO".
        beto = Persona.objects.create(nombres='BETO', apellidos='DOS', cedula='0222222222', tipo='FIJOS')
        self.asig.persona = beto
        self.asig.save()
        dia15 = datetime.date(self.anio, self.mes, 15)
        AsignacionPersonaPeriodo.objects.create(
            asignacion=self.asig, persona=self.persona,
            desde=datetime.date(self.anio, self.mes, 1), hasta=dia15 - datetime.timedelta(days=1),
        )
        AsignacionPersonaPeriodo.objects.create(
            asignacion=self.asig, persona=beto, desde=dia15, hasta=None,
        )

        r = self.client.get(f'/api/asignaciones/historial-mes/{self.mes}/{self.anio}/',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        body = r.json()
        dia = next((d for d in body['dias'] if d['fecha'] == dia15.isoformat()), None)
        self.assertIsNotNone(dia)
        cambio = next((it for it in dia['items'] if it['accion_key'] == 'CAMBIO'), None)
        self.assertIsNotNone(cambio)
        self.assertEqual(cambio['puesto'], 'P1')
        self.assertEqual(cambio['antes'], 'UNO ANA')     # quién estaba antes
        self.assertEqual(cambio['despues'], 'DOS BETO')   # quién quedó después

    def test_cambio_de_calendario_aparece(self):
        # Un cambio de calendario (token D/N/F por día) sale como acción "Calendario" con
        # su valor anterior y nuevo.
        AsignacionCalendarioLog.objects.create(
            asignacion=self.asig, week_start=datetime.date(self.anio, self.mes, 1),
            dia='wed', valor_anterior='F', valor_nuevo='D',
        )
        r = self.client.get(f'/api/asignaciones/historial-mes/{self.mes}/{self.anio}/',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        # Los cambios de calendario NO deben aparecer en la lista principal (van en el
        # cronograma del puesto, aparte).
        for d in r.json()['dias']:
            for it in d['items']:
                self.assertNotEqual(it['accion_key'], 'CALENDARIO')

    def test_cronograma_reconstruido_a_fecha(self):
        # Estado ACTUAL del calendario: el día 10 tiene 'D'. Hubo un cambio HOY de F -> D.
        target = datetime.date(self.anio, self.mes, 10)
        field = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}[target.weekday()]
        ws_iso = target - datetime.timedelta(days=target.weekday())
        AsignacionSemanal.objects.create(asignacion=self.asig, puesto=self.puesto,
                                         week_start=ws_iso, **{field: 'D'})
        AsignacionCalendarioLog.objects.create(asignacion=self.asig, week_start=ws_iso,
                                               dia=field, valor_anterior='F', valor_nuevo='D')

        # Reconstruido a HOY: el día 10 muestra 'D' y sale marcado como cambiado.
        r = self.client.get(f'/api/asignaciones/{self.asig.id}/cronograma-reconstruido/',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(r.status_code, 200)
        body = r.json()
        dia10 = next((d for d in body['dias'] if d['fecha'] == target.isoformat()), None)
        self.assertIsNotNone(dia10)
        self.assertEqual(dia10['token'], 'D')
        self.assertTrue(dia10['cambiado'])
        # El mes completo sale (28-31 días).
        self.assertGreaterEqual(len(body['dias']), 28)

        # Reconstruido a AYER (antes del cambio de hoy): el día 10 vuelve a 'F', sin marcar.
        ayer = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        r2 = self.client.get(f'/api/asignaciones/{self.asig.id}/cronograma-reconstruido/?hasta={ayer}',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        dia10b = next((d for d in r2.json()['dias'] if d['fecha'] == target.isoformat()), None)
        self.assertEqual(dia10b['token'], 'F')
        self.assertFalse(dia10b['cambiado'])

    def test_otro_mes_no_trae_movimientos(self):
        # Un mes sin asignaciones no devuelve movimientos.
        otro_mes = 1 if self.mes != 1 else 2
        r = self.client.get(f'/api/asignaciones/historial-mes/{otro_mes}/{self.anio + 5}/',
                            HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['total'], 0)
