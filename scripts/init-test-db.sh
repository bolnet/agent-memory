#!/bin/bash
# Creates the test database alongside the production database.
# Mounted as /docker-entrypoint-initdb.d/init-test-db.sh in docker-compose.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE memwright_test OWNER $POSTGRES_USER;
EOSQL
