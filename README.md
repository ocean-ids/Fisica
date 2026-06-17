# Seguridad Física

Plataforma de gestión de turnos de personal de seguridad física: clientes,
instalaciones, puestos, personas, asignaciones (calendario D/N/F), sacafrancos,
reportes de asistencia, consolidado y novedades de puesto.

- **Backend:** Django 5.2 + DRF + JWT — `backend/fisicaBack/`
- **Frontend:** Angular (SPA) — `frontendf/`
- **Base de datos:** PostgreSQL 17
- **Despliegue:** Docker Compose (`docker-compose.yml`)

## Cómo levantar el proyecto

| Quiero… | Ver |
|---------|-----|
| Levantar el **backend** local (paso a paso) | [`backend/fisicaBack/README.md`](backend/fisicaBack/README.md) y [`docs/backend-setup.md`](docs/backend-setup.md) |
| Levantar el **frontend** | `cd frontendf && npm install && npm start` |
| Levantar **todo con Docker** | [`docs/deploy-checklist.md`](docs/deploy-checklist.md) |
| Cómo **contribuir** | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

### Arranque rápido del backend

```bash
cd backend/fisicaBack
python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # completar SECRET_KEY, credenciales de BD, etc.
python manage.py migrate
python manage.py crear_grupos # roles ADMINISTRADOR / OPERADOR / CONSULTA
python manage.py createsuperuser
python manage.py runserver
pytest                        # correr las pruebas
```

## Documentación

- [`docs/backend-setup.md`](docs/backend-setup.md) — instalación del backend.
- [`docs/roles-permisos.md`](docs/roles-permisos.md) — roles y permisos (quién puede qué).
- [`docs/backup-restore.md`](docs/backup-restore.md) — backup y restauración (probado).
- [`docs/deploy-checklist.md`](docs/deploy-checklist.md) — despliegue.
- [`docs/adr/`](docs/adr/) — decisiones de arquitectura (ADRs).

## Ramas

- `main` — estable / entregable.
- `develop` — integración (rama de trabajo).
