"""Al reasignar (editar) una persona que tiene una asignación INACTIVA oculta del mismo
mes, se debe liberar esa asignación en vez de violar la unicidad (persona, mes, anio)."""
import json
from django.test import TestCase
from django.contrib.auth.models import User

from CoreFisica.models import Cliente, Instalacion, Puesto, Persona, Asignacion


def _login_token(client, username, password):
    resp = client.post('/api/login/', data=json.dumps({'username': username, 'password': password}),
                       content_type='application/json')
    return resp.json().get('access')


class ReasignarInactivaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='rea_user', password='ReaPass123!', email='r@e.com')
        self.access = _login_token(self.client, 'rea_user', 'ReaPass123!')
        self.mes, self.anio = 9, 2026

        self.cliente = Cliente.objects.create(razon_social='C', nombre_comercial='NC')
        self.inst = Instalacion.objects.create(cliente=self.cliente)
        self.puesto_x = Puesto.objects.create(instalacion=self.inst, nombre='PX')
        self.puesto_cen = Puesto.objects.create(instalacion=self.inst, nombre='CEN URDESA')

        self.b = Persona.objects.create(nombres='ADRIANO', apellidos='SANMARTIN QUEZADA',
                                        cedula='0999999999', tipo='FIJOS')
        # Asignación INACTIVA "oculta" de B en 9/2026 (el frontend la ve "Disponible").
        Asignacion.objects.create(persona=self.b, cliente=self.cliente, instalacion=self.inst,
                                  puesto=self.puesto_x, mes=self.mes, anio=self.anio, estado='INACTIVO')
        # Asignación destino (CEN URDESA) actualmente HUECA.
        self.asig_cen = Asignacion.objects.create(
            persona=None, es_hueca=True, cliente=self.cliente, instalacion=self.inst,
            puesto=self.puesto_cen, mes=self.mes, anio=self.anio, estado='ACTIVO',
        )

    def test_editar_asigna_pese_a_inactiva_oculta(self):
        resp = self.client.put(
            f'/api/editar-servicio/{self.asig_cen.id}/',
            data=json.dumps({'persona': self.b.id}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        )
        # Antes fallaba con 400 (unique violation). Ahora debe asignar bien.
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        self.asig_cen.refresh_from_db()
        self.assertEqual(self.asig_cen.persona_id, self.b.id)
        # La asignación inactiva quedó liberada (persona=None), sin duplicar la unicidad.
        inactiva = Asignacion.objects.get(puesto=self.puesto_x, mes=self.mes, anio=self.anio)
        self.assertIsNone(inactiva.persona_id)
