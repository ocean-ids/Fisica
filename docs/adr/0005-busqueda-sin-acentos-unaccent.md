# ADR 0005 — Búsqueda insensible a acentos con `unaccent`

**Estado:** Aceptado

## Contexto

Los datos (nombres de personas, clientes, instalaciones) se guardan en mayúsculas
y con acentos (`MARÍA`, `MUÑOZ`). Al filtrar, los usuarios escriben sin acentos
(`MARIA`, `MUNOZ`) y `icontains` no encontraba coincidencias, dando la sensación
de que "no filtra bien".

## Decisión

Usar la extensión **`unaccent` de PostgreSQL**:

- Migración `0117` crea la extensión (`UnaccentExtension`).
- `django.contrib.postgres` en `INSTALLED_APPS` habilita el lookup `__unaccent`.
- Las búsquedas usan `campo__unaccent__icontains=valor` (quita acentos a la
  columna) y se quita acentos al texto escrito (`_strip_accents`), de modo que
  ambos lados quedan sin acentos.

Se aplica en: lista de asignaciones, clientes, instalaciones, personas y
sacafranco. La cédula se deja como `icontains` (solo dígitos).

## Consecuencias

- **A favor:** `JOSE` encuentra `JOSÉ` y viceversa; búsqueda predecible.
- **En contra:** dependencia de una extensión de PostgreSQL. El usuario de BD
  debe poder crear la extensión (superusuario) la primera vez.
- El frontend además fuerza el texto del filtro a mayúsculas para coincidir con
  cómo se almacenan los datos.
