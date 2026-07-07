#!/bin/sh

# This script waits for the database to be ready, then waits for the
# `backend` service to finish applying migrations (so django_q's own
# tables are guaranteed to exist), before starting the Django-Q worker.

until pg_isready -h db -p 5432 -U postgres; do
  echo "Waiting for the database to be ready..."
  sleep 2
done

echo "Database is ready."

echo "Waiting for migrations to be applied..."
until python manage.py migrate --settings=backend.production --check >/dev/null 2>&1; do
  echo "Migrations not yet applied, waiting..."
  sleep 2
done

echo "Starting Django-Q cluster..."
exec python manage.py qcluster --settings=backend.production
