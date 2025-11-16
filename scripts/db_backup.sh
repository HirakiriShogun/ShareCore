#!/bin/bash
# Скрипт для создания резервной копии БД

set -e

BACKUP_DIR="./db_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/rentdb_backup_$TIMESTAMP.sql"

mkdir -p "$BACKUP_DIR"

echo "💾 Создание резервной копии БД..."
echo "📁 Файл: $BACKUP_FILE"

PGPASSWORD=demos1110 pg_dump -h localhost -U postgres -d rentdb > "$BACKUP_FILE"

echo "✅ Резервная копия создана успешно!"
echo "📊 Размер: $(du -h "$BACKUP_FILE" | cut -f1)"

# Удаление старых бэкапов (старше 30 дней)
echo "🧹 Удаление старых бэкапов (>30 дней)..."
find "$BACKUP_DIR" -name "rentdb_backup_*.sql" -mtime +30 -delete

echo "✅ Готово!"

