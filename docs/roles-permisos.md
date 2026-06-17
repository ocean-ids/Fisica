# Roles y permisos — Seguridad Física

La autorización usa el sistema de **permisos de Django**. Cada endpoint exige
`IsAuthenticated` y valida un permiso concreto con `request.user.has_perm('CoreFisica.<accion>_<modelo>')`
(p. ej. `view_asignacion`, `change_consolidado`, `export_reporteasistencia`).

## Roles (grupos)

Se crean con un comando idempotente:

```bash
python manage.py crear_grupos
# o en el servidor:
docker compose exec backend python manage.py crear_grupos
```

| Rol | Puede | No puede | Permisos |
|-----|-------|----------|----------|
| **ADMINISTRADOR** | Todo: crear, editar, ver, **eliminar**, exportar, importar | — | 106 |
| **OPERADOR** | Crear, editar, ver, exportar, importar (operación diaria) | **Eliminar** | 81 |
| **CONSULTA** | Ver y exportar (solo lectura) | Crear/editar/eliminar/importar | 29 |

> Los números pueden variar al agregar modelos nuevos; el comando los recalcula.

## Asignar un usuario a un rol

Desde el panel admin de Django (`/admin/`) → Usuarios → editar usuario → **Grupos**,
o por código:

```python
from django.contrib.auth.models import Group
user.groups.add(Group.objects.get(name='OPERADOR'))
```

Un **superusuario** (`createsuperuser`) tiene todos los permisos sin pertenecer a un grupo.

## Nota sobre `UserProfile.cargo`

El campo `cargo` del perfil es **informativo** (etiqueta del puesto del usuario) y no
otorga permisos por sí mismo. La autorización efectiva proviene de los grupos/permisos
de Django descritos arriba.

## Convención de permisos por acción

- `view_*`   → leer / listar / descargar (lectura).
- `add_*`    → crear.
- `change_*` → editar.
- `delete_*` → eliminar.
- `export_*` / `import_*` → exportar a Excel / importar desde Excel.
