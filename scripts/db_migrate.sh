#!/bin/bash
# Скрипт для применения миграций БД

set -e

cd "$(dirname "$0")/.."

echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

echo "📊 Проверка текущей версии БД..."
alembic current

echo "🚀 Применение миграций..."
alembic upgrade head

echo "✅ Миграции успешно применены!"
echo ""
echo "📈 Текущая версия БД:"
alembic current

