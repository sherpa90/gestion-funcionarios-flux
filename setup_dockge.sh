#!/bin/bash

# Script de configuración para despliegue en Dockge
# SGPAL - Sistema de Gestión de Personal y Asistencia Laboral

echo "🚀 Configurando SGPAL para Dockge..."

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p data/media
mkdir -p data/postgres
mkdir -p data/backups
mkdir -p logs

# Configurar permisos
echo "🔒 Configurando permisos..."
chmod 755 data/postgres
chmod 755 data/media
chmod 755 data/backups
chmod 755 logs

# Copiar archivo de configuración de producción
if [ ! -f .env ]; then
    echo "📋 Copiando configuración de producción..."
    cp .env.production.example .env
    echo "⚠️  IMPORTANTE: Edita el archivo .env con tus valores reales antes de desplegar"
    echo "   Especialmente: SECRET_KEY, SQL_PASSWORD, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD"
fi

echo "✅ Configuración completada!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales reales"
echo "2. En Dockge: Add Stack -> SGPAL"
echo "3. Pega el contenido de docker-compose.dockge.yml"
echo "4. Deploy!"
echo ""
echo "🌐 URLs después del despliegue:"
echo "   App: http://tu-servidor:8000"
echo "   Admin: http://tu-servidor:8000/admin/"
echo "   Health: http://tu-servidor:8000/health/"