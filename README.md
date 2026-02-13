# SGPAL - Sistema de Gestión de Personal y Asistencia Laboral

[![Django](https://img.shields.io/badge/Django-5.0+-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

> ⚠️ **IMPORTANTE - SEGURIDAD**: Nunca commits credenciales reales. Usa `.env.production.example` como template y configura tus variables de entorno de forma segura.

Sistema integral para la gestión de recursos humanos, control de asistencia, permisos, licencias médicas y liquidaciones de sueldo para instituciones educativas chilenas.

## 📋 Características Principales

### 👥 Gestión de Usuarios
- Sistema de roles (Funcionario, Director, Directivo, Secretaria, Administrador)
- Autenticación por RUT chileno
- Gestión de tipos de funcionario (Docente/Asistente)

### ⏰ Control de Asistencia
- Carga masiva desde Excel/PDF
- Cálculos automáticos de puntualidad
- Gestión de horarios personalizados
- Sistema de alegaciones y justificaciones

### 📅 Gestión de Permisos
- Solicitudes de días libres
- Aprobación por directores
- Control de días disponibles por usuario

### 🏥 Licencias Médicas
- Subida y gestión de documentos
- Seguimiento de estados
- Reportes de ausentismo

### 💰 Liquidaciones
- Gestión de documentos de pago
- Acceso seguro por usuario
- Historial completo

### 📊 Reportes y Estadísticas
- Dashboard administrativo
- Métricas de asistencia
- Reportes personalizados

## 🛠️ Tecnologías Utilizadas

- **Backend**: Django 5.0+ con Python 3.12+
- **Base de Datos**: PostgreSQL 15+
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **APIs**: WeasyPrint (PDF), OpenPyXL (Excel), PDFPlumber
- **Seguridad**: Django Axes, Sentry
- **Despliegue**: Docker, Docker Compose, Gunicorn

## 🚀 Instalación y Configuración

### Prerrequisitos
- Docker y Docker Compose
- Python 3.12+ (para desarrollo local)
- PostgreSQL 15+ (opcional para desarrollo local)

### Configuración Rápida con Docker

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd sgpal
   ```

2. **Configurar variables de entorno**
   ```bash
   cp .env.production.example .env
   # Editar .env con tus configuraciones REALES (nunca commits este archivo)
   ```

3. **Levantar servicios**
   ```bash
   docker-compose up -d
   ```

4. **Ejecutar migraciones**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Crear superusuario**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

### Configuración Manual (Desarrollo)

1. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate     # Windows
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar base de datos**
   ```bash
   createdb sgpal_db
   ```

4. **Ejecutar setup**
   ```bash
   python manage.py migrate
   python manage.py setup_data  # Si existe
   ```

## 📖 Uso del Sistema

### Acceso al Sistema
- **URL**: http://localhost:8000
- **Admin**: http://localhost:8000/admin

### Roles y Permisos

| Rol | Permisos |
|-----|----------|
| **Funcionario** | Ver asistencia, solicitar permisos, ver liquidaciones |
| **Director** | Aprobar solicitudes de permisos |
| **Secretaria** | Gestión completa de usuarios y permisos |
| **Administrador** | Acceso total al sistema |

### Funcionalidades por Módulo

#### Asistencia
- Carga masiva desde Excel
- Visualización de estadísticas personales
- Gestión de horarios

#### Permisos
- Solicitud de días libres
- Aprobación/rechazo por directores
- Control de saldo de días

#### Licencias
- Subida de documentos médicos
- Seguimiento de estados
- Reportes de ausentismo

#### Liquidaciones
- Acceso a boletas de pago
- Historial completo
- Descarga segura

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DEBUG` | Modo debug | `False` |
| `SECRET_KEY` | Clave secreta Django | *requerido* |
| `SQL_ENGINE` | Motor de BD | `django.db.backends.postgresql` |
| `SQL_DATABASE` | Nombre BD | `sgpal_db` |
| `EMAIL_HOST` | Servidor SMTP | - |
| `SENTRY_DSN` | DSN de Sentry | - |

### Comandos Útiles

```bash
# Ejecutar tests
python manage.py test

# Crear migraciones
python manage.py makemigrations

# Recolectar archivos estáticos
python manage.py collectstatic

# Backup de base de datos
pg_dump sgpal_db > backup.sql
```

## 🔒 Seguridad

### Credenciales y Variables de Entorno
- **Nunca commits archivos .env** con credenciales reales
- Usa `.env.production.example` como template
- Configura variables de entorno de forma segura en producción
- El `.gitignore` excluye automáticamente archivos `.env*`

### Seguridad de Aplicación
- Autenticación robusta con RUT chileno
- Protección contra fuerza bruta (Django Axes)
- Encriptación de contraseñas
- Validación de RUT integrada
- Auditoría completa de acciones

## 📊 Monitoreo

- **Sentry**: Reportes de errores
- **Health Checks**: Verificación de servicios
- **Logging**: Logs estructurados
- **Métricas**: Rendimiento y uso

## 🚀 Despliegue en Producción

### Con Docker
```bash
# Construir imagen
docker-compose -f docker-compose.prod.yml build

# Desplegar
docker-compose -f docker-compose.prod.yml up -d
```

### Checklist de Producción
- [ ] Cambiar `DEBUG=False`
- [ ] Configurar `SECRET_KEY` segura
- [ ] Configurar base de datos PostgreSQL
- [ ] Configurar email SMTP
- [ ] Configurar Sentry
- [ ] Configurar HTTPS
- [ ] Ejecutar `collectstatic`

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

### Estándares de Código
- PEP 8 para Python
- Black para formateo
- Tests obligatorios para nuevas funcionalidades

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o reportes de bugs:
- Crear issue en GitHub
- Contactar al equipo de desarrollo

## 🙏 Agradecimientos

- Comunidad Django
- Contribuidores del proyecto
- Instituciones educativas que utilizan el sistema

---

**Desarrollado con ❤️ para la gestión eficiente de recursos humanos en educación**