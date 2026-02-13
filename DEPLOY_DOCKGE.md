# 🚀 Despliegue en Dockge - SGPAL

Guía para desplegar SGPAL en tu servidor Debian con Dockge y CloudPanel.

## 📋 Tu Configuración Actual

- ✅ **Servidor Debian** con Dockge corriendo
- ✅ **CloudPanel** configurado en `www.losalercespuertomontt.cl`
- ✅ **Dominio** `tramites.losalercespuertomontt.cl` configurado en CloudFlare
- ✅ **Proxy reverso** listo para recibir conexiones en puerto 8000

## 🔒 Seguridad Corregida

**Importante**: Se han removido las credenciales expuestas del repositorio. Ahora usa `.env.production.example` como template seguro.

## 📋 Prerrequisitos

- **Acceso SSH** a tu servidor Debian
- **Proyecto SGPAL** subido al servidor (en `/opt/stacks/sgpal-stack/`)

## ⚡ Despliegue en tu Servidor (4 pasos)

### Paso 1: Subir el proyecto a tu servidor
```bash
# Conectar por SSH a tu servidor Debian
ssh usuario@tu-servidor

# Ir al directorio de stacks de Dockge
cd /opt/stacks/

# Crear directorio para SGPAL
mkdir -p sgpal-stack
cd sgpal-stack

# Subir todos los archivos del proyecto aquí
# (usando SCP, SFTP, o tu método preferido)
```

### Paso 2: Configurar el proyecto
```bash
# Ejecutar configuración automática
./setup_dockge.sh
```

### Paso 3: Configurar variables de entorno
```bash
# Editar el archivo .env generado
nano .env
```

**Variables críticas que DEBES verificar/cambiar:**
```bash
SECRET_KEY=tu-clave-secreta-muy-larga-y-segura-aqui
SQL_PASSWORD=tu-contraseña-segura-para-postgres
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
```

### Paso 4: Desplegar en Dockge
1. **Abrir Dockge** en tu navegador (normalmente `http://tu-servidor:5000`)
2. **Hacer clic en "Add Stack"**
3. **Nombre**: `SGPAL`
4. **Pegar** el contenido completo de `docker-compose.dockge.yml`
5. **Hacer clic en "Deploy"**

¡Listo! SGPAL estará disponible en `tramites.losalercespuertomontt.cl` a través de CloudPanel.

## 🔧 Configuración Inicial (Después del despliegue)

### Crear Superusuario
```bash
# Conectarse al contenedor web
docker exec -it sgpal-web bash

# Crear superusuario
python manage.py createsuperuser

# Salir
exit
```

### Configurar Proxy Reverso en CloudPanel
1. **Accede a CloudPanel**
2. **Ve a "Sites"** → **"Create Site"**
3. **Configura:**
   - **Domain**: `tramites.losalercespuertomontt.cl`
   - **Site Type**: `Reverse Proxy`
   - **Reverse Proxy URL**: `http://127.0.0.1:8000`

### Configurar SSL
1. **En CloudPanel**, selecciona el sitio creado
2. **Ve a "SSL"** → **"Let's Encrypt"**
3. **Agrega el dominio** `tramites.losalercespuertomontt.cl`
4. **CloudPanel manejará automáticamente** la renovación de certificados

### Verificar que funciona
- **Aplicación**: `https://tramites.losalercespuertomontt.cl`
- **Admin**: `https://tramites.losalercespuertomontt.cl/admin/`
- **Health Check**: `https://tramites.losalercespuertomontt.cl/health/`

## 🌐 Configuración con Proxy Reverso (Opcional)

Si usas un proxy reverso (como Nginx, CloudPanel, etc.), configura:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 🔧 Monitoreo y Troubleshooting

### Health Check
Visita `http://tu-servidor:8000/health/` para verificar el estado del sistema.

### Ver Logs
```bash
# Logs de la aplicación
docker logs -f sgpal-web

# Logs de la base de datos
docker logs -f sgpal-db
```

### Problemas Comunes
- **Contenedor no inicia**: Verifica las variables en `.env`
- **Error de BD**: Revisa que PostgreSQL esté corriendo con `docker ps`
- **Puerto ocupado**: Cambia el puerto 8000 en `docker-compose.dockge.yml`

## 🎯 Acceso al Sistema

Después del despliegue y configuración de CloudPanel, accede a:

- **Aplicación**: `https://tramites.losalercespuertomontt.cl`
- **Panel Admin**: `https://tramites.losalercespuertomontt.cl/admin/`
- **Health Check**: `https://tramites.losalercespuertomontt.cl/health/`

## 📞 Primer Inicio de Sesión

1. Ve a `https://tramites.losalercespuertomontt.cl/admin/`
2. Usa las credenciales del superusuario que creaste

---

**¡Tu SGPAL está listo para producción!** 🎉

El sistema está corriendo de forma segura con SSL automático gracias a CloudPanel y CloudFlare.