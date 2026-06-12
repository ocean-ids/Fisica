# Architecture Decision Records (ADRs)

Este directorio documenta las decisiones de arquitectura **no obvias** del
sistema: el *por qué* detrás de elecciones que un desarrollador nuevo podría
cuestionar.

Cada ADR sigue el formato: **Contexto → Decisión → Consecuencias**.

> Nota: varios de estos ADRs se escribieron de forma retroactiva (la decisión ya
> estaba tomada e implementada). El objetivo es dejar registro del razonamiento.

## Índice

| ADR | Título | Estado |
|-----|--------|--------|
| [0001](0001-autenticacion-jwt.md) | Autenticación con JWT en vez de sesiones | Aceptado |
| [0002](0002-vistas-basadas-en-funciones.md) | Vistas basadas en funciones (FBV) | Aceptado |
| [0003](0003-asignacionsemanal-siete-campos-dia.md) | `AsignacionSemanal` con 7 campos de día | Aceptado |
| [0004](0004-audit-trail-via-senales.md) | Audit trail vía señales + middleware | Aceptado |
| [0005](0005-busqueda-sin-acentos-unaccent.md) | Búsqueda insensible a acentos con `unaccent` | Aceptado |
| [0006](0006-vistas-compartidas-en-bd.md) | Vistas de cantón/empresa compartidas en BD | Aceptado |
