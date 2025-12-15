# 🚀 Despliegue en Dockge - SGPAL

Guía completa para desplegar el Sistema de Gestión de Personal y Asistencia Laboral en Dockge.

## 📋 Prerrequisitos

- **Dockge** instalado y funcionando
- **Acceso SSH** al servidor donde corre Dockge
- **Dominio** (opcional pero recomendado)

## 📁 Paso 1: Preparar el Proyecto

### Opción A: Desde GitHub (Recomendado)
```bash
# Clonar el repositorio
cd /opt/stacks/
git clone https://github.com/TU_USUARIO/sgpal.git sgpal-stack
cd sgpal-stack

# Crear directorio para datos persistentes
mkdir -p data/media data/backups
```

### Opción B: Subir Archivos Manualmente
```bash
# Crear directorio del stack
mkdir -p /opt/stacks/sgpal-stack
cd /opt/stacks/sgpal-stack

# Subir todos los archivos del proyecto aquí
# (usando SCP, SFTP, o tu método preferido)
```

## ⚙️ Paso 2: Configurar Variables de Entorno

```bash
# Copiar archivo de producción
cp .env.production .env

# Editar con tus valores reales
nano .env
```

**Variables críticas a configurar:**
```bash
SECRET_KEY=tu-clave-secreta-muy-larga-y-segura
DJANGO_ALLOWED_HOSTS=tramites.losalercespuertomontt.cl,www.tramites.losalercespuertomontt.cl
SQL_PASSWORD=contraseña_segura_para_postgres
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
```

## 🐳 Paso 3: Configurar en Dockge

### 3.1 Crear Nuevo Stack
1. Abrir **Dockge** en tu navegador
2. Hacer clic en **"Add Stack"**
3. **Name**: `SGPAL`
4. **Description**: `Sistema de Gestión de Personal y Asistencia Laboral`

### 3.2 Configurar Stack
```yaml
# Usar el contenido de docker-compose.dockge.yml
# Copiar y pegar el contenido completo
```

### 3.3 Variables de Entorno
En la sección **Environment** de Dockge, agregar:
```
.env
```

### 3.4 Paths y Volúmenes
Asegurarse de que los paths sean correctos:
- **Compose Path**: `/opt/stacks/sgpal-stack/docker-compose.dockge.yml`
- **Environment Path**: `/opt/stacks/sgpal-stack/.env`

## 🚀 Paso 4: Desplegar

1. Hacer clic en **"Deploy"** en Dockge
2. Esperar a que se construya la imagen (primera vez toma tiempo)
3. Verificar que ambos contenedores estén **"Running"**

## 🔧 Paso 5: Configuración Inicial

### 5.1 Ejecutar Migraciones
```bash
# Conectarse al contenedor web
docker exec -it sgpal-web bash

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Salir del contenedor
exit
```

### 5.2 Importar Datos de Prueba (Opcional)
```bash
# Si quieres datos de prueba
docker exec -it sgpal-web bash
python manage.py setup_data
exit
```

## 🌐 Paso 6: Configurar CloudPanel (Proxy Reverso)

CloudPanel incluye proxy reverso integrado. Configura el sitio web:

### 6.1 Crear Sitio en CloudPanel

1. **Accede a CloudPanel** (tu panel de control)
2. **Ve a "Sites"** → **"Create Site"**
3. **Configura:**
   - **Domain**: `tramites.losalercespuertomontt.cl`
   - **Site Type**: `Reverse Proxy` (o `PHP` si tienes opción)
   - **Reverse Proxy URL**: `http://127.0.0.1:8000`

### 6.2 Configuración SSL

1. **En CloudPanel**, ve a tu sitio creado
2. **SSL** → **"Let's Encrypt"**
3. **Agrega los dominios:**
   - `tramites.losalercespuertomontt.cl`
   - `www.tramites.losalercespuertomontt.cl`
4. **Haz clic en "Create Certificate"**

### 6.3 Configuración Avanzada (Opcional)

Si necesitas configuración personalizada, edita el archivo de configuración de Nginx en CloudPanel:

```nginx
# Configuración personalizada para SGPAL
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Buffers
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
}

# Static files (si usas archivos locales)
location /static/ {
    alias /opt/stacks/sgpal-stack/staticfiles/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Media files
location /media/ {
    alias /opt/stacks/sgpal-stack/data/media/;
    expires 1M;
    add_header Cache-Control "public";
}
```

## 🔒 Paso 7: SSL con CloudPanel

CloudPanel maneja automáticamente los certificados SSL:

### 7.1 Configuración SSL Automática

1. **En CloudPanel**, selecciona tu sitio
2. **Ve a la pestaña "SSL"**
3. **Activa "Let's Encrypt"**
4. **Agrega los dominios:**
   - `tramites.losalercespuertomontt.cl`
   - `www.tramites.losalercespuertomontt.cl`
5. **CloudPanel renovará automáticamente** los certificados

### 7.2 Verificación SSL

- **CloudPanel** se encarga de la renovación automática
- **No necesitas comandos manuales** de certbot
- **Los certificados se renuevan** automáticamente antes de expirar

## 📊 Paso 8: Monitoreo y Mantenimiento

### Health Checks
- **URL**: `https://tu-dominio.com/health/`
- **Métricas**: CPU, Memoria, Base de datos, Aplicación

### Backups
```bash
# Backup de base de datos
docker exec sgpal-db pg_dump -U sgpal_prod_user sgpal_prod > /opt/stacks/sgpal-stack/data/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Backup de archivos media
tar -czf /opt/stacks/sgpal-stack/data/backups/media_$(date +%Y%m%d_%H%M%S).tar.gz /opt/stacks/sgpal-stack/data/media/
```

### Logs
```bash
# Ver logs de la aplicación
docker logs -f sgpal-web

# Ver logs de base de datos
docker logs -f sgpal-db
```

## 🔧 Paso 9: Troubleshooting

### Problema: Contenedor no inicia
```bash
# Ver logs detallados
docker-compose -f docker-compose.dockge.yml logs

# Verificar variables de entorno
docker exec sgpal-web env | grep -E "(SQL|DJANGO|SECRET)"
```

### Problema: Error de conexión a BD
```bash
# Verificar conectividad
docker exec sgpal-web nc -zv sgpal-db 5432

# Verificar credenciales
docker exec sgpal-db psql -U sgpal_prod_user -d sgpal_prod -c "SELECT version();"
```

### Problema: Error 502 Bad Gateway
```bash
# Verificar que la app esté corriendo
docker exec sgpal-web curl -f http://localhost:8000/health/

# Verificar Nginx configuración
sudo nginx -t
```

## 🎯 URLs de Acceso

- **Aplicación**: `https://tramites.losalercespuertomontt.cl`
- **Admin Django**: `https://tramites.losalercespuertomontt.cl/admin/`
- **Health Check**: `https://tramites.losalercespuertomontt.cl/health/`

## 📞 Usuario Administrador

- **Email**: El que configuraste en `createsuperuser`
- **Password**: El que configuraste en `createsuperuser`

## 🚀 Próximos Pasos

1. **Configurar usuarios reales** en el sistema
2. **Importar datos históricos** si los tienes
3. **Configurar backups automáticos**
4. **Monitoreo avanzado** con Grafana/Prometheus
5. **CDN** para archivos estáticos si es necesario

---

**¡Tu SGPAL está listo para producción!** 🎉