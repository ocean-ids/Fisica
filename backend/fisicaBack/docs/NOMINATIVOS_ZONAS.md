# Especificación: Zonas y Nominativos

> Documento de definición. A implementar en la rama `feature` (modelos, migración,
> pantalla, validación en import). Cambio **aditivo**: no se pierde nada de lo actual.

## 1. Zonas (nueva tabla)

Cada **zona** tiene un **identificador** (Zona 1, Zona 2, …), un **nombre** y una
**letra única**. Se pueden **crear tantas zonas como sea necesario**.

| Zona    | Nombre | Letra | Nominativos (ejemplo) |
|---------|--------|-------|-----------------------|
| Zona 1  | GAMMA  | G     | G1, G2, G3, …         |
| Zona 2  | DELTA  | D     | D1, D2, D3, …         |
| Zona 3  | (otra) | B     | B1, B2, …             |

- El **usuario escribe la letra**; el sistema valida que no se repita.
- La letra es **única en todo el sistema**.

## 2. Nominativo

Formato: **[letra de la zona] + [número secuencial]**, escrito **junto**: `G23`, `D5`.

- Se asigna a una **instalación** (nivel instalación).
- Número **secuencial y único por zona**; **huecos reutilizables**; sin tope práctico.
- Único: dos instalaciones no comparten nominativo.

### Variante con varios nombres por zona
Una zona puede tener varios nombres, cada uno con **abreviatura única** (1–3 letras).
Dos formas del nominativo:
- **Completo** = nombre + número (`KAPPA1`) → **Reporte de Asistencia**.
- **Resumido** = abreviatura + número (`K1`) → **Instalación** y **sacafranco**.

| Nombre | Abrev. | Completo | Resumido |
|--------|--------|----------|----------|
| KAPPA  | K      | KAPPA1   | K1       |
| ARES   | AR     | ARES1    | AR1      |
| ANDES  | AN     | ANDES1   | AN1      |

## 3. ¿Es necesaria la tabla de zonas?

- **Solo `Nominativo` (letra+número):** basta para validar y asignar; la "zona" es
  implícita por la letra. NO permite nombre de zona ni filtrar por nombre.
- **Con `ZonaOperativa`:** permite **nombrar** zonas y **filtrar el Reporte de
  Asistencia por zona** (GAMMA/DELTA). → **Necesaria porque se quiere filtrar el
  reporte por estas zonas.**

## 4. Asignación y validación al importar

- Los nominativos se **administran aparte** (pantalla Zonas/Nominativos), asignados a
  la instalación. El import **valida y referencia** (no crea).
- Al importar, si el nominativo **no existe** o **no corresponde a esa instalación**
  → **alerta** y **no se importa** esa fila.
- **Por qué importa:** los tokens del sacafranco (`D/N + código`) resuelven cobertura
  por ese código; si el nominativo no coincide, el sacafranco caería en el cliente
  equivocado.

## 5. Sin perder lo actual (migración aditiva)

- Los nominativos actuales viven en `Instalacion.codigo` (U20, P8, G15…) → **se
  conservan** y sirven para **sembrar** la tabla nueva (por cada código `U20` → crear
  zona letra `U` + nominativo `U20` ligado a la instalación).
- El modelo **`Zona` actual** (Zona 1/2/3 por instalación, usado por `Puesto.zona` y
  el filtro actual del reporte) **NO se toca**.
- Pendiente decidir: las zonas nuevas (GAMMA/DELTA) **¿reemplazan** el filtro de zona
  actual del Reporte de Asistencia, o son **adicionales**?

## 6. Plan técnico (en `feature`)

- Modelos: `ZonaOperativa` (numero, nombre, letra única) + `Nominativo`
  (zona FK, numero, instalacion OneToOne null=libre, unique(zona,numero)).
- Migración que **siembra** desde `Instalacion.codigo`.
- Pantalla CRUD de zonas + asignar nominativo a instalación.
- Import: validar nominativo ↔ instalación (por código exacto).
- Reporte de Asistencia: filtro por zona nueva.

## Notas técnicas (estado actual)

- Hoy `nominativo` solo existe como `Instalacion.codigo` y como campo en `Consolidado`.
- El import ya valida hoy que el **código de instalación exista** (si no → alerta).
- Existe una validación provisional cliente↔nominativo en el import (por nombre,
  tolerante); la confiable (por código) es la del #4.
