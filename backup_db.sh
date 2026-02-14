#!/bin/bash
# =============================================================================
# SCRIPT DE BACKUP PARA SGPAL
# =============================================================================
# Este script hace backup de la base de datos PostgreSQL
# 
# Uso: ./backup_db.sh
# 
# Configura en crontab para ejecución automática:
# 0 2 * * * /app/backup_db.sh >> /var/log/backup.log 2>&1
# =============================================================================

set -e

# Configuración
BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="${SQL_DATABASE:-sgpal_db}"
DB_USER="${SQL_USER:-sgpal_user}"
DB_HOST="${SQL_HOST:-db}"
DB_PORT="${SQL_PORT:-5432}"

# Crear directorio de backups
mkdir -p "$BACKUP_DIR"

echo "=== Iniciando backup: $DATE ==="

# Generar nombre del archivo
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

# Ejecutar backup
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F c -b -v -f "$BACKUP_FILE" "$DB_NAME"

# Verificar que el backup se creó
if [ -f "$BACKUP_FILE" ]; then
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup creado exitosamente: $BACKUP_FILE ($FILE_SIZE)"
else
    echo "❌ Error: No se pudo crear el backup"
    exit 1
fi

# Eliminar backups antiguos (mantener últimos 7)
echo "Limpiando backups antiguos (mantener últimos 7)..."
ls -t "$BACKUP_DIR"/${DB_NAME}_*.sql.gz | tail -n +8 | xargs -r rm -f

echo "=== Backup completado ==="
echo ""

# Listar backups actuales
echo "Backups disponibles:"
ls -lh "$BACKUP_DIR"/${DB_NAME}_*.sql.gz
