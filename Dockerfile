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
ENV SECRET_KEY=ZXXBlDpBklnF3J1VkWJA9kACXn396D-0oxel35abYR4AkO8t3fG8qW3rQpgoTJNIYXg
ENV DJANGO_ALLOWED_HOSTS=tramites.losalercespuertomontt.cl,www.tramites.losalercespuertomontt.cl,losalercespuertomontt.cl,localhost,127.0.0.1
ENV SQL_ENGINE=django.db.backends.postgresql
ENV SQL_DATABASE=sgpal_production
ENV SQL_USER=sgpal_prod_user
ENV SQL_PASSWORD=Linuxhbk619047
ENV SQL_HOST=sgpal-db
ENV SQL_PORT=5432
ENV EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
ENV EMAIL_HOST=smtp.gmail.com
ENV EMAIL_PORT=587
ENV EMAIL_USE_TLS=True
ENV EMAIL_USE_SSL=False
ENV EMAIL_HOST_USER=mrosas@losalercespuertomontt.cl
ENV EMAIL_HOST_PASSWORD="bliw uumf uqtc kvai"
ENV DEFAULT_FROM_EMAIL=noreply@tramites.losalercespuertomontt.cl

RUN python manage.py collectstatic --noinput

# Make entrypoint executable
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
