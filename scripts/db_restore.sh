#!/bin/bash
# Скрипт для восстановления БД из резервной копии

set -e

if [ -z "$1" ]; then
    echo "❌ Ошибка: укажите файл резервной копии"
    echo "Использование: $0 <backup_file.sql>"
    echo ""
    echo "Доступные бэкапы:"
    ls -lh ./db_backups/*.sql 2>/dev/null || echo "Нет бэкапов"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Файл не найден: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  ВНИМАНИЕ: Это удалит все текущие данные в БД!"
read -p "Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Отменено"
    exit 0
fi

echo "🗑️  Удаление старой БД..."
PGPASSWORD=demos1110 dropdb -h localhost -U postgres --if-exists rentdb

echo "🆕 Создание новой БД..."
PGPASSWORD=demos1110 createdb -h localhost -U postgres rentdb

echo "📥 Восстановление из резервной копии..."
PGPASSWORD=demos1110 psql -h localhost -U postgres -d rentdb < "$BACKUP_FILE"

echo "✅ БД успешно восстановлена!"
echo "🔄 Не забудьте применить миграции: ./scripts/db_migrate.sh"

