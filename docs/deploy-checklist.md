# Deploy Checklist

## Pre-deploy

1. Backend image construida y publicada.
2. Suite minima de pruebas en verde.
3. Variables en `.env` revisadas en servidor.
4. Certificados TLS presentes en `certs/` del servidor.

## Comandos recomendados (servidor)

```bash
cd /opt/fisica
docker compose pull backend frontend
docker compose up -d db backend frontend
docker compose exec backend python manage.py migrate --noinput
docker compose restart backend
docker compose logs --tail=100 backend
```

## Verificacion post-deploy

1. `docker compose ps` sin reinicios anormales.
2. `docker compose logs --tail=100 backend` sin tracebacks.
3. Login funcional (`/api/login/`).
4. Endpoint critico funcional (`/api/reporte-asistencia/...`).
5. Frontend HTTPS responde correctamente.

## Rollback rapido

Si hay error critico:

1. Volver a imagen backend anterior.
2. `docker compose up -d backend`.
3. Revisar logs y estado de migraciones.

## Backup y restauracion

Scripts en `scripts/` (ver `docs/backup-restore.md` para el detalle):

```bash
cd /opt/fisica
sh scripts/backup.sh                              # backups/sf_bd_<fecha>.sql.gz (+ media)
sh scripts/restore.sh backups/sf_bd_<fecha>.sql.gz # restaura (sobrescribe sf_bd)
```

- **Frecuencia recomendada:** diaria (cron 02:00). Retencion: ultimos 14.
- **Antes de cada deploy:** ejecutar `sh scripts/backup.sh`.
- **Probado:** dump + restore verificados (conteo de filas identico origen/restaurado).
