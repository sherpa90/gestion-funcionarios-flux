#!/bin/bash
set -e

# Default to sgpal-db-myx9xn if SQL_HOST not set (Dokploy production)
SQL_HOST=${SQL_HOST:-sgpal-db-myx9xn}
SQL_PORT=${SQL_PORT:-5432}

# Wait for db
echo "Waiting for database at $SQL_HOST:$SQL_PORT..."
while ! nc -z $SQL_HOST $SQL_PORT; do
  sleep 1
done
echo "Database started"

# Run migrations
python manage.py migrate --noinput

# Start gunicorn
# Ensure gunicorn is installed or fallback/fail early
if ! command -v gunicorn &> /dev/null; then
    echo "gunicorn could not be found, installing..."
    pip install gunicorn
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3