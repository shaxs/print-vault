#!/bin/sh

# This script waits for the database to be ready before starting the web server.

# The until loop will continue until the command `pg_isready` succeeds.
until pg_isready -h db -p 5432 -U postgres; do
  echo "Waiting for the database to be ready..."
  sleep 2
done

echo "Database is ready."

# Run database migrations to ensure the schema is up to date.
echo "Running database migrations..."
python manage.py migrate --settings=backend.production

# Collect all static files into the designated directory.
echo "Collecting static files..."
python manage.py collectstatic --settings=backend.production --noinput

# Start the Gunicorn web server.
echo "Starting Gunicorn server..."
python -m gunicorn backend.wsgi:application --bind 0.0.0.0:8000