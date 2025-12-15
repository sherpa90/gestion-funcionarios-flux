#!/bin/bash
# Wait for db
while ! nc -z db 5432; do
  echo "Waiting for database..."
  sleep 1
done

# Run migrations
python manage.py migrate

# Start gunicorn
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000