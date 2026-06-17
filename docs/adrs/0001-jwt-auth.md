# ADR 0001: Autenticacion JWT para API

## Estado

Aceptado

## Contexto

El backend expone API consumida por frontend SPA y requiere autenticacion stateless entre cliente y API.

## Decision

Usar JWT con `rest_framework_simplejwt` como mecanismo principal de autenticacion.

## Consecuencias

- Pros: escalable, sin sesion de servidor, simple para frontend SPA.
- Pros: permite expiracion y rotacion de tokens.
- Contras: requiere manejo cuidadoso de expiracion y revocacion.
- Contras: permisos deben validarse por endpoint para evitar acceso excesivo.
