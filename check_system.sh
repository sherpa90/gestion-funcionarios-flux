#!/bin/bash

# Script para verificar el estado del sistema después del despliegue
# Uso: ./check_system.sh

echo "🔍 Verificando estado del sistema..."

# Función para verificar servicio
check_service() {
    if sudo systemctl is-active --quiet "$1"; then
        echo "✅ $1: Activo"
    else
        echo "❌ $1: Inactivo"
        return 1
    fi
}

# Verificar servicios
echo "📋 Verificando servicios..."
services_ok=true

check_service nginx || services_ok=false
check_service gunicorn || services_ok=false
check_service postgresql || services_ok=false

if [ "$services_ok" = false ]; then
    echo "❌ Algunos servicios no están activos"
    exit 1
fi

# Verificar conectividad
echo "🌐 Verificando conectividad..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200\|301\|302"; then
    echo "✅ Servidor web responde correctamente"
else
    echo "❌ Servidor web no responde"
    exit 1
fi

# Verificar archivos estáticos
echo "📄 Verificando archivos estáticos..."
if [ -d "staticfiles" ] && [ "$(ls -A staticfiles)" ]; then
    echo "✅ Archivos estáticos recolectados"
else
    echo "❌ Archivos estáticos no encontrados"
fi

# Verificar base de datos
echo "🗄️ Verificando base de datos..."
python manage.py dbshell -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Conexión a base de datos OK"
else
    echo "❌ Error de conexión a base de datos"
fi

# Verificar logs
echo "📝 Verificando logs..."
if [ -f "logs/django.log" ]; then
    echo "✅ Archivo de logs existe"
    # Mostrar últimas líneas de error
    echo "Últimos errores en logs:"
    tail -10 logs/django.log | grep -i error || echo "No hay errores recientes"
else
    echo "⚠️ Archivo de logs no encontrado"
fi

# Verificar procesos
echo "🔧 Verificando procesos..."
gunicorn_processes=$(ps aux | grep gunicorn | grep -v grep | wc -l)
if [ "$gunicorn_processes" -gt 0 ]; then
    echo "✅ Gunicorn ejecutándose ($gunicorn_processes procesos)"
else
    echo "❌ Gunicorn no está ejecutándose"
fi

echo "✅ Verificación completada"