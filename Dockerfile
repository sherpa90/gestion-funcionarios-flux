FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBUG=True
ENV SECRET_KEY=build-key-only
ENV DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# 1. Dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev python3-cffi python3-brotli \
    libpango1.0-dev libglib2.0-0 libgstrtspserver-1.0-0 \
    libharfbuzz-dev libgdk-pixbuf-2.0-0 shared-mime-info \
    fonts-freefont-ttf libharfbuzz-subset0 libjpeg-dev \
    libopenjp2-7-dev libmemcached-dev zlib1g-dev netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 2. Crear usuario y grupo (ID 1000 es el estándar)
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --ingroup appgroup appuser

# 3. Preparar el directorio de trabajo ANTES de copiar nada
WORKDIR /app

# 4. Crear carpetas críticas como ROOT y darles permisos totales (777)
# Esto asegura que CUALQUIER usuario pueda escribir en ellas
RUN mkdir -p /app/logs /app/media /app/staticfiles && \
    chmod -R 777 /app/logs /app/media /app/staticfiles && \
    chown -R appuser:appgroup /app

# 5. Instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copiar el código fuente forzando el dueño
COPY --chown=appuser:appgroup . .

# 7. Asegurar permisos finales
RUN chmod +x /app/entrypoint.sh && \
    chown appuser:appgroup /app/entrypoint.sh

# CAMBIO AL USUARIO NO-ROOT
USER appuser

# 8. Tareas de Django
RUN python manage.py collectstatic --noinput

ENTRYPOINT ["/app/entrypoint.sh"]
