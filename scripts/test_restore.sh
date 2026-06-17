#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# Verificación AUTOMÁTICA de la integridad del backup (no manual):
#   1) genera un dump de sf_bd
#   2) lo restaura en una base TEMPORAL
#   3) compara el conteo de filas de una tabla grande origen vs restaurada
#   4) elimina la base temporal
# Imprime un log con timestamp y sale 0 (OK) o 1 (FALLO). Apto para cron/CI.
#
# Uso (servidor):  sh scripts/test_restore.sh
#   (registrar evidencia):  sh scripts/test_restore.sh | tee -a docs/backup-restore-test.log
# ---------------------------------------------------------------------------
set -e

TS=$(date '+%Y-%m-%d %H:%M:%S')
TMPDB="sf_bd_verify_$(date +%s)"
TABLE="CoreFisica_asignacionsemanal"
DUMP=$(mktemp)

db() { docker compose exec -T db "$@"; }

echo "[$TS] test_restore: generando dump de sf_bd..."
db pg_dump -U postgres -d sf_bd > "$DUMP"

echo "[$TS] creando base temporal $TMPDB y restaurando..."
db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS $TMPDB;" >/dev/null
db psql -U postgres -d postgres -c "CREATE DATABASE $TMPDB;" >/dev/null
db psql -U postgres -d "$TMPDB" < "$DUMP" >/dev/null

ORIG=$(db psql -U postgres -d sf_bd      -t -c "SELECT count(*) FROM \"$TABLE\";" | tr -d ' \r\n')
REST=$(db psql -U postgres -d "$TMPDB"   -t -c "SELECT count(*) FROM \"$TABLE\";" | tr -d ' \r\n')

db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS $TMPDB;" >/dev/null
rm -f "$DUMP"

if [ -n "$ORIG" ] && [ "$ORIG" = "$REST" ]; then
  echo "[$TS] OK backup verificado: $TABLE origen=$ORIG restaurado=$REST"
  exit 0
else
  echo "[$TS] FALLO: conteos distintos. origen=$ORIG restaurado=$REST"
  exit 1
fi
