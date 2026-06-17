# Backend Setup (Django)

## Requisitos

- Python 3.12+
- PostgreSQL 17 (local) **o** el contenedor `db` del `docker-compose.yml`
- Extensión `unaccent` disponible en Postgres (se habilita por migración)

## 1. Clonar y crear entorno virtual

```bash
git clone <repo>
cd <repo>/backend/fisicaBack
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
# .\venv\Scripts\Activate.ps1
```

## 2. Dependencias

```bash
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # pruebas (pytest, pytest-django)
```

## 3. Variables de entorno

La plantilla está en `backend/fisicaBack/.env.example`.

```bash
cp .env.example .env
# completar secretos reales: SECRET_KEY, DB_*, correo, etc.
```

## 4. Base de datos y arranque

```bash
python manage.py migrate
python manage.py crear_grupos          # crea roles ADMINISTRADOR/OPERADOR/CONSULTA
python manage.py createsuperuser       # usuario inicial
python manage.py runserver
```

## 5. Pruebas

```bash
pytest                 # usa pytest.ini (DJANGO_SETTINGS_MODULE ya configurado)
# o con Django:
python manage.py test CoreFisica
```

## Comprobaciones básicas

- `GET /api/docs/` abre Swagger.
- `POST /api/login/` retorna `access` y `refresh`.
- Endpoints protegidos retornan `403` sin los permisos correspondientes.

## Levantar todo con Docker (alternativa)

Desde la raíz del repo, con un `.env` válido:

```bash
docker compose up -d
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py crear_grupos
```

Ver también: `docs/roles-permisos.md`, `docs/backup-restore.md`, `docs/deploy-checklist.md`.
