#!/bin/bash
# Скрипт для проверки статуса БД и миграций

set -e

cd "$(dirname "$0")/.."

echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

echo ""
echo "📊 Текущая версия БД:"
alembic current

echo ""
echo "📜 История миграций:"
alembic history --verbose

echo ""
echo "🔍 Проверка подключения к БД..."
PGPASSWORD=demos1110 psql -h localhost -U postgres -d rentdb -c "\conninfo"

echo ""
echo "📈 Статистика таблиц:"
PGPASSWORD=demos1110 psql -h localhost -U postgres -d rentdb -c "
SELECT 
    schemaname,
    relname as tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS size,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;
"

echo ""
echo "🗂️ Количество записей:"
PGPASSWORD=demos1110 psql -h localhost -U postgres -d rentdb -c "
SELECT 'users' as table_name, COUNT(*) as count FROM \"user\"
UNION ALL
SELECT 'devices', COUNT(*) FROM device
UNION ALL
SELECT 'orders', COUNT(*) FROM \"order\"
UNION ALL
SELECT 'audit_log', COUNT(*) FROM audit_log WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_log')
UNION ALL
SELECT 'device_stats', COUNT(*) FROM device_stats WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'device_stats');
" 2>/dev/null || echo "Некоторые таблицы еще не созданы"

