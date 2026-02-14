# 📖 MANUAL DE USUARIO - SGPAL

Sistema de Gestión de Personal y Asistencia Laboral

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Acceso al Sistema](#acceso-al-sistema)
3. [Roles de Usuario](#roles-de-usuario)
4. [Módulos del Sistema](#módulos-del-sistema)
5. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 1. INTRODUCCIÓN

SGPAL es un sistema integral para la gestión de recursos humanos, que incluye:

- ✅ Control de asistencia
- ✅ Gestión de permisos
- ✅ Licencias médicas
- ✅ Liquidaciones de sueldo
- ✅ Reportes y estadísticas

---

## 2. ACCESO AL SISTEMA

### URL de Acceso

```
https://tramites.losalercespuertomontt.cl
```

### Credenciales

| Rol | Acceso |
|-----|--------|
| Administrador | `/admin/` |
| Funcionario | `/` (página principal) |

### Recuperar Contraseña

1. Ir a `/accounts/login/`
2. Click en "¿Olvidaste tu contraseña?"
3. Ingresar el email registrado
4. Recibirás un email con enlace de recuperación

---

## 3. ROLES DE USUARIO

### 👤 Funcionario

- Ver su asistencia
- Solicitar permisos
- Ver sus liquidaciones
- Ver sus licencias médicas

### 👨‍💼 Director

- Todas las funciones de Funcionario
- Aprobar/rechazar permisos de funcionarios
- Ver reportes del establecimiento

### �_secretaria Secretaria

- Gestionar usuarios
- Gestionar permisos
- Gestionar asistencia
- Ver reportes

### ⚙️ Administrador

- Acceso total al sistema
- Gestión de usuarios
- Configuración del sistema
- Todos los reportes

---

## 4. MÓDULOS DEL SISTEMA

### 📅 Asistencia

#### Para Funcionarios

1. **Ver mi asistencia**
   - Ir a `/asistencia/mis-registros/`
   - Ver registro diario
   - Descargar reporte PDF

2. **Mi horario**
   - Ir a `/asistencia/mi-horario/`
   - Ver horario asignado

#### Para Administradores

1. **Cargar asistencia**
   - Ir a `/asistencia/carga/`
   - Subir archivo Excel con registros
   - El sistema procesa automáticamente

2. **Gestión de horarios**
   - Ir a `/asistencia/horarios/`
   - Crear/modificar horarios
   - Asignar a funcionarios

3. **Gestión de alegaciones**
   - Ir a `/asistencia/alegaciones/`
   - Revisar justificaciones
   - Aprobar/rechazar

---

### 📝 Permisos

#### Solicitar Permiso

1. Ir a `/permisos/solicitar/`
2. Llenar formulario:
   - Tipo de permiso
   - Fecha inicio
   - Fecha término
   - Motivo
3. Click en "Enviar Solicitud"
4. Esperar aprobación

#### Tipos de Permisos

| Tipo | Descripción |
|------|-------------|
| Día Administrativo | Permiso con goce de sueldo |
| Día de libre disposición | Día propio |
| Permiso médico | Por situación de salud |
|Otro|Otra causa justificada|

#### Aprobar Permiso (Directores)

1. Ir a `/permisos/dashboard-director/`
2. Ver solicitudes pendientes
3. Click en "Aprobar" o "Rechazar"
4. Agregar motivo si se rechaza

---

### 🏥 Licencias Médicas

#### Registrar Licencia

1. Ir a `/licencias/nueva/`
2. Subir documento PDF
3. Ingresar fechas
4. Guardar

#### Estados de Licencia

- **Pendiente**: Esperando revisión
- **Aprobada**: Licencia aceptada
- **Rechazada**: Documentación inválida

---

### 💰 Liquidaciones

#### Ver Mi Liquidación

1. Ir a `/liquidaciones/mis-liquidaciones/`
2. Ver lista de liquidación
3. Click para descargar PDF

#### Administrar Liquidaciones (Admin)

1. Ir a `/liquidaciones/`
2. Click en "Subir Liquidación"
3. Seleccionar usuario
4. Subir archivo PDF

---

### 📊 Reportes

#### Reportes Disponibles

1. **Asistencia Mensual**
   - Resumen de asistencia por mes
   
2. **Reporte Detallado**
   - Registro día a día
   
3. **Estadísticas**
   - Gráficos y métricas

4. **Exportar**
   - Descargar en PDF o Excel

---

## 5. PREGUNTAS FRECUENTES

### ¿Cómo recupero mi contraseña?

1. Ve a la página de login
2. Click en "¿Olvidaste tu contraseña?"
3. Ingresa tu email
4. Revisa tu correo (incluyendo spam)

### ¿Por qué mi permiso fue rechazado?

Revisa el motivo del rechazo en el detalle de tu solicitud. Common reasons:
- Falta de documentación
- Fechas incorrectas
- Falta de personal

### ¿Cuántos días de permiso tengo?

Consulta tus días disponibles en tu perfil o solicita a tu administrador.

### ¿Cómo veo mi historial de asistencia?

Ve a `/asistencia/mis-registros/` y filtra por fecha.

### ¿El sistema me avisa cuando me aprueban un permiso?

Sí, recibirás un email de notificación.

---

## 📞 Soporte

Para problemas técnicos:
- Email: soporte@losalercespuertomontt.cl
- Horario: Lunes a Viernes 8:00-17:00

---

**Versión del Sistema**: 1.0
**Última actualización**: 2024
