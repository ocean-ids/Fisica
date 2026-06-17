# ADR 0003: Esquema semanal con columnas por dia

## Estado

Aceptado (deuda conocida)

## Contexto

`AsignacionSemanal` guarda los dias en columnas `mon..sun` como `CharField`.

## Decision

Conservar el esquema actual en el corto plazo para no romper logica de negocio y pantallas actuales.

## Consecuencias

- Pros: compatibilidad inmediata con codigo y datos existentes.
- Pros: evita migracion riesgosa en fase operativa.
- Contras: consultas por dia menos expresivas en ORM.
- Contras: deuda tecnica para analitica y mantenibilidad.

## Plan de evolucion

1. Disenar modelo normalizado por dia (fila por dia).
2. Migrar datos con script reversible.
3. Adaptar endpoints por fases con pruebas de regresion.
