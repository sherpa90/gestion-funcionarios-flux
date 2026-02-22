# Guía de Seguridad para Producción - SGPAL

## Resumen de Correcciones de Seguridad Implementadas

Esta guía documenta las mejoras de seguridad implementadas basadas en OWASP Top 10 y mejores prácticas de seguridad para aplicaciones Django en producción.

---

## Vulnerabilidades Corregidas

### 1. A01:2021 - Broken Access Control

**Problema:** Configuraciones de seguridad insuficientes.

**Correcciones implementadas:**
- ✅ `SECRET_KEY` ahora es **obligatoria** via variable de entorno (no hay valor por defecto)
- ✅ `DEBUG` ahora es `False` por defecto
- ✅ `SECURE_SSL_REDIRECT` habilitado en producción
- ✅ `ALLOWED_HOSTS` debe configurarse explícitamente
- ✅ `CSRF_TRUSTED_ORIGINS` configurado correctamente
- ✅ Validación de IDs en vistas para prevenir IDOR
- ✅ Content Security Policy (CSP) habilitado en producción

### 2. A02:2021 - Cryptographic Failures

**Problema:** Secretos hardcodeados.

**Correcciones implementadas:**
- ✅ Secret Key debe generarse y configurarse externamente
- ✅ Sentry configurado para NO enviar PII (`send_default_pii=False`)

### 3. A03:2021 - Injection

**Problema:** Posible XSS en mensajes.

**Correcciones implementadas:**
- ✅ Sanitización de HTML en mensajes de error de liquidaciones
- ✅ Sanitización de mensajes en templates (removido `|safe`)
- ✅ CSP previene XSS en producción

### 6. A06:2021 - Vulnerable and Outdated Components

**Problema:** Dependencias desactualizadas.

**Correcciones implementadas:**
- ✅ Actualización regular de dependencias
- ✅ Revisión de seguridad en requirements.txt

### 7. A07:2021 - Identification and Authentication Failures

**Problema:** Gestión de contraseñas.

**Correcciones implementadas:**
- ✅ Función de reset de contraseña para ADMIN/SECRETARIA
- ✅ Validación de contraseñas robusta (Django validators)
- ✅ Protección contra fuerza bruta (django-axes)

### 4. A04:2021 - Insecure Design

**Problema:** Health check expone información sensible.

**Correcciones implementadas:**
- ✅ Health check ahora solo devuelve información básica por defecto
- ✅ Métricas del sistema solo disponibles con `HEALTH_CHECK_DETAILED=True`

### 5. A05:2021 - Security Misconfiguration

**Problema:** Múltiples configuraciones inseguras.

**Correcciones implementadas:**
- ✅ Límites de tamaño de archivos subidos (10MB)
- ✅ SESSION_COOKIE_AGE aumentado a 8 horas
- ✅ HSTS habilitado por 1 año
- ✅ X-Frame-Options: DENY

---

## Configuración Requerida para Producción

### 1. Generar Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(50))"
```

### 2. Archivo .env de Producción

Copia `.env.production.example` a `.env` y configura:

```env
# REQUERIDO - Genera una clave segura
SECRET_KEY=<tu-clave-generada>

# REQUERIDO - Tus dominios
DEBUG=False
DJANGO_ALLOWED_HOSTS=tu-dominio.cl,www.tu-dominio.cl
CSRF_TRUSTED_ORIGINS=https://tu-dominio.cl

# SEGURIDAD
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# OPCIONAL - Monitoreo
SENTRY_DSN=
HEALTH_CHECK_DETAILED=False
```

### 3. Verificar Configuración

Ejecuta el check de Django:

```bash
python manage.py check --deploy
```

---

## Configuraciones de Seguridad Activas

| Configuración | Desarrollo | Producción |
|--------------|------------|------------|
| DEBUG | True | False |
| SECRET_KEY | required | required |
| SSL Redirect | False | True |
| HSTS | False | True (1 año) |
| CSP | Disabled | Enabled |
| Session Cookie Secure | False | True |
| CSRF Cookie Secure | False | True |
| Health Check Detailed | True | False |
| Max Upload Size | 10MB | 10MB |

---

## Recomendaciones Adicionales para Producción

### 1. Rated Limiting
La aplicación ya usa `django-axes` para protección contra fuerza bruta. Asegúrate de:
- No bloquear el acceso al health check
- Configurar apropiadamente en Nginx/Reverse Proxy

### 2. Base de Datos
- Usar PostgreSQL en producción (no SQLite)
- Habilitar SSL para conexiones a la base de datos
- Rotar regularmente las credenciales

### 3. Archivos Estáticos
- Usar WhiteNoise sirve archivos estáticos
- Configurar CDN para archivos estáticos en producción

### 4. Logs y Monitoreo
- Revisar regularmente los logs de seguridad
- Configurar alertas para intentos de login fallidos
- Usar Sentry para tracking de errores (sin PII)

### 5. Backups
- Configurar backups automáticos
- Encriptar backups
- Probar restauración regularmente

---

## Testing de Seguridad

### Verificar Configuración

```bash
# Check de Django
python manage.py check --deploy

# Verificar variables de entorno
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('SECRET_KEY set:', bool(os.environ.get('SECRET_KEY'))); print('DEBUG:', os.environ.get('DEBUG'))"
```

### Pruebas Manuales

1. ✅ Intentar acceder sin login - debe redirigir a login
2. ✅ Intentar acceder a URLs de admin sin permisos - debe ser denegado
3. ✅ Verificar que health check no exponga información sensible
4. ✅ Probar carga de archivos - debe limitar tamaño
5. ✅ Verificar HTTPS obligatorio en producción

---

## Notas de Despliegue

### Dokploy/Dockge
Cuando despliegues en producción:
1. Asegúrate de设置 `SECRET_KEY` segura
2. Configura `DEBUG=False`
3. Configura `DJANGO_ALLOWED_HOSTS` con tu dominio real
4. Configura `CSRF_TRUSTED_ORIGINS` con HTTPS

### Variables de Entorno Críticas
- `SECRET_KEY` - **OBLIGATORIA** - Genera una nueva para producción
- `DEBUG` - Debe ser `False` en producción
- `DJANGO_ALLOWED_HOSTS` - Tu dominio
- `CSRF_TRUSTED_ORIGINS` - HTTPS de tu dominio

---

## Normalización de Base de Datos

Se ha creado una nueva aplicación `catalogos` que proporciona tablas normalizadas para el sistema:

### Tablas Creadas

| Tabla | Descripción |
|-------|-------------|
| `catalogos_rolusuario` | Roles de usuario del sistema |
| `catalogos_tipofuncionario` | Tipos de funcionario (Docente, Asistente) |
| `catalogos_estadoregistroasistencia` | Estados de asistencia |
| `catalogos_estadosolicitudpermiso` | Estados de solicitudes de permiso |
| `catalogos_tipoequipo` | Tipos de equipos |
| `catalogos_estadoequipo` | Estados de equipos |
| `catalogos_periodoliquidacion` | Períodos de liquidaciones |
| `catalogos_jornadalaboral` | Jornadas laborales |
| `catalogos_tipodia` | Tipos de día |

### Beneficios de la Normalización
- **3NF**: No hay dependencias transitivas
- **Integridad de datos**: Valores controlados por catálogos
- **Mantenibilidad**: Cambios en un solo lugar
- **Escalabilidad**: Índices optimizados
- **Auditoría**: Campos de created/updated en todas las tablas

### Cómo Aplicar

```bash
# 1. Crear migraciones
python manage.py makemigrations catalogos

# 2. Aplicar migraciones
python manage.py migrate

# 3. Poblar catálogos con datos iniciales
python manage.py seed_catalogos
```

---

## Referencias

- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [Django Security Docs](https://docs.djangoproject.com/en/5.2/topics/security/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
