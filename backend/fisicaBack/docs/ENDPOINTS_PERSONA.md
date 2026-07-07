# API — Endpoints de Persona (Empleados)

**Base URL:** `/api/v1/` (también disponible en `/api/`)
**Autenticación:** JWT (SimpleJWT) — cabecera `Authorization: Bearer <access_token>`.
**Formato:** JSON, salvo subidas de archivo (`multipart/form-data`).
**Docs interactivas:** Swagger en `/api/v1/docs/` · Schema en `/api/v1/schema/`.

> Nota: todas las rutas requieren usuario autenticado y el permiso correspondiente
> de Django (`CoreFisica.view_persona`, `CoreFisica.add_persona`,
> `CoreFisica.change_persona`, `CoreFisica.delete_persona`, según el caso).

---

## 1. CRUD de Persona

| Método | Ruta | Descripción |
|---|---|---|
| `GET`  | `/personas/` | Lista de personas. Filtros por query: `?unidad=FISICA\|CARGA` (vacío/nulo cuenta como FISICA), `?tipo=<TIPO>`, y filtros de búsqueda. |
| `POST` | `/crear-persona/` | Crea una persona. Body = campos del empleado. |
| `PUT`  | `/actualizar-persona/<id>/` | Actualiza la persona `id`. Body parcial con los campos a cambiar. |
| `DELETE` | `/eliminar-persona/<id>/` | Elimina la persona `id`. |

**Campos del body (crear/actualizar)** — principales:
`nombres`, `apellidos`, `cedula`, `tipo` (clasificación: FIJOS, RETEN, CUSTODIO,
EVENTUAL, SACAFRANCO, …), `sexo`, `fecha_nacimiento`, `lugar_nacimiento`,
`estatura`, `nacionalidad`, `estado_civil`, `provincia`, `canton`, `parroquia`,
`direccion`, `telefono`, `conyuge`, `cliente`, `seccion`, `unidad_negocio`
(SEGURIDAD FISICA / SEGURIDAD DE CARGA), `tipo_empleado`, `forma_pago`, `perfil`,
`region`, `motivo_salida`, `cargo`, `departamento`, `codigo_erp`, `centro_costo`,
`numero_afiliacion`, `numero_contrato`, `actividad`, `fecha_ingreso`,
`fecha_salida`, `fecha_pago_liquidacion`, `gypaseg`, `affis`, `pbip`,
**`estado_empleado`** (ver abajo).

### Estado del empleado
El formulario usa **`estado_empleado`** con 3 valores: **`ACTIVO`**, **`LIQUIDADO`**,
**`SUSPENDIDO`**. `LIQUIDADO` y `SUSPENDIDO` equivalen a *deshabilitado*: el modelo
sincroniza `is_active` automáticamente en `save()` (`ACTIVO` → `is_active=True`; el
resto → `is_active=False`). Todos los filtros del sistema siguen usando `is_active`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/disable-persona/<id>/` | Deshabilita (baja): pone `estado_empleado=LIQUIDADO` → `is_active=False`. |
| `POST` | `/enable-persona/<id>/` | Habilita (alta): `estado_empleado=ACTIVO` → `is_active=True`. |

---

## 2. Foto

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/personas/<id>/foto/` | Sube la foto de la persona. `multipart/form-data`, campo `foto`. |

---

## 3. Pestañas del formulario (datos por empleado)

Cada pestaña tiene un `GET` (obtener) y un `guardar` (`PUT`/`POST`).

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/personas/<id>/nomina/` | Datos de nómina (ingresos/descuentos, beneficios de ley, acumulados). |
| `PUT`/`POST` | `/personas/<id>/nomina/guardar/` | Guarda la nómina. |
| `GET` | `/personas/<id>/otros-datos/` | Otros datos (banco, cuentas, vacaciones, cuentas contables, relación de dependencia). |
| `PUT`/`POST` | `/personas/<id>/otros-datos/guardar/` | Guarda otros datos. |
| `GET` | `/personas/<id>/referencias/` | Datos referenciales + estudios + servicios. |
| `PUT`/`POST` | `/personas/<id>/referencias/guardar/` | Guarda referencias. |
| `GET` | `/personas/<id>/documentos/` | Documentos (rutas compartidas). |
| `PUT`/`POST` | `/personas/<id>/documentos/guardar/` | Guarda documentos. |
| `GET` | `/personas/<id>/mas-referencias/` | Experiencia, referencias personales, niveles de estudio y formación. |
| `PUT`/`POST` | `/personas/<id>/mas-referencias/guardar/` | Guarda "más referencias". |

---

## 4. Certificados

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/certificados/catalogo/` | Catálogo de tipos de certificado (agrupados). |
| `POST` | `/certificados/tipos/` | Crea un tipo de certificado nuevo. Body: `nombre` (y grupo). |
| `GET` | `/personas/<id>/certificados/` | Certificados de la persona (estado por tipo + archivo). |
| `PUT`/`POST` | `/personas/<id>/certificados/guardar/` | Guarda el estado (check) de los certificados. |
| `POST` | `/personas/<id>/certificados/<tipo_id>/archivo/` | Sube el archivo (PDF/imagen) de ese certificado. `multipart/form-data`, campo `archivo`. |
| `DELETE` | `/personas/<id>/certificados/<tipo_id>/archivo/eliminar/` | Elimina el archivo de ese certificado. |

---

## 5. Importar / Exportar

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/importar-personas/` | Importa personas desde archivo (Excel/CSV). `multipart/form-data`. |
| `GET` | `/exportar-personas-excel/` | Exporta las personas a Excel. |

---

## 6. Sacafranco

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/personas/sacafrancos/` | Lista de personas tipo SACAFRANCO. |
| `POST` | `/personas/sacafrancos/assign/` | Asigna un sacafranco. |
| `POST` | `/personas/sacafrancos/unassign/` | Desasigna un sacafranco. |

---

## 7. Sincronización desde el ERP (Powersai)

Endpoint máquina-a-máquina (no usa JWT sino **API Key**):

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/sync/empleado/` | `Authorization: Bearer <SYNC_API_KEY>` | Upsert de empleado por cédula. Solo unidades SF/SC (`unidad_negocio` **obligatorio**; otra unidad → 200 "Ignorado"). Cabecera `X-Powersai-Event: empleado.creado \| empleado.actualizado \| empleado.baja`. La baja (evento `empleado.baja` o `estado` = BAJA/INACTIVO/CESADO) marca deshabilitado (`estado_empleado=LIQUIDADO`). |

**Códigos de respuesta:** `201` creado · `200` actualizado o ignorado ·
`400` dato inválido (no reintentar) · `401` token inválido (no reintentar) ·
`500` error del servidor (reintentar con backoff).

> Ruta definida en `CoreFisica/urls.py` como `path('sync/empleado/', sincronizar_empleado)`
> (bajo el prefijo `/api/v1/`, también accesible en `/api/`). La autenticación se valida
> contra `settings.SYNC_API_KEY` en `CoreFisica/views/sync_views.py`.

---

_Documento generado a partir de `CoreFisica/urls.py` y `CoreFisica/views/persona_views.py` (+ `sync_views.py`)._
