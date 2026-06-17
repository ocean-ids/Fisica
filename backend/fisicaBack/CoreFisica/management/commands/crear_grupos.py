"""Crea los grupos de roles iniciales con sus permisos.

Roles:
  - ADMINISTRADOR : todos los permisos de la app CoreFisica.
  - OPERADOR      : crear/editar/ver/eliminar + exportar/importar (operación diaria).
  - CONSULTA      : solo ver (read-only) + exportar.

Uso:
    python manage.py crear_grupos
    docker compose exec backend python manage.py crear_grupos

Idempotente: se puede correr varias veces; reasigna los permisos sin duplicar grupos.
Asignar un usuario a un grupo se hace desde el panel de administración de Django
(o `user.groups.add(grupo)`).
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea/actualiza los grupos de roles (ADMINISTRADOR, OPERADOR, CONSULTA) con sus permisos.'

    def handle(self, *args, **options):
        perms = list(Permission.objects.filter(content_type__app_label='CoreFisica'))
        if not perms:
            self.stdout.write(self.style.WARNING(
                'No hay permisos de CoreFisica. Corre primero las migraciones.'))
            return

        def by_prefixes(prefixes):
            return [p for p in perms if any(p.codename.startswith(pre) for pre in prefixes)]

        roles = {
            'ADMINISTRADOR': perms,  # todos (incluye eliminar)
            'OPERADOR': by_prefixes(['add_', 'change_', 'view_', 'export_', 'import_']),  # sin eliminar
            'CONSULTA': by_prefixes(['view_', 'export_']),  # solo lectura + exportar
        }

        for nombre, permisos in roles.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            grupo.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS(
                f'Grupo "{nombre}": {len(permisos)} permisos asignados.'))

        self.stdout.write(self.style.SUCCESS('Roles listos.'))
