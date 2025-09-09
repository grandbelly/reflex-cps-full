#!/usr/bin/env bash
set -euo pipefail

# Restore latest remote schema dump into local ecoanp_timescaledb (schema-only)

BACKUP_DIR="backups"
LATEST=$(ls -1t ${BACKUP_DIR}/ecoanp_remote_schema_*.sql 2>/dev/null | head -n1 || true)
if [[ -z "$LATEST" ]]; then
  echo "No remote schema dump found in ${BACKUP_DIR}/ecoanp_remote_schema_*.sql" >&2
  exit 1
fi

echo "Using schema dump: $LATEST"
CTR=ecoanp_timescaledb
TMP=/tmp/restore_schema.sql

echo "Copy schema into container..."
docker cp "$LATEST" ${CTR}:${TMP}

echo "Attempt drop+create database as postgres; if not available, fallback to schema reset..."
if docker exec -i ${CTR} psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT 1" >/dev/null 2>&1; then
  docker exec -i ${CTR} psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ecoanp WITH (FORCE);"
  docker exec -i ${CTR} psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ecoanp OWNER ecoanp_user;"
  docker exec -i ${CTR} psql -U postgres -d ecoanp -v ON_ERROR_STOP=1 -f ${TMP}
else
  echo "postgres role not available; resetting public schema in existing ecoanp DB..."
  docker exec -i ${CTR} psql -U ecoanp_user -d ecoanp -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public AUTHORIZATION ecoanp_user;"
  # sanitize dump: drop unknown psql meta commands
  docker exec -i ${CTR} bash -lc "sed -i -e '/^\\\\connect/d' -e '/^\\\\restrict/d' -e '/^\\\\unrestrict/d' -e '/^\\\\echo/d' ${TMP}"
  docker exec -i ${CTR} psql -U ecoanp_user -d ecoanp -v ON_ERROR_STOP=1 -f ${TMP}
fi

echo "Cleanup..."
docker exec -i ${CTR} rm -f ${TMP}

echo "Schema restore completed."
