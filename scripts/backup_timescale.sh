#!/usr/bin/env bash
set -euo pipefail

# Usage:
#  scripts/backup_timescale.sh local [schema|full]
#  scripts/backup_timescale.sh remote [schema|full]   # remote uses $TS_DSN from .env

OUT_DIR="backups"
mkdir -p "$OUT_DIR"
TS=$(date +%Y%m%d_%H%M%S)

target=${1:-local}
mode=${2:-schema}   # default to schema-only

if [[ "$target" == "local" ]]; then
  DB_DSN="postgresql://ecoanp_user:ecoanp_password@ecoanp_timescaledb:5432/ecoanp"
  if [[ "$mode" == "schema" ]]; then
    OUT="$OUT_DIR/ecoanp_local_schema_${TS}.sql"
    echo "Backing up LOCAL (schema-only) to $OUT"
    docker exec ecoanp_timescaledb pg_dump --schema-only --no-owner --no-privileges \
      -N information_schema -N pg_catalog -N _timescaledb_% \
      "$DB_DSN" -f "/tmp/ecoanp_local_schema_${TS}.sql"
    docker cp ecoanp_timescaledb:/tmp/ecoanp_local_schema_${TS}.sql "$OUT_DIR/"
    docker exec ecoanp_timescaledb rm -f "/tmp/ecoanp_local_schema_${TS}.sql"
    echo "OK: $OUT"
  else
    OUT="$OUT_DIR/ecoanp_local_full_${TS}.sql"
    echo "Backing up LOCAL (full) to $OUT"
    docker exec ecoanp_timescaledb pg_dump --no-owner --no-privileges \
      "$DB_DSN" -f "/tmp/ecoanp_local_full_${TS}.sql"
    docker cp ecoanp_timescaledb:/tmp/ecoanp_local_full_${TS}.sql "$OUT_DIR/"
    docker exec ecoanp_timescaledb rm -f "/tmp/ecoanp_local_full_${TS}.sql"
    echo "OK: $OUT"
  fi
elif [[ "$target" == "remote" ]]; then
  # Requires TS_DSN in environment (docker compose env_file ../.env)
  # Example: postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable
  if [[ -z "${TS_DSN:-}" ]]; then
    # Try to load from project .env
    if [[ -f ./.env ]]; then
      TS_DSN=$(grep -E '^TS_DSN=' ./.env | sed 's/^TS_DSN=//' | tr -d '\r')
    fi
  fi
  if [[ -z "${TS_DSN:-}" ]]; then
    echo "TS_DSN not set. Export TS_DSN or add to .env" >&2; exit 1
  fi
  SAFE_DSN="${TS_DSN//\?sslmode=disable/}"
  if [[ "$mode" == "schema" ]]; then
    OUT="$OUT_DIR/ecoanp_remote_schema_${TS}.sql"
    echo "Backing up REMOTE (schema-only) $SAFE_DSN to $OUT"
    docker exec ecoanp_timescaledb pg_dump --schema-only --no-owner --no-privileges \
      -N information_schema -N pg_catalog -N _timescaledb_% \
      "$TS_DSN" -f "/tmp/ecoanp_remote_schema_${TS}.sql"
    docker cp ecoanp_timescaledb:/tmp/ecoanp_remote_schema_${TS}.sql "$OUT_DIR/"
    docker exec ecoanp_timescaledb rm -f "/tmp/ecoanp_remote_schema_${TS}.sql"
    echo "OK: $OUT"
  else
    OUT="$OUT_DIR/ecoanp_remote_full_${TS}.sql"
    echo "Backing up REMOTE (full) $SAFE_DSN to $OUT"
    docker exec ecoanp_timescaledb pg_dump --no-owner --no-privileges \
      "$TS_DSN" -f "/tmp/ecoanp_remote_full_${TS}.sql"
    docker cp ecoanp_timescaledb:/tmp/ecoanp_remote_full_${TS}.sql "$OUT_DIR/"
    docker exec ecoanp_timescaledb rm -f "/tmp/ecoanp_remote_full_${TS}.sql"
    echo "OK: $OUT"
  fi
else
  echo "Unknown target: $target" >&2; exit 1
fi
