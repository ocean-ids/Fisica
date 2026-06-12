# ADR 0006 — Vistas de cantón/empresa compartidas en BD

**Estado:** Aceptado

## Contexto

La pantalla de asignaciones permite agrupar el trabajo en "vistas" personalizadas
(p. ej. *GUAYAQUIL - DURÁN*). Originalmente se guardaban en `localStorage` del
navegador, por lo que una vista creada en una máquina no aparecía en otra y cada
usuario tenía que recrearla.

## Decisión

Persistir las vistas en la **base de datos** como recurso **compartido (global)**
entre todos los usuarios:

- Modelo `VistaCanton` con `tipo` (`canton` | `cliente`), `cantones` y `clientes`.
- Endpoint `/api/vistas-cantones/` con sincronización *upsert + prune* (recibe la
  lista completa, actualiza/crea/borra y devuelve ids estables).
- El frontend carga y guarda desde la BD (ya no usa `localStorage`).

Se admiten dos tipos de vista:
- **Por cantones:** agrupa 2+ cantones.
- **Por empresas:** agrupa 1+ clientes y muestra **todas sus instalaciones** sin
  importar el cantón.

## Consecuencias

- **A favor:** las vistas siguen al equipo en cualquier máquina; consistencia.
- **En contra:** una vista creada/borrada afecta a todos los usuarios (decisión
  explícita: se prefirió compartir sobre aislar por usuario).
- Para la vista por empresa, el filtrado de sacafranco deriva los cantones de las
  instalaciones de esos clientes.
