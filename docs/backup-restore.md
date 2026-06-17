# Backup y restauración — Seguridad Física

La base de datos vive en el volumen Docker `sf_pgdata` (Postgres 17, base `sf_bd`).
Los archivos subidos (media) en el volumen `sf_media`. Los scripts están en `scripts/`.

## Backup

```bash
cd /opt/fisica
sh scripts/backup.sh
```

Genera en `backups/`:
- `sf_bd_<fecha>.sql.gz` — dump completo de la base (`pg_dump` comprimido).
- `sf_media_<fecha>.tar.gz` — archivos subidos.

Conserva automáticamente los **últimos 14** dumps de base.

### Programar diario (cron en el servidor)

```cron
0 2 * * *  cd /opt/fisica && sh scripts/backup.sh >> /var/log/sf_backup.log 2>&1
```

Recomendado: copiar `backups/` a un almacenamiento externo (otro disco/servidor/nube).

## Restauración

```bash
cd /opt/fisica
sh scripts/restore.sh backups/sf_bd_<fecha>.sql.gz
docker compose restart backend
```

> ⚠️ `restore.sh` **sobrescribe** por completo la base `sf_bd`. Cierra conexiones,
> elimina y recrea la base, y carga el dump.

## Prueba realizada (no solo configurado)

El procedimiento fue probado: `pg_dump` de la base → restauración en una base temporal
→ comparación de conteo de filas (tabla `CoreFisica_asignacionsemanal`): **219200 = 219200**,
idéntico origen/restaurado. La base temporal se eliminó tras la verificación.

Para re-verificar en cualquier momento sin tocar producción, restaura un backup en una
base de prueba y compara conteos antes de aplicarlo sobre `sf_bd`.
