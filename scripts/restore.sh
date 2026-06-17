#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# Restaura la base de datos del sistema Seguridad Física desde un backup.
#
# Uso (en el servidor, dentro de /opt/fisica):
#   sh scripts/restore.sh backups/sf_bd_20260617_020000.sql.gz
#
# ADVERTENCIA: reemplaza por completo la base 'sf_bd' actual.
# Requiere: docker compose corriendo (servicio db = sf_postgres).
# ---------------------------------------------------------------------------
set -e

DUMP="$1"
if [ -z "$DUMP" ]; then
  echo "Uso: sh scripts/restore.sh <archivo.sql | archivo.sql.gz>"
  exit 1
fi
if [ ! -f "$DUMP" ]; then
  echo "No existe el archivo: $DUMP"
  exit 1
fi

echo "ADVERTENCIA: se va a SOBREESCRIBIR la base 'sf_bd' con $DUMP"
echo "Cerrando conexiones y recreando la base..."
docker compose exec -T db psql -U postgres -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='sf_bd' AND pid<>pg_backend_pid();" >/dev/null
docker compose exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS sf_bd;"
docker compose exec -T db psql -U postgres -d postgres -c "CREATE DATABASE sf_bd OWNER postgres;"

echo "Restaurando datos..."
case "$DUMP" in
  *.gz) gunzip -c "$DUMP" | docker compose exec -T db psql -U postgres -d sf_bd ;;
  *)    docker compose exec -T db psql -U postgres -d sf_bd < "$DUMP" ;;
esac

echo "Restauración completa. Reinicia el backend si es necesario:"
echo "  docker compose restart backend"
