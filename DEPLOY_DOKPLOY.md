# Guía de Despliegue en Dokploy

Esta guía detalla cómo desplegar el proyecto SGPAL en Dokploy de forma segura.

## Requisitos Previos

- Tener acceso a una instancia de Dokploy.
- Tener el código subido a un repositorio Git (GitHub/GitLab).
- Un dominio configurado en Dokploy (opcional, pero recomendado para HTTPS).

## Paso 1: Configuración del Repositorio

Asegúrate de que tu repositorio tenga la siguiente estructura (ya configurada por el asistente):
- `Dockerfile` (optimizado para producción, sin secretos).
- `.dockerignore` (para evitar subir archivos sensibles al build context).
- `entrypoint.sh` (para manejar migraciones y arranque).

## Paso 2: Crear Base de Datos en Dokploy

1. En el panel de Dokploy, ve a tu proyecto.
2. Haz clic en **"Create Service"** -> **"Database"**.
3. Selecciona **PostgreSQL**.
4. Configura el nombre (ej. `sgpal-db`) y la contraseña.
5. Dokploy te dará los detalles de conexión interna (Host, Port, User, Password, Database). **Guárdalos**.

## Paso 3: Crear la Aplicación

1. En el mismo proyecto, haz clic en **"Create Service"** -> **"Application"**.
2. Selecciona tu proveedor de Git (GitHub) y el repositorio.
3. Configura la rama (ej. `main` o `master`).
4. En **"Build Type"**, selecciona **Dockerfile**.
5. Asegúrate de que el **Docker Context** sea `/` y el **Docker Path** sea `./Dockerfile`.

## Paso 4: Variables de Entorno (Environment)

Ve a la pestaña **"Environment"** de tu aplicación y agrega las siguientes variables. **NUNCA** subas el archivo `.env` al repositorio.

| Variable | Valor Recomendado / Descripción |
|----------|---------------------------------|
| `DEBUG` | `False` (IMPORTANTE para seguridad) |
| `SECRET_KEY` | Genera una clave larga y aleatoria |
| `DJANGO_ALLOWED_HOSTS` | `tu-dominio.com,localhost` (separados por comas) |
| `CSRF_TRUSTED_ORIGINS` | `https://tu-dominio.com` (IMPORTANTE: Debe incluir el protocolo https://) |
| `SQL_ENGINE` | `django.db.backends.postgresql` |
| `SQL_DATABASE` | Nombre de la DB creada en Paso 2 |
| `SQL_USER` | Usuario de la DB |
| `SQL_PASSWORD` | Contraseña de la DB |
| `SQL_HOST` | Host interno de la DB (ej. `sgpal-db-myx9xn`) |
| `SQL_PORT` | `5432` |
| `EMAIL_HOST` | `smtp.gmail.com` (o tu proveedor) |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | Tu correo |
| `EMAIL_HOST_PASSWORD` | Tu contraseña de aplicación |
| `SENTRY_DSN` | URL de Sentry (opcional para monitoreo) |

## Paso 5: Persistencia (Volumes)

Para que los archivos subidos (media) y los archivos estáticos persistan entre despliegues:

1. Ve a la pestaña **"Volumes"**.
2. Agrega un volumen para Media:
   - **Host Path:** (Déjalo vacío para que Dokploy use docker volumes, o especifica una ruta si prefieres bind mounts)
   - **Mount Path:** `/app/media`
3. (Opcional) Volumen para Static:
   - **Mount Path:** `/app/staticfiles`
   - *Nota*: Whitenoise está configurado para servir estáticos, pero un volumen asegura que no se pierdan si se generan en runtime (aunque collectstatic corre en build).

## Paso 6: Despliegue

1. Ve a la pestaña **"Deployments"**.
2. Haz clic en **"Deploy"**.
3. Revisa los logs para asegurarte de que:
   - La imagen se construye correctamente.
   - Las migraciones se ejecutan (`Running migrations...`).
   - Gunicorn inicia correctamente.

## Troubleshooting

- **Error de conexión a DB:** Verifica `SQL_HOST`. En redes Docker internas de Dokploy, usa el nombre del servicio de base de datos.
- **Error CSRF:** Verifica que `CSRF_TRUSTED_ORIGINS` incluya `https://tu-dominio.com`.
- **Archivos Estáticos no cargan:** Verifica que `Whitenoise` esté activo (ya configurado en `settings.py`).
