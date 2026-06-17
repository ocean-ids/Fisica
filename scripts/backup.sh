#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# Backup de la base de datos (y media) del sistema Seguridad Física.
#
# Uso (en el servidor, dentro de /opt/fisica):
#   sh scripts/backup.sh            # genera backups/sf_bd_<fecha>.sql(.gz)
#   sh scripts/backup.sh /ruta/dir  # guarda en otra carpeta
#
# Requiere: docker compose corriendo (servicio db = sf_postgres).
# Programar diario con cron, p. ej.:
#   0 2 * * *  cd /opt/fisica && sh scripts/backup.sh >> /var/log/sf_backup.log 2>&1
# ---------------------------------------------------------------------------
set -e

OUT_DIR="${1:-backups}"
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$OUT_DIR"

DB_FILE="$OUT_DIR/sf_bd_${TS}.sql.gz"
echo "[backup] Base de datos -> $DB_FILE"
docker compose exec -T db pg_dump -U postgres -d sf_bd | gzip > "$DB_FILE"

MEDIA_FILE="$OUT_DIR/sf_media_${TS}.tar.gz"
echo "[backup] Media -> $MEDIA_FILE"
docker compose exec -T backend tar czf - -C /app media > "$MEDIA_FILE" 2>/dev/null \
  || echo "[backup] (media omitida)"

# Retención: conservar solo los últimos 14 backups de base.
ls -1t "$OUT_DIR"/sf_bd_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "[backup] OK"
ls -lh "$OUT_DIR" | tail -5
