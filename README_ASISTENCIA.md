# 🚀 Sistema de Asistencia - Guía de Configuración Completa

## 📋 Estado Actual

### ✅ Problemas Resueltos
- ❌ ~~`'HorarioFuncionario' object has no attribute 'exists'`~~ → **CORREGIDO**
- ❌ ~~Menú duplicado "Estadísticas y Reportes"~~ → **CORREGIDO**
- ❌ ~~Campos faltantes en BD~~ → **MIGRACIONES CREADAS**
- ❌ ~~No hay usuarios en BD~~ → **SCRIPT DE IMPORTACIÓN CREADO**
- ❌ ~~Formato Excel "06-11-2025 07:45" no reconocido~~ → **VERIFICADO Y FUNCIONAL**

### 🎯 Sistema Completamente Funcional
- ✅ Carga masiva desde Excel
- ✅ Matching inteligente de RUTs
- ✅ Cálculos automáticos de asistencia
- ✅ Estadísticas completas
- ✅ Interfaz web completa

---

## 🛠️ Configuración Automática (Recomendado)

### Paso 1: Ejecutar Corrección Completa
```bash
# Ejecutar corrección completa del sistema
python3 fix_asistencia_complete.py
```

Este script ejecutará automáticamente:
1. ✅ **Verificación del formato del Excel** (confirma que funciona con "06-11-2025 07:45")
2. ✅ **Corrección del modelo** (arregla el error .exists() en OneToOneField)
3. ✅ **Migraciones de base de datos**
4. ✅ **Importación de 44 usuarios desde Excel**
5. ✅ **Creación de horarios por defecto**
6. ✅ **Verificación completa del sistema**

### Paso 2: Verificar Resultado
Después del setup, deberías tener:
- 👥 **44 usuarios** en la base de datos
- ⏰ **44 horarios** de trabajo (08:00-17:00)
- ✅ **Sistema listo** para procesar asistencia

---

## 🔧 Configuración Manual (Si es necesario)

### Opción A: Solo Migraciones
```bash
# Ejecutar solo migraciones
./run_migrations.sh
```

### Opción B: Solo Importar Usuarios
```bash
# Importar usuarios desde Excel
python3 import_users_excel.py
```

### Opción C: Verificar Sistema
```bash
# Verificar estado del sistema
python3 debug_asistencia.py
```

---

## 🎯 Uso del Sistema

### 1. Cargar Registros de Asistencia
1. Ve a **Asistencia → Cargar Registros**
2. Sube el archivo `templates/Asistentes_Nov.xlsx`
3. Selecciona **Mes: Noviembre**, **Año: 2025**
4. Haz clic en **"Procesar Archivo"**

### 2. Ver Estadísticas Personales
1. Ve a **Asistencia → Mi Asistencia**
2. Selecciona el mes que quieres ver
3. Verás estadísticas completas de puntualidad

### 3. Gestionar Horarios
1. Ve a **Asistencia → Gestión de Horarios**
2. Crea o modifica horarios de entrada para usuarios
3. Los horarios afectan los cálculos de retraso

---

## 🔍 Solución de Problemas

### Error: "CSRF token incorrect"
**Solución:** Recarga la página (`F5`) y vuelve a intentar

### Error: "No se encontraron registros válidos"
**Causa:** No hay usuarios en la BD que coincidan con los RUTs del Excel
**Solución:** Ejecuta `python3 setup_asistencia.py`

### Error: "HorarioFuncionario object has no attribute exists"
**Causa:** Código desactualizado
**Solución:** Las migraciones ya están corregidas

---

## 📊 Datos Importados

### Formato del Excel Verificado ✅
**Archivo:** `templates/Asistentes_Nov.xlsx`
- **Columnas:** 3 (RUT, Nombre, Horario)
- **Formato RUT:** `9479036-0` (sin puntos)
- **Formato Horario:** `06-11-2025 07:45` (fecha y hora juntos)
- **Regex utilizado:** `^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})$`
- **Estado:** ✅ **FUNCIONA PERFECTAMENTE**

### Usuarios Creados (44 totales)
| RUT | Nombre | Usuario | Contraseña |
|-----|--------|---------|------------|
| 17639211-8 | MARCO ROSAS VILLARRO | user_176392118 | 123456 |
| 9479036-0 | CRISTIAN CACERES O. | user_94790360 | 123456 |
| ... | ... | ... | 123456 |

### Horarios por Defecto
- **Hora de entrada:** 08:00:00
- **Tolerancia:** 15 minutos
- **Estado:** Activo

---

## ⚠️ Consideraciones de Seguridad

### IMPORTANTE: Cambiar Contraseñas
```python
# En el shell de Django
python manage.py shell

from users.models import CustomUser
users = CustomUser.objects.all()
for user in users:
    user.set_password('NuevaContraseñaSegura123!')
    user.save()
```

### Usuarios Administrativos
Los usuarios importados tienen rol `FUNCIONARIO`. Para crear administradores:
```python
# Cambiar rol de un usuario
user = CustomUser.objects.get(run='17639211-8')
user.role = 'ADMIN'
user.save()
```

---

## 📈 Funcionalidades del Sistema

### ✅ Carga Masiva
- Soporte para Excel (.xlsx/.xls) y PDF
- Parsing automático de fechas y horas
- Matching inteligente de RUTs (múltiples formatos)

### ✅ Cálculos Automáticos
- Determinación automática de estado (Puntual/Retraso/Ausente)
- Cálculo de minutos de retraso
- Cálculo de tiempo trabajado

### ✅ Estadísticas Completas
- Porcentaje de puntualidad
- Días trabajados vs días totales
- Tiempo promedio trabajado
- Filtros por mes/año

### ✅ Gestión de Horarios
- Horarios personalizados por usuario
- Tolerancia configurable
- Activación/desactivación de horarios

---

## 🎉 ¡Sistema Listo!

Después de ejecutar `python3 setup_asistencia.py`, el sistema estará completamente funcional con:

- ✅ **44 usuarios** importados
- ✅ **Horarios configurados**
- ✅ **Base de datos actualizada**
- ✅ **Sistema verificado**

**¡Ya puedes empezar a usar el sistema de asistencia!** 🚀