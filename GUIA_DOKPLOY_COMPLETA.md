# 🚀 GUÍA COMPLETA: Despliegue SGPAL en Dokploy

Esta guía te llevará de cero a producción completa. Siguela en orden.

---

## 📋 ÍNDICE

1. [Requisitos Previos](#1-requisitos-previos)
2. [Subir Código a GitHub](#2-subir-código-a-github)
3. [Configurar Dominio](#3-configurar-dominio)
4. [Crear Proyecto en Dokploy](#4-crear-proyecto-en-dokploy)
5. [Crear Base de Datos PostgreSQL](#5-crear-base-de-datos-postgresql)
6. [Crear Aplicación Web](#6-crear-aplicación-web)
7. [Configurar Variables de Entorno](#7-configurar-variables-de-entorno)
8. [Configurar Volúmenes](#8-configurar-volúmenes)
9. [Configurar Dominio y HTTPS](#9-configurar-dominio-y-https)
10. [Desplegar](#10-desplegar)
11. [Verificar Funcionamiento](#11-verificar-funcionamiento)
12. [Mantenimiento](#12-mantenimiento)

---

## 1. REQUISITOS PREVIOS

### 1.1 Cuenta en Dokploy

Si no tienes cuenta en Dokploy:

1. Ve a **https://dokploy.com**
2. Click en **"Get Started"** o **"Sign Up"**
3. Regístrate con:
   - Email
   - Contraseña
4. Verifica tu email

### 1.2 Cuenta en GitHub

1. Ve a **https://github.com**
2. Regístrate o inicia sesión
3. Crea un nuevo repositorio:
   - Nombre: `sgpal`
   - Tipo: **Private**
   - NO inicialices con README

### 1.3 Dominio (Opcional pero recomendado)

Si tienes un dominio:
- Apunta los DNS a tu servidor Dokploy
- Si no tienes, puedes usar el subdomain de Dokploy

---

## 2. SUBIR CÓDIGO A GITHUB

### 2.1 Generar Token de Acceso Personal

1. Ve a: **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Configura:
   
   ```
   Note: SGPAL Deploy
   Expiration: 90 days
   Select scopes: ✅ repo
   ```
4. Click **"Generate token"**
5. **COPIA EL TOKEN** (tiene forma `ghp_xxxxxxxxxxxx`)

### 2.2 Configurar Git Local

En tu terminal, ejecuta:

```bash
# Ir a la carpeta del proyecto
cd /Users/mrosas/Documents/sgpal

# Ver estado actual
git status

# Configurar nombre y email (si no lo has hecho)
git config --global user.name "Marcelo Rosas"
git config --global user.email "mrosas@losalercespuertomontt.cl"

# Establecer el remote con tu token
# Reemplaza TU_TOKEN con el token que copiaste
git remote set-url origin https://ghp_TU_TOKEN@github.com/sherpa90/sgpal.git

# Verificar remote
git remote -v
# Debe mostrar: origin  https://ghp_xxx@github.com/sherpa90/sgpal.git (fetch)
#               origin  https://ghp_xxx@github.com/sherpa90/sgpal.git (push)
```

### 2.3 Hacer Push

```bash
# Subir código a GitHub
git push -u origin main
```

**Si pide usuario y contraseña:**
- Usuario: Tu nombre de usuario de GitHub
- Contraseña: **Usa el token** (no tu password de GitHub)

✅ **Verifica en GitHub** que el código subió correctamente.

---

## 3. CONFIGURAR DOMINIO

### 3.1 Si tienes dominio propio

1. Ve a tu proveedor de dominio (Namecheap, GoDaddy, etc.)
2. Crea un registro **A**:
   - Host: `@` o `tu-dominio.com`
   - Value: `IP_DE_TU_SERVIDOR_DOKPLOY`
3. Espera hasta 24 horas (propagación DNS)

### 3.2 Si NO tienes dominio

Dokploy te dará un subdomain gratuito:
- Format: `tu-proyecto.dokploy.app`

---

## 4. CREAR PROYECTO EN DOKPLOY

### 4.1 Crear Proyecto

1. Inicia sesión en **https://dokploy.com**
2. En el dashboard, click en **"New Project"**
3. Configura:

| Campo | Valor |
|-------|-------|
| **Project Name** | `sgpal` |
| **Description** | Sistema de Gestión de Personal |

4. Click **"Create Project"**

---

## 5. CREAR BASE DE DATOS POSTGRESQL

### 5.1 Crear el servicio de base de datos

1. En tu proyecto Dokploy, click en **"Create Service"**
2. Selecciona **"Database"**
3. Configura:

| Campo | Valor |
|-------|-------|
| **Name** | `sgpal-db` |
| **Database** | `sgpal_db` |
| **User** | `sgpal_user` |
| **Password** | `Sgpal2025Secure!` |
| **Version** | `15` o `latest` |

4. Click **"Create Database"**

### 5.2 Obtener datos de conexión

Una vez creada, Dokploy te mostrará los datos de conexión. **Guarda estos datos**:

```
Host: dokploy-postgres-xxx (algo así)
Port: 5432
User: sgpal_user
Password: Sgpal2025Secure!
Database: sgpal_db
```

---

## 6. CREAR APLICACIÓN WEB

### 6.1 Crear la aplicación

1. En tu proyecto Dokploy, click en **"Create Service"**
2. Selecciona **"Application"**
3. Configura:

| Campo | Valor |
|-------|-------|
| **Name** | `sgpal-web` |
| **Description** | Aplicación web SGPAL |

4. Click **"Next"**

### 6.2 Configurar Git

1. **Provider**: Selecciona **GitHub**
2. **Repository**: Busca y selecciona `sgpal` o `sherpa90/sgpal`
3. **Branch**: `main`
4. Click **"Next"**

### 6.3 Configurar Build

1. **Build Type**: Selecciona **Dockerfile**
2. **Docker Context**: `/`
3. **Dockerfile Path**: `./Dockerfile`
4. **Port**: `8000`
5. Click **"Next"**

### 6.4 Configuración de instance

1. **Instance Type**: 
   - **1GB RAM / 1 CPU** (mínimo para desarrollo)
   - **2GB RAM / 2 CPU** (recomendado producción)

2. Click **"Create Application"**

---

## 7. CONFIGURAR VARIABLES DE ENTORNO

### 7.1 Acceder a Environment

1. En tu aplicación `sgpal-web`, busca la pestaña **"Environment"**
2. Click en **"Add Variable"**

### 7.2 Agregar Variables

Agrega una por una:

| Variable | Valor | Notas |
|----------|-------|-------|
| `DEBUG` | `False` | ⚠️ IMPORTANTE |
| `SECRET_KEY` | `genera-una-clave-muy-larga-y-segura-aqui` | Genera una clave larga con caracteres especiales |
| `DJANGO_ALLOWED_HOSTS` | `sgpal.tu-dominio.com,www.sgpal.tu-dominio.com,localhost` | Tu dominio |
| `CSRF_TRUSTED_ORIGINS` | `https://sgpal.tu-dominio.com` | Tu dominio con https |
| `SQL_ENGINE` | `django.db.backends.postgresql` | |
| `SQL_DATABASE` | `sgpal_db` | El nombre de tu DB |
| `SQL_USER` | `sgpal_user` | El usuario de tu DB |
| `SQL_PASSWORD` | `Sgpal2025Secure!` | La contraseña de tu DB |
| `SQL_HOST` | `dokploy-postgres-xxx` | El host de tu DB (ver paso 5.2) |
| `SQL_PORT` | `5432` | |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` | |
| `EMAIL_HOST` | `smtp.gmail.com` | O tu proveedor |
| `EMAIL_PORT` | `587` | |
| `EMAIL_USE_TLS` | `True` | |
| `EMAIL_HOST_USER` | `tu-email@gmail.com` | |
| `EMAIL_HOST_PASSWORD` | `tu-app-password` | Necesitas generar app password en Google |
| `DEFAULT_FROM_EMAIL` | `noreply@tu-dominio.com` | |
| `SESSION_COOKIE_SECURE` | `True` | |
| `CSRF_COOKIE_SECURE` | `True` | |
| `SECURE_HSTS_SECONDS` | `31536000` | |
| `SECURE_HSTS_PRELOAD` | `True` | |

### 7.3 Generar SECRET_KEY

Para generar una clave segura, puedes usar:

```bash
# En Python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

O usa este comando:
```
# Copia esta clave (ejemplo):
django-insecure-k8s2m9v5xj1h4p7w0n3q6t8y1z5a4b7c9e1f2g3h4i5j6k7l8m9n0p1q
```

---

## 8. CONFIGURAR VOLÚMENES

### 8.1 Acceder a Volumes

En tu aplicación, busca la pestaña **"Volumes"**

### 8.2 Agregar Volumen para Media

1. Click en **"Add Volume"**
2. Configura:

| Campo | Valor |
|-------|-------|
| **Type** | `Volume` |
| **Name** | `sgpal-media` |
| **Mount Path** | `/app/media` |

3. Click **"Save"**

### 8.3 Volumen para Staticfiles (Opcional)

Si prefieres que los archivos estáticos persistan:

| Campo | Valor |
|-------|-------|
| **Type** | `Volume` |
| **Name** | `sgpal-static` |
| **Mount Path** | `/app/staticfiles` |

---

## 9. CONFIGURAR DOMINIO Y HTTPS

### 9.1 Agregar Dominio

1. En tu aplicación, busca la pestaña **"Domains"** o **"Domain"**
2. Click en **"Add Domain"**
3. Ingresa tu dominio: `sgpal.tu-dominio.com`
4. Click **"Save"**

### 9.2 Habilitar HTTPS (SSL)

1. Busca la opción **"SSL"** o **"HTTPS"**
2. Habilita **"Force SSL"** o **"Redirect HTTP to HTTPS"**
3. Click en **"Request Certificate"**
4. Espera unos minutos hasta que se aprovisione

✅ **Verifica** que el candado verde aparezca en el navegador

---

## 10. DESPLEGAR

### 10.1 Ejecutar Despliegue

1. En tu aplicación, busca la pestaña **"Deployments"**
2. Click en **"Deploy"** (puede ser verde o azul)
3. Observa los logs

### 10.2 Monitorear Logs

Durante el despliegue, verás logs como:

```
#1 [1/10] FROM docker.io/library/python:3.12-slim
#2 [2/10] WORKDIR /app
...
Running migrations...
  Applying asistencia.0001_initial... OK
  Applying users.0001_initial... OK
...
System check identified no issues (0 silenced).
[2024-01-01 12:00:00] [INFO] Starting gunicorn 21.0.1
[2024-01-01 12:00:00] [INFO] Listening at: http://0.0.0.0:8000
```

✅ **Busca** en los logs:
- `Running migrations...` - Debe decir `OK`
- `Starting gunicorn` - Indica que el servidor arrancó
- Sin errores rojos al final

### 10.3 Si hay errores

1. Revisa los **logs de error**
2. Common issues:

| Error | Solución |
|-------|----------|
| `connection refused` | Revisa `SQL_HOST` |
| `ModuleNotFoundError` | Falta dependencia en requirements.txt |
| `permission denied` | Revisa permisos de archivos |
| `database does not exist` | Crea la DB primero |

---

## 11. VERIFICAR FUNCIONAMIENTO

### 11.1 Probar la aplicación

Abre en tu navegador:

```
https://sgpal.tu-dominio.com
```

### 11.2 Probar el Admin

```
https://sgpal.tu-dominio.com/admin
```

Usa las credenciales que creaste:
- Email: `mrosas@losalercespuertomontt.cl`
- Contraseña: `Sgpal2025!`

### 11.3 Pruebas de funcionalidad

| Página | URL | Esperado |
|--------|-----|----------|
| Login | `/accounts/login/` | Formulario de login |
| Dashboard | `/admin/` | Panel de admin |
| Asistencia | `/asistencia/` | Gestión de asistencia |
| Permisos | `/permisos/` | Solicitar permisos |

---

## 12. MANTENIMIENTO

### 12.1 Actualizar el proyecto

Cuando hagas cambios en tu código:

```bash
# En tu电脑
git add .
git commit -m "Descripción del cambio"
git push origin main
```

Luego en Dokploy:
1. Ve a tu aplicación
2. Click en **"Redeploy"** o **"Deploy"**
3. Los cambios se aplicarán automáticamente

### 12.2 Ver logs en producción

En Dokploy, pestaña **"Logs** para ver:
- Errores de Python
- Access logs
- Error logs

### 12.3 Backup de Base de Datos

Dokploy puede hacer backups automáticos. Busca en tu DB:
- **"Backups"** → Habilita backups automáticos

### 12.4 Monitoreo

Busca en tu aplicación:
- **"Metrics"** - Uso de CPU, RAM
- **"Alerts"** - Configurar alertas

---

## 📞 TROUBLESHOOTING

### Error: "Bad Gateway" o "502"

- El contenedor puede estar reiniciando
- Revisa los logs
- Verifica que el puerto sea 8000

### Error: "Too Many Connections"

- PostgreSQL tiene límite de conexiones
- Reduce workers de Gunicorn a 2

### Error: "Static file not found"

- Ejecuta: `docker-compose exec web python manage.py collectstatic`
- O verifica el volumen de staticfiles

### Error: "CSRF verification failed"

- Asegúrate que `CSRF_TRUSTED_ORIGINS` incluya `https://tu-dominio.com`

---

## ✅ CHECKLIST FINAL

Antes de considerar el despliegue completo:

- [ ] Código subido a GitHub
- [ ] Base de datos PostgreSQL creada
- [ ] Aplicación creada en Dokploy
- [ ] Variables de entorno configuradas (DEBUG=False)
- [ ] Volúmenes configurados
- [ ] Dominio configurado
- [ ] SSL/HTTPS habilitado
- [ ] Despliegue exitoso (sin errores)
- [ ] Login funciona
- [ ] Admin Django funciona

---

## 🎉 ¡Felicitaciones!

Tu aplicación SGPAL está desplegada en producción. 

**Próximos pasos:**
1. Configura el email correctamente
2. Crea usuarios adicionales
3. Personaliza según necesidades

---

¿Necesitas ayuda con algún paso específico?