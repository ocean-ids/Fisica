"""La campanita (puestos sin persona) tiene permiso propio: view_notificacion_vacantes.
El login lo devuelve solo a quien lo tiene; view_asignacion ya no la incluye."""
import json

from django.contrib.auth.models import Permission, User
from django.test import TestCase


class PermisoNotificacionVacantesTests(TestCase):
    def _perms_login(self, user):
        r = self.client.post('/api/login/', data=json.dumps({'username': user.username, 'password': 'Pass12345!'}),
                             content_type='application/json')
        return r.json()['user']['permissions']

    def test_asignaciones_sin_campanita(self):
        u = User.objects.create_user(username='solo_asig', password='Pass12345!')
        u.user_permissions.add(Permission.objects.get(codename='view_asignacion'))
        perms = self._perms_login(u)
        self.assertIn('CoreFisica.view_asignacion', perms)
        self.assertNotIn('CoreFisica.view_notificacion_vacantes', perms)

    def test_con_permiso_de_campanita(self):
        u = User.objects.create_user(username='con_campana', password='Pass12345!')
        u.user_permissions.add(Permission.objects.get(codename='view_asignacion'),
                               Permission.objects.get(codename='view_notificacion_vacantes'))
        self.assertIn('CoreFisica.view_notificacion_vacantes', self._perms_login(u))
