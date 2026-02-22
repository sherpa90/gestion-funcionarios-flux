FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set default environment variables for build
ENV DEBUG=True
ENV SECRET_KEY=dev-secret-key-for-docker-build-only
ENV DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
ENV SQL_DATABASE=sgpal_db
ENV SQL_USER=sgpal_user
ENV SQL_PASSWORD=sgpal_password
ENV SQL_HOST=localhost
ENV SQL_PORT=5432

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

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=appuser:appgroup . /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create logs directory and ensure permissions
RUN mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Run collectstatic with dummy secret key if needed, or rely on settings default
RUN python manage.py collectstatic --noinput

# Make entrypoint executable (already handled by COPY but ensuring)
# ENTRYPOINT is executed relative to WORKDIR
ENTRYPOINT ["/app/entrypoint.sh"]

