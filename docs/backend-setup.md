# Backend Setup (Django)

## Requisitos

- Python 3.12+
- PostgreSQL (o contenedor `db` del `docker-compose.yml`)
- Entorno virtual en `backend/fisicaBack/venv`

## Variables de entorno

Usar la plantilla `.env.example` en la raiz del repo.

1. Copiar `.env.example` a `.env`.
2. Completar secretos reales (`SECRET_KEY`, credenciales DB, correo).

## Arranque local (Windows PowerShell)

```powershell
Set-Location "c:/Users/bryan/Desktop/Fisica/backend/fisicaBack"
( Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned )
& .\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

## Pruebas minimas recomendadas

```powershell
Set-Location "c:/Users/bryan/Desktop/Fisica/backend/fisicaBack"
c:/Users/bryan/Desktop/Fisica/backend/fisicaBack/venv/Scripts/python.exe manage.py test CoreFisica.tests.ApiSmokeAuthTests CoreFisica.tests.UbicacionPermissionsTests CoreFisica.tests.CriticalPermissionsTests CoreFisica.tests.AsignacionCrudIntegrationTests CoreFisica.tests.ConsolidadoIntegrationTests -v 2
```

## Comprobaciones basicas

- `GET /api/docs/` abre Swagger.
- `POST /api/login/` retorna `access` y `refresh`.
- Endpoints protegidos retornan `403` sin permisos granulares.
