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

## Verificación automática (no solo configurado — probado)

Hay un script que prueba el ciclo completo **sin intervención manual**: genera un dump,
lo restaura en una base temporal, compara el conteo de filas origen vs restaurada,
borra la temporal e imprime un log con timestamp (sale 0 OK / 1 FALLO):

```bash
sh scripts/test_restore.sh                                   # corre la verificación
sh scripts/test_restore.sh | tee -a docs/backup-restore-test.log   # y registra evidencia
```

Apto para cron/CI (p. ej. semanal) para validar que los backups son recuperables.

### Evidencia de prueba

Log con timestamp en [`backup-restore-test.log`](backup-restore-test.log). Última corrida:

```
[2026-06-17 11:26:08] OK backup verificado: CoreFisica_asignacionsemanal origen=219200 restaurado=219200
```

`pg_dump` de la base → restauración en base temporal → conteo de filas **idéntico**
(219200 = 219200). La base temporal se eliminó tras la verificación.
