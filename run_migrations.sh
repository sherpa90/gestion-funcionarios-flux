#!/bin/bash

echo "🚀 Ejecutando migraciones de Django..."
echo "====================================="

# Verificar si estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: No se encuentra manage.py. Asegúrate de estar en el directorio raíz del proyecto Django."
    exit 1
fi

echo "📦 Creando migraciones..."
python manage.py makemigrations

echo ""
echo "⚡ Aplicando migraciones..."
python manage.py migrate

echo ""
echo "✅ Migraciones completadas exitosamente!"
echo ""
echo "💡 Si hay errores, revisa los logs arriba."