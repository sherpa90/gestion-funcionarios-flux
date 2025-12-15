FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies for WeasyPrint and Postgres
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libmemcached-dev \
    zlib1g-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Copy environment file
COPY .env /app/.env

# Set environment variables for collectstatic (with defaults)
ENV DEBUG=0
ENV SECRET_KEY=change-this-in-production
ENV DJANGO_ALLOWED_HOSTS="localhost 127.0.0.1 [::1] tramites.losalercespuertomontt.cl"
ENV SQL_ENGINE=django.db.backends.postgresql
ENV SQL_DATABASE=sgpal_db
ENV SQL_USER=sgpal_user
ENV SQL_PASSWORD=change_this_secure_password
ENV SQL_HOST=db
ENV SQL_PORT=5432

RUN python manage.py collectstatic --noinput

# Make entrypoint executable
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
