# ADR 0001 — Autenticación con JWT en vez de sesiones

**Estado:** Aceptado

## Contexto

El backend (Django REST Framework) sirve a un frontend Angular desacoplado
(SPA), potencialmente desde un dominio distinto. Se necesitaba un mecanismo de
autenticación stateless que funcionara bien con un cliente que no comparte
cookies de sesión de forma natural en escenarios cross-origin.

## Decisión

Usar **JWT con `djangorestframework-simplejwt`**:

- `access_token` de vida corta + `refresh_token` con rotación.
- El frontend guarda los tokens y los envía en `Authorization: Bearer <token>`.
- Se complementa con un cierre de sesión por inactividad en el frontend.

## Consecuencias

- **A favor:** stateless, escala horizontalmente sin almacenamiento de sesión
  compartido; encaja con el SPA Angular; soporta blacklist de refresh tokens.
- **En contra:** revocar un access token antes de su expiración no es trivial
  (mitigado con vida corta + blacklist del refresh).
- Los permisos se evalúan por endpoint con `request.user.has_perm(...)`, ya que
  DRF sincroniza el usuario autenticado al request.
