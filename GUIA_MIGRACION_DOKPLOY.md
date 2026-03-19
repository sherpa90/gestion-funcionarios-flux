# Guía de Migración de Servidor en Dokploy

Esta guía te permitirá migrar la aplicación SGPAL completa (aplicación + base de datos) de un servidor a otro en Dokploy.

---

## Fase 1: Preparación en el Servidor Origen

### 1.1 Realizar Backup de la Base de Datos

En el servidor actual (Dokploy), sigue estos pasos:

1. Accede a tu proyecto en Dokploy
2. Busca el servicio de base de datos PostgreSQL
3. En la pestaña **"Backups"** o usa el cliente de PostgreSQL:

```bash
# Desde el contenedor de la base de datos o terminal
pg_dump -h <HOST_DB_ORIGEN> -U <USUARIO_DB> -F c -b -v -f backup_sgpal_$(date +%Y%m%d).sql.gz <NOMBRE_DB>
```

O desde Dokploy:
1. Ve a tu **Database Service**
2. Busca **"Create Backup"** o **"Manual Backup"**
3. Nombre: `sgpal_backup_before_migration`
4. Descarga el archivo generado

### 1.2 Exportar Variables de Entorno

Anota todas las variables de entorno de tu aplicación actual:

1. Ve a tu aplicación en Dokploy
2. Accede a la pestaña **"Environment"**
3. Copia cada variable y su valor

Variables críticas a guardar:
```
DEBUG=False
SECRET_KEY=<tu_clave>
DJANGO_ALLOWED_HOSTS=<tus_dominios>
CSRF_TRUSTED_ORIGINS=https://<tu_dominio>
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=<nombre_db>
SQL_USER=<usuario_db>
SQL_PASSWORD=<password_db>
SQL_HOST=<host_db>
SQL_PORT=5432
```

### 1.3 Respaldar Archivos Media

Si tienes archivos subidos (imágenes, documentos, etc.):

1. Ve a **"Volumes"** en tu aplicación
2. Identifica el volumen de media (mount path: `/app/media`)
3. Descarga el contenido o usa:

```bash
# Si tienes acceso SSH al servidor
docker cp <contenedor_web>:/app/media ./media_backup
```

---

## Fase 2: Configurar el Nuevo Servidor

### 2.1 Crear el Proyecto en Dokploy (Nuevo Servidor)

1. Inicia sesión en **https://dokploy.com**
2. Crea un nuevo proyecto o usa uno existente
3. Anota la IP del nuevo servidor

### 2.2 Crear Base de Datos PostgreSQL

1. En tu proyecto, click en **"Create Service"**
2. Selecciona **"Database"** → **PostgreSQL**
3. Configura:
   - **Name**: `sgpal-db` (puede ser diferente)
   - **Database**: `sgpal_db` (usa el mismo nombre o anota el nuevo)
   - **User**: `sgpal_user`
   - **Password**: `Sgpal2025Secure!` (o nueva contraseña)
   - **Version**: 15 o latest

4. **Guarda los datos de conexión** que te proporciona Dokploy:
   - Host interno
   - Puerto
   - Usuario
   - Contraseña
   - Nombre de base de datos

### 2.3 Crear la Aplicación Web

1. **"Create Service"** → **"Application"**
2. Configura:
   - **Name**: `sgpal-web`
   - **Provider**: GitHub
   - **Repository**: `sherpa90/sgpal` (tu repositorio)
   - **Branch**: `main`
3. **Build Type**: Dockerfile
4. **Docker Context**: `/`
5. **Dockerfile Path**: `./Dockerfile`
6. **Port**: 8000

### 2.4 Configurar Variables de Entorno

En la pestaña **"Environment"** de tu nueva aplicación, agrega:

| Variable | Valor |
|----------|-------|
| `DEBUG` | `False` |
| `SECRET_KEY` | (Genera una nueva clave) |
| `DJANGO_ALLOWED_HOSTS` | `<nuevo_dominio>,localhost` |
| `CSRF_TRUSTED_ORIGINS` | `https://<nuevo_dominio>` |
| `SQL_ENGINE` | `django.db.backends.postgresql` |
| `SQL_DATABASE` | `sgpal_db` (el nombre que usaste) |
| `SQL_USER` | `sgpal_user` |
| `SQL_PASSWORD` | `Sgpal2025Secure!` |
| `SQL_HOST` | `<host_db_nuevo>` (ver paso 2.2) |
| `SQL_PORT` | `5432` |

### 2.5 Configurar Volúmenes

1. **Volumes** → **Add Volume**:
   - **Type**: Volume
   - **Name**: `sgpal-media`
   - **Mount Path**: `/app/media`

---

## Fase 3: Restaurar la Base de Datos

### 3.1 Método 1: Restaurar desde Backup de Dokploy

1. Ve a tu nueva base de datos en Dokploy
2. Busca **"Backups"** → **"Restore"**
3. Sube el archivo de backup descargado en el paso 1.1

### 3.2 Método 2: Restaurar desde Terminal

```bash
# Conectar al contenedor de PostgreSQL
pg_restore -h <HOST_DB_NUEVO> -U <USUARIO_DB> -d <NOMBRE_DB> -v backup_sgpal_*.sql.gz
```

### 3.3 Verificar Restauración

```bash
# Conectar a la DB
psql -h <HOST_DB_NUEVO> -U <USUARIO_DB> -d <NOMBRE_DB>

# Verificar tablas
\dt

# Verificar datos de ejemplo
SELECT COUNT(*) FROM users_user;
SELECT COUNT(*) FROM asistencia_registroasistencia;
```

---

## Fase 4: Desplegar la Aplicación

### 4.1 Primer Despliegue

1. En tu nueva aplicación, ve a **"Deployments"**
2. Click en **"Deploy"**
3. Observa los logs para verificar:
   - Las migraciones se ejecutan
   - Gunicorn inicia correctamente
   - No hay errores

### 4.2 Configurar Dominio (Opcional)

1. Ve a **"Domains"** en tu aplicación
2. Agrega tu nuevo dominio
3. Habilita **SSL/HTTPS**

---

## Fase 5: Transferir Archivos Media

### 5.1 Si usas volúmenes de Dokploy

1. Descarga el contenido del volumen media del servidor anterior
2. Sube los archivos al nuevo volumen:

```bash
# Usando docker cp
docker cp ./media_backup/. <nuevo_contenedor>:/app/media/
```

### 5.2 Verificar Archivos

En Django shell del nuevo servidor:
```python
from django.conf import settings
import os
print(settings.MEDIA_ROOT)
# Verificar que los archivos existen
```

---

## Fase 6: Verificación Final

### 6.1 Probar la Aplicación

| Prueba | URL | Esperado |
|--------|-----|----------|
| Login | `https://<nuevo_dominio>/accounts/login/` | Formulario de login |
| Admin | `https://<nuevo_dominio>/admin/` | Panel de admin |
| Asistencia | `https://<nuevo_dominio>/asistencia/` | Ver registros |
| Permisos | `https://<nuevo_dominio>/permisos/` | Ver solicitudes |

### 6.2 Verificar Datos

1. Accede al admin de Django
2. Verifica que existen:
   - Usuarios (incluyendo el superusuario)
   - Registros de asistencia
   - Permisos solicitados
   - Catálogos
   - Equipos

### 6.3 Probar Funcionalidades Críticas

- [ ] Login con usuarios existentes
- [ ] Crear/modificar registros de asistencia
- [ ] Solicitar y aprobar permisos
- [ ] Enviar correos (verificar configuración SMTP)
- [ ] Subir archivos (media)

---

## Fase 7: Configuración de Backups Automáticos

En tu nueva base de datos:

1. Ve a **"Backups"**
2. Habilita **"Automated Backups"**
3. Configura:
   - **Frequency**: Diario
   - **Retention**: 7 días (o más)
   - **Destination**: Almacenamiento de Dokploy

---

## Checklist de Migración

- [ ] Backup de base de datos creado y descargado
- [ ] Variables de entorno documentadas
- [ ] Archivos media respaldados (si aplica)
- [ ] Nueva base de datos creada en Dokploy
- [ ] Nueva aplicación creada en Dokploy
- [ ] Variables de entorno configuradas
- [ ] Volúmenes configurados
- [ ] Base de datos restaurada
- [ ] Aplicación desplegada
- [ ] Dominio configurado (si aplica)
- [ ] SSL/HTTPS habilitado
- [ ] Archivos media transferidos (si aplica)
- [ ] Login funciona
- [ ] Admin Django funciona
- [ ] Datos verificados
- [ ] Backups automáticos configurados

---

## Solución de Problemas

### Error: "Database does not exist"
- Verifica que creaste la base de datos con el mismo nombre
- O actualiza `SQL_DATABASE` en las variables de entorno

### Error: "Connection refused"
- Verifica que `SQL_HOST` tiene el valor correcto (host interno de Dokploy)
- La IP externa no funciona para conexiones internas de Docker

### Error: "Permission denied" en archivos media
- Verifica que el volumen está correctamente configurado
- Recrea el contenedor si es necesario

### Error: CSRF verification failed
- Asegúrate que `CSRF_TRUSTED_ORIGINS` incluya `https://<nuevo_dominio>`

### Error: Static files not found
- Ejecuta `python manage.py collectstatic` en el contenedor
- O verifica el volumen de staticfiles

---

## Notas Importantes

1. **Cambia la SECRET_KEY** en el nuevo servidor por seguridad
2. **Actualiza los DNS** si usas un dominio propio
3. **Prueba exhaustivamente** antes de dar de baja el servidor antiguo
4. **Mantén ambos servidores** funcionando en paralelo durante la migración
5. **Documenta cualquier personalización** específica del servidor antiguo

---

## ¿Necesitas Ayuda?

Si tienes dudas o surgen errores durante la migración, consulta los logs de Dokploy o revisa la documentación original en:
- `DEPLOY_DOKPLOY.md`
- `GUIA_DOKPLOY_COMPLETA.md`
