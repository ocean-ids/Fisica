# Seguridad Física — Backend

API REST del sistema de gestión de turnos de personal de seguridad física.

- **Framework:** Django 5.2 + Django REST Framework
- **Auth:** JWT (SimpleJWT)
- **Base de datos:** PostgreSQL 17 (requiere la extensión `unaccent`)
- **Docs API:** Swagger en `/api/docs/` y ReDoc en `/api/redoc/` (autogenerado por drf-spectacular)

---

## Requisitos

- Python 3.12
- PostgreSQL 17 (con la extensión `unaccent` disponible)
- (Opcional) Docker + Docker Compose para despliegue

---

## Instalación local

```bash
cd backend/fisicaBack

# 1) Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2) Dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt   # solo para correr tests

# 3) Variables de entorno
cp .env.example .env
#   -> edita .env con tus valores (SECRET_KEY, credenciales de BD, etc.)
#   Genera una SECRET_KEY:
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 4) Migraciones (crea tablas + extensión unaccent + siembra provincias/cantones)
python manage.py migrate

# 5) Superusuario (para el admin de Django)
python manage.py createsuperuser

# 6) Crear los grupos de roles (ADMINISTRADOR / OPERADOR / CONSULTA)
python manage.py crear_grupos

# 7) Levantar el servidor de desarrollo
python manage.py runserver
```

> Roles y permisos: ver [`docs/roles-permisos.md`](../../docs/roles-permisos.md).
> Backup/restauración: ver [`docs/backup-restore.md`](../../docs/backup-restore.md).

> La extensión `unaccent` se crea automáticamente en la migración `0117`. El
> usuario de PostgreSQL debe poder ejecutar `CREATE EXTENSION` (normalmente
> superusuario). En local con el usuario `postgres` no hay problema.

---

## Variables de entorno

Ver [`.env.example`](.env.example) para la lista completa y documentada. Las
principales:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django (obligatoria) |
| `DEBUG` | `True` en desarrollo, `False` en producción |
| `ALLOWED_HOSTS` | Hosts permitidos (coma-separados) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Conexión a PostgreSQL |
| `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` | Orígenes del frontend |
| `EMAIL_*` | SMTP para reseteo de contraseña |

En producción (`DEBUG=False`) se activan automáticamente: redirección HTTPS,
HSTS y cookies seguras (ver `settings.py`).

---

## Tests

```bash
# Con el runner de Django:
python manage.py test CoreFisica

# Con pytest (requiere requirements-dev.txt):
pytest
```

Cubren: autenticación JWT, permisos por endpoint, CRUD de asignación y
consolidado, y el audit trail. La CI (`.github/workflows/ci.yml`) los corre en
cada push/PR a `main` y `develop`.

---

## Estructura

```
CoreFisica/
  models.py              Modelos de dominio
  urls.py                Rutas de la API
  serializers.py         Serializers DRF
  views/                 Vistas (una por dominio): cliente, instalacion,
                         puesto, persona, asignacion, consolidado, etc.
  migrations/            Migraciones (incluye seed de provincias/cantones)
  audit.py + signals.py  Audit trail (registro de operaciones)
  tests/                 Tests (pytest / Django test runner)
fisicaBack/
  settings.py            Configuración (env-driven)
```

---

## Despliegue (Docker)

El proyecto se despliega con `docker-compose.yml` (servicios `sf_postgres`,
`sf_backend`, `sf_frontend`). El contenedor del backend ejecuta `migrate`
automáticamente al arrancar, por lo que las migraciones pendientes se aplican
solas en cada deploy.

```bash
docker compose pull backend frontend
docker compose up -d
```

Variables sensibles (`SECRET_KEY`, `DB_PASSWORD`, `POSTGRES_PASSWORD`) se
inyectan vía entorno, no se versionan.

---

## Decisiones de arquitectura

Ver [`docs/adr/`](../../docs/adr/) para el registro de decisiones (ADRs).
