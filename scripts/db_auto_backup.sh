#!/bin/bash
# Скрипт автоматического ежедневного бэкапа БД

set -e

cd "$(dirname "$0")/.."

# Настройки
BACKUP_DIR="./db_backups"
RETENTION_DAYS=30  # Хранить бэкапы 30 дней
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/rentdb_backup_${TIMESTAMP}.sql"

# Создать директорию если не существует
mkdir -p "$BACKUP_DIR"

echo "🔄 Начало автоматического бэкапа..."
echo "📅 Дата: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📁 Файл: $BACKUP_FILE"

# Проверить подключение к БД
if ! PGPASSWORD=demos1110 psql -h localhost -U postgres -d rentdb -c "SELECT 1;" >/dev/null 2>&1; then
    echo "❌ Ошибка: Не удается подключиться к базе данных"
    exit 1
fi

echo "✅ Подключение к БД установлено"

# Создать бэкап
echo "💾 Создание резервной копии..."
PGPASSWORD=demos1110 pg_dump -h localhost -U postgres -d rentdb \
    --verbose \
    --no-owner \
    --no-privileges \
    --format=plain \
    --file="$BACKUP_FILE"

# Проверить размер файла
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Бэкап создан успешно! Размер: $FILE_SIZE"
else
    echo "❌ Ошибка: Файл бэкапа пустой или не создан"
    exit 1
fi

# Очистка старых бэкапов
echo "🧹 Очистка старых бэкапов (старше $RETENTION_DAYS дней)..."
find "$BACKUP_DIR" -name "rentdb_backup_*.sql" -type f -mtime +$RETENTION_DAYS -delete

# Показать статистику
echo ""
echo "📊 Статистика бэкапов:"
echo "Всего файлов: $(ls -1 "$BACKUP_DIR"/rentdb_backup_*.sql 2>/dev/null | wc -l)"
echo "Общий размер: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
echo "Последние 5 бэкапов:"
ls -lt "$BACKUP_DIR"/rentdb_backup_*.sql 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 " bytes) - " $6 " " $7 " " $8}'

echo ""
echo "✅ Автоматический бэкап завершен успешно!"

# Логирование
LOG_FILE="$BACKUP_DIR/backup.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Бэкап создан: $BACKUP_FILE ($FILE_SIZE)" >> "$LOG_FILE"
