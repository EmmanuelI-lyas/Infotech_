#!/bin/sh
set -e

superset db upgrade
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME:-admin}" \
  --firstname "${SUPERSET_ADMIN_FIRSTNAME:-Superset}" \
  --lastname "${SUPERSET_ADMIN_LASTNAME:-Admin}" \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@superset.com}" \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true

superset init

# Optionally auto-register the Titanic data source in Superset.
if [ "${AUTO_CREATE_TITANIC_DB:-true}" = "true" ]; then
  superset set_database_uri \
    --database_name "${SUPERSET_TITANIC_DB_DISPLAY_NAME:-Titanic PostgreSQL}" \
    --uri "postgresql+psycopg2://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-titanic_db}" || true
fi

# Optional imports for existing exported Superset assets.
if [ -f /app/imports/dashboards.zip ]; then
  superset import-dashboards --path /app/imports/dashboards.zip || true
fi

if [ -f /app/imports/datasets.zip ]; then
  superset import-datasources --path /app/imports/datasets.zip || true
fi
