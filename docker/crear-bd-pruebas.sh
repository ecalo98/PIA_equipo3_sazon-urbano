#!/bin/sh
# Se ejecuta solo al crear el volumen de PostgreSQL por primera vez.
# Crea la base ${POSTGRES_DB}_test para que las pruebas no toquen los datos de la app.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "CREATE DATABASE \"${POSTGRES_DB}_test\" OWNER \"$POSTGRES_USER\";"
