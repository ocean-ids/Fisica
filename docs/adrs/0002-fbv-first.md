# ADR 0002: Predominio de Function-Based Views (FBV)

## Estado

Aceptado (historico)

## Contexto

El codigo existente implementa la mayoria de endpoints con `@api_view`.

## Decision

Mantener FBV en modulos existentes para cambios incrementales y bajo riesgo.

## Consecuencias

- Pros: menor friccion al mantener codigo legado.
- Pros: cambios puntuales rapidos en endpoints ya existentes.
- Contras: mayor dispersion de validaciones y estilos de respuesta.
- Contras: dificulta estandarizacion si no se define una guia comun.

## Nota

A futuro se recomienda converger por modulo a patrones mas consistentes (FBV estandarizadas o CBV/ViewSets), evitando cambios masivos en una sola iteracion.
