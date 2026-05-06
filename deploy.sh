#!/bin/bash

# Script de despliegue para Django
# Uso: ./deploy.sh [restart|full]

set -e

PROJECT_DIR="/home/sherpa/Proyectos/gestion-funcionarios-flux"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="gunicorn"

echo "🚀 Iniciando despliegue..."

# Función para verificar si el comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependencias
if ! command_exists python3; then
    echo "❌ Python3 no está instalado"
    exit 1
fi

if ! command_exists pip; then
    echo "❌ pip no está instalado"
    exit 1
fi

if ! command_exists nginx; then
    echo "❌ nginx no está instalado"
    exit 1
fi

cd "$PROJECT_DIR"

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p staticfiles media logs

# Configurar virtualenv si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creando virtualenv..."
    python3 -m venv "$VENV_DIR"
fi

# Activar virtualenv
echo "🔧 Activando virtualenv..."
source "$VENV_DIR/bin/activate"

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Configurar variables de entorno
echo "⚙️ Configurando entorno..."
export DJANGO_SETTINGS_MODULE=config.settings
export PYTHONPATH="$PROJECT_DIR"

# Ejecutar migraciones
echo "🗄️ Ejecutando migraciones..."
python manage.py migrate

# Recolectar archivos estáticos
echo "📄 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Cambiar permisos
echo "🔒 Configurando permisos..."
sudo chown -R www-data:www-data "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
sudo chmod -R 777 "$PROJECT_DIR/media"
sudo chmod -R 755 "$PROJECT_DIR/staticfiles"

# Configurar servicios del sistema
if [ "$1" = "full" ]; then
    echo "🔧 Configurando servicios del sistema..."

    # Copiar archivo de servicio de gunicorn
    sudo cp "$PROJECT_DIR/gunicorn.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable gunicorn

    # Copiar configuración de nginx
    sudo cp "$PROJECT_DIR/nginx.conf" /etc/nginx/sites-available/gestion-funcionarios
    sudo ln -sf /etc/nginx/sites-available/gestion-funcionarios /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl enable nginx
fi

# Reiniciar servicios
echo "🔄 Reiniciando servicios..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# Verificar estado
echo "✅ Verificando estado..."
sudo systemctl status gunicorn --no-pager
sudo systemctl status nginx --no-pager

# Probar aplicación
echo "🧪 Probando aplicación..."
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://localhost/ > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Despliegue completado exitosamente!"
    echo "🌐 Aplicación disponible en: http://localhost"
else
    echo "❌ Error en el despliegue"
    exit 1
fi

echo "🎉 ¡Despliegue completado!"