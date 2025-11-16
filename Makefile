.PHONY: help install migrate backup restore status new-migration docker-up docker-down

help:
	@echo "📚 Доступные команды:"
	@echo ""
	@echo "  make install          - Установка зависимостей"
	@echo "  make migrate          - Применить миграции БД"
	@echo "  make backup           - Создать резервную копию БД"
	@echo "  make auto-backup       - Автоматический бэкап с очисткой"
	@echo "  make cleanup           - Очистить старые бэкапы"
	@echo "  make restore FILE=... - Восстановить БД из бэкапа"
	@echo "  make status           - Проверить статус БД и миграций"
	@echo "  make new-migration MSG=\"...\" - Создать новую миграцию"
	@echo ""
	@echo ""
	@echo "  make run              - Запустить приложение"
	@echo "  make dev              - Запустить в режиме разработки"
	@echo ""

install:
	@echo "📦 Установка зависимостей..."
	source venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Зависимости установлены!"

migrate:
	@echo "🚀 Применение миграций..."
	./scripts/db_migrate.sh

backup:
	@echo "💾 Создание резервной копии..."
	./scripts/db_backup.sh

auto-backup:
	@echo "🔄 Автоматический бэкап с очисткой..."
	./scripts/db_auto_backup.sh

cleanup:
	@echo "🧹 Очистка старых бэкапов..."
	./scripts/db_cleanup.sh

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Укажите файл: make restore FILE=./db_backups/backup.sql"; \
		exit 1; \
	fi
	./scripts/db_restore.sh $(FILE)

status:
	@./scripts/db_status.sh

new-migration:
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Укажите описание: make new-migration MSG=\"Add user avatar\""; \
		exit 1; \
	fi
	./scripts/db_new_migration.sh "$(MSG)"

clean:
	@echo "🧹 Очистка временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ Очистка завершена!"

