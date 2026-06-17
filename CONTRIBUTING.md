# Guía de contribución — Seguridad Física

Proyecto: backend **Django (DRF + JWT)** + frontend **Angular** + **PostgreSQL**, desplegado con Docker.

## Estructura

```
backend/fisicaBack/   # API Django (app CoreFisica)
frontendf/            # SPA Angular
docs/                 # documentación (setup, ADRs, roles, backup, deploy)
scripts/              # backup.sh / restore.sh
docker-compose.yml    # orquestación (db, backend, frontend)
```

## Levantar el proyecto

- Backend: ver [docs/backend-setup.md](docs/backend-setup.md).
- Frontend: `cd frontendf && npm install && npm start`.
- Todo con Docker: `docker compose up -d` (requiere `.env`, ver `.env.example`).

## Antes de hacer push

1. **Backend**: `pytest` en verde (desde `backend/fisicaBack/`).
2. **Frontend**: `npx tsc --noEmit -p tsconfig.app.json` sin errores.
3. **Migraciones**: si cambiaste modelos, `python manage.py makemigrations` y commitea la migración.
4. No subir secretos: el `.env` está ignorado; solo se versiona `.env.example`.

## Convenciones

- **Permisos**: cada endpoint valida `request.user.has_perm('CoreFisica.<accion>_<modelo>')`. Ver [docs/roles-permisos.md](docs/roles-permisos.md).
- **Vistas**: organizadas por dominio en `CoreFisica/views/*.py`, cada módulo con docstring de qué hace.
- **Decisiones de arquitectura**: documentadas como ADRs en [docs/adr/](docs/adr/).

## Ramas

- `main`: estable / producción.
- `develop`: integración.
- Trabajar en ramas de feature y abrir PR hacia `develop`.

## Backup / restauración

Ver [docs/backup-restore.md](docs/backup-restore.md) (`scripts/backup.sh`, `scripts/restore.sh`).
