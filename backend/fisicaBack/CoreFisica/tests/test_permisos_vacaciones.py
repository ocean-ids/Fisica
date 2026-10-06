"""Reporte de Vacaciones: solo quien tiene permiso edita; los demás solo ven."""
import importlib
import json

from django.apps import apps as django_apps
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase


def _login(c, u, p):
    return c.post('/api/login/', data=json.dumps({'username': u, 'password': p}),
                  content_type='application/json').json().get('access')


class PermisosVacacionesTests(TestCase):
    def _usuario(self, nombre, *perms):
        u = User.objects.create_user(username=nombre, password='Pass12345!', email=f'{nombre}@e.com')
        for c in perms:
            u.user_permissions.add(Permission.objects.get(codename=c))
        return {'HTTP_AUTHORIZATION': f"Bearer {_login(self.client, nombre, 'Pass12345!')}"}

    def _crear(self, auth):
        body = {'cliente': 'X', 'fecha_desde': '2026-10-01', 'fecha_hasta': '2026-10-10', 'dias': 10}
        return self.client.post('/api/reporte-vacaciones/crear/', data=json.dumps(body),
                                content_type='application/json', **auth)

    def test_solo_lectura_ve_pero_no_crea_ni_edita_ni_borra(self):
        editor = self._usuario('editor', 'view_reportevacaciones', 'add_reportevacaciones',
                               'change_reportevacaciones', 'delete_reportevacaciones')
        rid = self._crear(editor).json()['id']
        lector = self._usuario('lector', 'view_reportevacaciones')
        self.assertEqual(self.client.get('/api/reporte-vacaciones/', **lector).status_code, 200)
        self.assertEqual(self.client.get('/api/reporte-vacaciones/exportar-excel/', **lector).status_code, 200)
        self.assertEqual(self._crear(lector).status_code, 403)
        self.assertEqual(self.client.put(f'/api/reporte-vacaciones/{rid}/', data=json.dumps({'cliente': 'Y'}),
                                         content_type='application/json', **lector).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/reporte-vacaciones/{rid}/eliminar/', **lector).status_code, 403)

    def test_sin_permiso_no_ve(self):
        nadie = self._usuario('nadie')
        self.assertEqual(self.client.get('/api/reporte-vacaciones/', **nadie).status_code, 403)

    def test_el_editor_si_edita_y_borra(self):
        editor = self._usuario('editor2', 'view_reportevacaciones', 'add_reportevacaciones',
                               'change_reportevacaciones', 'delete_reportevacaciones')
        rid = self._crear(editor).json()['id']
        self.assertEqual(self.client.put(f'/api/reporte-vacaciones/{rid}/', data=json.dumps({'cliente': 'Y'}),
                                         content_type='application/json', **editor).status_code, 200)
        self.assertEqual(self.client.delete(f'/api/reporte-vacaciones/{rid}/eliminar/', **editor).status_code, 204)

    def test_la_migracion_asigna_los_permisos_por_grupo(self):
        consola = Group.objects.create(name='CONSOLA')
        galo = Group.objects.create(name='COORDINADOR_GALO')
        asist = Group.objects.create(name='Asistentes_Fisica')
        asist.permissions.add(Permission.objects.get(codename='add_reportevacaciones'))
        mig = importlib.import_module('CoreFisica.migrations.0205_permisos_vacaciones')
        mig.asignar(django_apps, None)
        cod = lambda g: set(g.permissions.filter(codename__endswith='reportevacaciones').values_list('codename', flat=True))
        self.assertEqual(cod(consola), {'view_reportevacaciones'})
        self.assertEqual(cod(asist), {'view_reportevacaciones'})                       # se le quitó "crear"
        self.assertEqual(cod(galo), {'view_reportevacaciones', 'add_reportevacaciones',
                                     'change_reportevacaciones', 'delete_reportevacaciones'})
