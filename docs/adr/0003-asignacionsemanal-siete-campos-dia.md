# ADR 0003 — `AsignacionSemanal` con 7 campos de día

**Estado:** Aceptado

## Contexto

El calendario de turnos se representa por **semana** (una fila por puesto/asignación
y `week_start`), y cada día de esa semana guarda un valor corto: `D` (diurno),
`N` (nocturno), `F` (franco) o un código de cobertura (sacafranco).

Alternativas consideradas:
1. 7 campos `CharField` (`mon`, `tue`, … `sun`).
2. Una fila por día (modelo normalizado `día → valor`).
3. Un `JSONField` con los 7 valores.

## Decisión

Usar **7 `CharField`** (`mon`..`sun`) en `AsignacionSemanal`.

## Consecuencias

- **A favor:** la vista de calendario (frontend) renderiza una fila = una semana
  de forma directa; lectura/escritura de una semana es una sola fila; encaja con
  el formato Excel de "reporte de horarios" que el negocio ya usa.
- **En contra:** no se puede filtrar "todos los puestos con `F` el día X" con un
  filtro ORM limpio sin un `OR` sobre los 7 campos; consultas por día son
  incómodas.
- Mitigación: los reportes y consolidados que sí necesitan vista por día
  recorren los 7 campos en código. Para auditoría de cambios de calendario existe
  `AsignacionCalendarioLog`.

> Si en el futuro se requiere análisis intensivo por día, considerar normalizar a
> opción (2) o materializar una vista por día.
