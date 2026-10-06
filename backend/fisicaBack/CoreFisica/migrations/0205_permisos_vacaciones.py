from django.db import migrations

# Reporte de Vacaciones: ahora el servidor exige permisos. Para que nadie pierda lo que debe tener:
#   - COORDINADOR_GALO (ggomez): crea, edita, elimina y ve.
#   - CONSOLA y ADMINISTRADOR: solo ven.
#   - Asistentes_Fisica: solo ven (se le quita "crear").
# Los superusuarios siguen con acceso a todo. Si un grupo no existe (otra base), se omite.
VER = 'view_reportevacaciones'
TODOS = ['add_reportevacaciones', 'change_reportevacaciones', 'delete_reportevacaciones', VER]
SOLO_LECTURA = {'CONSOLA', 'ADMINISTRADOR', 'Asistentes_Fisica'}
EDITAN = {'COORDINADOR_GALO'}


def asignar(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    perms = {p.codename: p for p in Permission.objects.filter(
        content_type__app_label='CoreFisica', codename__in=TODOS)}
    if VER not in perms:
        return                      # base nueva: los permisos aún no existen (se crean después)
    for g in Group.objects.filter(name__in=SOLO_LECTURA | EDITAN):
        if g.name in EDITAN:
            g.permissions.add(*[perms[c] for c in TODOS if c in perms])
        else:
            g.permissions.add(perms[VER])
            g.permissions.remove(*[perms[c] for c in TODOS if c != VER and c in perms])


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0204_visita_supervisor'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(asignar, migrations.RunPython.noop),
    ]
