"""Audit trail automático.

Registra en `AuditLog` las operaciones de creación, edición y eliminación de las
entidades de negocio, usando las señales post_save / post_delete. El usuario y la
IP se obtienen del request actual (ver audit.py).

Se excluyen a propósito:
  - AuditLog (evita recursión).
  - AsignacionSemanal / SacafrancoFilaSemanal: cambios de calendario de muy alta
    frecuencia, ya cubiertos por AsignacionCalendarioLog.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .audit import get_current_user, get_current_ip
from .models import (
    AuditLog,
    Cliente, Instalacion, Puesto, Persona, Asignacion, Horario,
    Consolidado, ReporteAsistencia, SacafrancoFila, VistaCanton,
    NovedadPuesto,
)

# Modelos auditados (create/update/delete).
AUDITED_MODELS = [
    Cliente, Instalacion, Puesto, Persona, Asignacion, Horario,
    Consolidado, ReporteAsistencia, SacafrancoFila, VistaCanton,
    NovedadPuesto,
]


def _registrar(accion, instance):
    user = get_current_user()
    try:
        repr_str = str(instance)
    except Exception:
        repr_str = ''
    AuditLog.objects.create(
        usuario=user,
        usuario_str=(getattr(user, 'username', '') or 'sistema'),
        accion=accion,
        modelo=type(instance).__name__,
        objeto_id=str(getattr(instance, 'pk', '') or ''),
        objeto_repr=repr_str[:255],
        ip=get_current_ip(),
    )


@receiver(post_save)
def _audit_post_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    _registrar('CREATE' if created else 'UPDATE', instance)


@receiver(post_delete)
def _audit_post_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    _registrar('DELETE', instance)
