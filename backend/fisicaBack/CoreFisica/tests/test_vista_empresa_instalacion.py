"""La exclusion de vistas por canton es POR INSTALACION cuando la vista de
empresa define instalaciones especificas: una instalacion del cliente que NO
este en la vista de empresa sigue apareciendo en su canton; la que SI este se
excluye. Si la vista de empresa no define instalaciones ("toda la empresa"),
se excluye el cliente completo (comportamiento anterior)."""
import json
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from CoreFisica.models import (
    Cliente, Instalacion, Puesto, Horario, Persona, Asignacion, VistaCanton,
    Provincia, Canton,
)


def _login(client, u, p):
    r = client.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                    content_type='application/json')
    return r.json().get('access')


class VistaEmpresaPorInstalacionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ve_user', password='VePass123!', email='ve@e.com')
        self.user.user_permissions.add(Permission.objects.get(codename='view_asignacion'))
        self.access = _login(self.client, 've_user', 'VePass123!')

        self.prov, _ = Provincia.objects.get_or_create(nombre='GUAYAS')
        self.cA, _ = Canton.objects.get_or_create(nombre='GUAYAQUIL', provincia=self.prov)
        self.cB, _ = Canton.objects.get_or_create(nombre='DURAN', provincia=self.prov)

        self.cli = Cliente.objects.create(razon_social='CX', nombre_comercial='CX')
        self.instA = Instalacion.objects.create(cliente=self.cli, canton=self.cA, nombre='INST A GYE')
        self.instB = Instalacion.objects.create(cliente=self.cli, canton=self.cB, nombre='INST B DURAN')
        self.pA = Puesto.objects.create(instalacion=self.instA, nombre='PA')
        self.pB = Puesto.objects.create(instalacion=self.instB, nombre='PB')
        self.hor = Horario.objects.create(hora_ingreso='08:00', hora_salida='20:00')
        self.perA = Persona.objects.create(nombres='A', apellidos='AA', cedula='0900000001', tipo='FIJOS', estado_empleado='ACTIVO')
        self.perB = Persona.objects.create(nombres='B', apellidos='BB', cedula='0900000002', tipo='FIJOS', estado_empleado='ACTIVO')

        self.mes, self.anio = 7, 2026
        self.aA = Asignacion.objects.create(persona=self.perA, cliente=self.cli, instalacion=self.instA,
                                            puesto=self.pA, horario=self.hor, mes=self.mes, anio=self.anio, estado='ACTIVO')
        self.aB = Asignacion.objects.create(persona=self.perB, cliente=self.cli, instalacion=self.instB,
                                            puesto=self.pB, horario=self.hor, mes=self.mes, anio=self.anio, estado='ACTIVO')

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access}'}

    def _ids_en_canton_view(self):
        url = f'/api/asignaciones/{self.mes}/{self.anio}/?canton_ids={self.cA.id},{self.cB.id}'
        r = self.client.get(url, **self._auth())
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        results = data.get('results', []) if isinstance(data, dict) else data
        return {row.get('id') for row in results}

    def test_vista_empresa_con_instalacion_excluye_solo_esa(self):
        # Vista de empresa que incluye SOLO instB
        VistaCanton.objects.create(nombre='VE', tipo='cliente', clientes=[self.cli.id], instalaciones=[self.instB.id])
        ids = self._ids_en_canton_view()
        self.assertIn(self.aA.id, ids, 'INST A (no está en la vista) debe salir en su cantón')
        self.assertNotIn(self.aB.id, ids, 'INST B (sí está en la vista) NO debe salir en el cantón')

    def test_vista_empresa_sin_instalaciones_excluye_cliente_completo(self):
        # Vista de empresa sin instalaciones = toda la empresa -> excluye ambas
        VistaCanton.objects.create(nombre='VE', tipo='cliente', clientes=[self.cli.id], instalaciones=[])
        ids = self._ids_en_canton_view()
        self.assertNotIn(self.aA.id, ids, 'toda la empresa: INST A excluida')
        self.assertNotIn(self.aB.id, ids, 'toda la empresa: INST B excluida')

    def test_sin_vista_empresa_todo_sale(self):
        ids = self._ids_en_canton_view()
        self.assertIn(self.aA.id, ids)
        self.assertIn(self.aB.id, ids)
