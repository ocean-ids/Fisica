"""Un SacafrancoFila sellado a una VISTA se muestra SOLO en esa vista, aunque otra
vista comparta el mismo cantón. Evita la duplicación del sacafranco entre vistas."""
import json
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from CoreFisica.models import (
    Provincia, Canton, Persona, VistaCanton, SacafrancoFila,
)


def _login_token(client, username, password):
    resp = client.post(
        '/api/login/',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json',
    )
    return resp.json().get('access')


class SacafrancoVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='saca_user', password='SacaPass123!', email='saca@example.com'
        )
        self.access = _login_token(self.client, 'saca_user', 'SacaPass123!')

        hoy = timezone.localdate()
        self.mes, self.anio = hoy.month, hoy.year

        self.prov, _ = Provincia.objects.get_or_create(nombre='ZZ_PROV_TEST_SACA')
        self.canton = Canton.objects.create(nombre='ZZ_CANTON_A', provincia=self.prov)
        self.otro = Canton.objects.create(nombre='ZZ_CANTON_B', provincia=self.prov)

        self.p1 = Persona.objects.create(nombres='ANA', apellidos='UNO', cedula='0111111111',
                                         tipo='SACAFRANCO', canton=self.canton)
        self.p2 = Persona.objects.create(nombres='BETO', apellidos='DOS', cedula='0222222222',
                                         tipo='SACAFRANCO', canton=self.canton)

        # Dos vistas que COMPARTEN el mismo cantón (GUAYAQUIL).
        self.vistaA = VistaCanton.objects.create(nombre='VISTA A', tipo='canton',
                                                 cantones=[self.canton.id])
        self.vistaB = VistaCanton.objects.create(nombre='VISTA B', tipo='canton',
                                                 cantones=[self.canton.id, self.otro.id])

        # Sacafranco SELLADO a la vista A (cantón GUAYAQUIL).
        self.fila_A = SacafrancoFila.objects.create(
            persona=self.p1, mes=self.mes, anio=self.anio,
            cantones=[self.canton.id], vista=self.vistaA,
        )
        # Sacafranco SIN vista (legado): debe salir por su cantón en ambas vistas.
        self.fila_legado = SacafrancoFila.objects.create(
            persona=self.p2, mes=self.mes, anio=self.anio,
            cantones=[self.canton.id], vista=None,
        )

    def _ids(self, params):
        resp = self.client.get(
            '/api/sacafranco-filas/', {'mes': self.mes, 'anio': self.anio, **params},
            HTTP_AUTHORIZATION=f'Bearer {self.access}',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        rows = data.get('results', data) if isinstance(data, dict) else data
        return {r['id'] for r in rows}

    def test_fila_sellada_sale_en_su_vista(self):
        ids = self._ids({'canton_ids': str(self.canton.id), 'vista_id': self.vistaA.id})
        self.assertIn(self.fila_A.id, ids, 'La fila sellada debe salir en su vista (A)')

    def test_fila_sellada_NO_sale_en_otra_vista(self):
        # Vista B comparte el cantón GUAYAQUIL, pero la fila es de la vista A -> NO debe salir.
        ids = self._ids({'canton_ids': str(self.canton.id), 'vista_id': self.vistaB.id})
        self.assertNotIn(self.fila_A.id, ids,
                         'La fila de la vista A NO debe aparecer en la vista B')

    def test_fila_legado_sale_en_ambas_vistas(self):
        # Sin vista (vista=None): sigue el scope por cantón -> aparece en A y en B.
        ids_a = self._ids({'canton_ids': str(self.canton.id), 'vista_id': self.vistaA.id})
        ids_b = self._ids({'canton_ids': str(self.canton.id), 'vista_id': self.vistaB.id})
        self.assertIn(self.fila_legado.id, ids_a)
        self.assertIn(self.fila_legado.id, ids_b)

    def test_sin_vista_id_no_rompe_compatibilidad(self):
        # Sin vista_id: ambas filas salen por su cantón (comportamiento anterior).
        ids = self._ids({'canton_ids': str(self.canton.id)})
        self.assertIn(self.fila_A.id, ids)
        self.assertIn(self.fila_legado.id, ids)
