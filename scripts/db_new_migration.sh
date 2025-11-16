#!/bin/bash
# Скрипт для создания новой миграции

set -e

if [ -z "$1" ]; then
    echo "❌ Ошибка: укажите описание миграции"
    echo "Использование: $0 \"описание миграции\""
    echo "Пример: $0 \"Add user status field\""
    exit 1
fi

cd "$(dirname "$0")/.."

echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

echo "🆕 Создание новой миграции: $1"
alembic revision --autogenerate -m "$1"

echo "✅ Миграция создана!"
echo ""
echo "📝 Проверьте файл миграции в alembic/versions/"
echo "🚀 Для применения: ./scripts/db_migrate.sh"

