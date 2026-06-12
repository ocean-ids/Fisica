# ADR 0002 — Vistas basadas en funciones (FBV)

**Estado:** Aceptado

## Contexto

DRF permite vistas basadas en clases (CBV: `APIView`, `ViewSet`, generics) o
basadas en funciones (FBV con `@api_view`). El sistema tiene mucha lógica de
negocio específica por endpoint (cálculo de turnos, generación de calendarios,
exportación Excel/PDF, importación desde Excel) que no encaja en el CRUD genérico
de un `ModelViewSet`.

## Decisión

Predominan las **vistas basadas en funciones** con `@api_view` (~92% de las
vistas). Las pocas CBV existentes (p. ej. `PatronAsignacion`) se usan donde el
CRUD genérico sí aplica.

## Consecuencias

- **A favor:** la lógica de negocio compleja queda explícita y lineal, fácil de
  seguir; control total sobre permisos, validación y forma de la respuesta.
- **En contra:** más código repetido (permisos, parseo de parámetros) que con
  generics; archivos de vistas grandes (ver deuda técnica: dividir
  `asignacion_views.py`).
- Decisión consciente: priorizar legibilidad de la lógica de dominio sobre la
  brevedad del CRUD genérico.
