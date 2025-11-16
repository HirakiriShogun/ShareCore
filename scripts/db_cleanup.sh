#!/bin/bash
# Скрипт очистки старых бэкапов

set -e

cd "$(dirname "$0")/.."

# Настройки
BACKUP_DIR="./db_backups"
RETENTION_DAYS=30  # Хранить бэкапы 30 дней

echo "🧹 Очистка старых бэкапов (старше $RETENTION_DAYS дней)..."

# Показать что будет удалено
echo "📋 Файлы для удаления:"
find "$BACKUP_DIR" -name "rentdb_backup_*.sql" -type f -mtime +$RETENTION_DAYS -ls

# Подсчитать количество файлов для удаления
COUNT=$(find "$BACKUP_DIR" -name "rentdb_backup_*.sql" -type f -mtime +$RETENTION_DAYS | wc -l)

if [ "$COUNT" -eq 0 ]; then
    echo "✅ Нет файлов для удаления"
    exit 0
fi

echo "🗑️  Удаление $COUNT файлов..."

# Удалить старые бэкапы
find "$BACKUP_DIR" -name "rentdb_backup_*.sql" -type f -mtime +$RETENTION_DAYS -delete

echo "✅ Очистка завершена!"

# Показать статистику после очистки
echo ""
echo "📊 Статистика после очистки:"
echo "Всего файлов: $(ls -1 "$BACKUP_DIR"/rentdb_backup_*.sql 2>/dev/null | wc -l)"
echo "Общий размер: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
echo "Последние 5 бэкапов:"
ls -lt "$BACKUP_DIR"/rentdb_backup_*.sql 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 " bytes) - " $6 " " $7 " " $8}'

# Логирование
LOG_FILE="$BACKUP_DIR/cleanup.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Очистка: удалено $COUNT файлов" >> "$LOG_FILE"
