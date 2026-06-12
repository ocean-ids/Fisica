# ADR 0004 — Audit trail vía señales + middleware

**Estado:** Aceptado

## Contexto

Se necesitaba un registro de quién crea/edita/elimina las entidades de negocio
(trazabilidad). El reto con DRF + JWT: las señales de Django (`post_save`,
`post_delete`) no tienen acceso al `request`, por lo que no conocen al usuario.

## Decisión

- Modelo `AuditLog` (usuario, acción, modelo, id de objeto, repr, IP, fecha).
- Middleware (`CoreFisica/audit.py`) que guarda el **request** en thread-local.
- Señales (`CoreFisica/signals.py`) que, al dispararse, leen `request.user` del
  thread-local y crean el `AuditLog`.

Punto clave: se guarda el *request* (no el usuario) y se lee `request.user` en el
momento de la señal, porque con SimpleJWT el usuario se autentica **dentro de la
vista** (DRF sincroniza `request.user` al request subyacente al autenticar).

## Consecuencias

- **A favor:** captura automática y centralizada, sin tocar cada vista; el
  usuario JWT queda correctamente asociado.
- **En contra:** depende de thread-local (correcto en el modelo síncrono actual;
  habría que revisar en un despliegue async).
- Se excluyen `AsignacionSemanal`/`SacafrancoFilaSemanal` (cambios de calendario
  de muy alta frecuencia), ya cubiertos por `AsignacionCalendarioLog`.
- El `AuditLog` es consultable en el admin de Django (solo lectura).
