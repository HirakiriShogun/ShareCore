# ShareCore

## 1. Стек и требования
- Python 3.11+, Flask 3, Flask-SocketIO, SQLAlchemy, Alembic
- PostgreSQL 14+ (локально и на сервере)
- Node.js (только для pm2 на проде)
- GitHub Actions (`appleboy/ssh-action`) для деплоя

## 2. Установка и локальный запуск
1. `python -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Скопируйте `.env` (см. ниже) и укажите свои значения.
4. Запустите PostgreSQL и создайте базу `rentdb` (или поменяйте DSN).
5. Примените миграции: `alembic upgrade head` или `./scripts/db_migrate.sh`.
6. Старт приложения: `python app.py` или `flask --app app run --debug`.

Основные команды из `Makefile`:
- `make install` — установка зависимостей.
- `make migrate` — прогон Alembic миграций.
- `make backup | auto-backup | restore FILE=...` — управление дампами в `db_backups/`.
- `make new-migration MSG="..."` — создание новой миграции.

## 3. Переменные окружения (.env)
| Ключ | Назначение | Пример |
| --- | --- | --- |
| `SECRET_KEY` | Flask session key | `SECRET_KEY=devkey` |
| `DATABASE_URL` | DSN PostgreSQL | `postgresql://postgres:demos1110@localhost:5432/rentdb` |
| `ALFABANK_ENABLED` | включить оплату через Альфабанк | `true` / `false` |
| `ALFABANK_API_URL`, `ALFABANK_LOGIN`, `ALFABANK_PASSWORD`, `ALFABANK_TOKEN`, `ALFABANK_CURRENCY`, `ALFABANK_PAGE_VIEW` | настройки платёжного шлюза | см. документацию банка |

Если `.env` отсутствует, приложение берёт дефолты из `config.py`.

## 4. База данных
- Движок: PostgreSQL.
- Дефолтный пользователь: `postgres`, пароль: `demos1110`, база: `rentdb`.
- Таблицы (см. `app/models.py`):
  - `user`: авторизация, иерархия админов (`parent_id`), роли (`superadmin`, `localadmin`, `worker`), флаги активности.
  - `device`: устройства, тарифы, текущие статусы (`relay_state`, `allowed_minutes`, `last_seen_at`).
  - `order`: платежи и сеансы (связь с устройством по `device_table_id`, состояние `payment_status`, `payment_id`).
  - `audit_log`: все действия (таблица/ID, действие, пользователь, старые/новые данные, IP/User-Agent).
  - `device_stats`: агрегаты по дате и устройству (кол-во заказов, выручка, минуты, средний чек).
- `db.create_all()` и `ensure_schema()` подстраховывают БД при запуске, но для контроля версий используйте Alembic.
- Резервные копии складываются в `db_backups/` (см. скрипты `scripts/db_*.sh`).

## 5. Константные данные и директории
- Шаблоны: `templates/`, статические файлы: `static/`.
- Документы (публичная оферта, политики, инструкции) лежат в `static/documents/` и доступны с главной страницы.
- Файлы `.log` и временные архивы не игнорируются — храните служебные материалы внимательно.

## 6. Прод, сервер и деплой
- Сервер: `195.133.5.249`.
- Пользователь: `root`.
- Пароль SSH: `demos1110` (альтернативно используется ключ из `secrets.SSH_KEY` в GitHub Actions).
- Код расположен в `/root/rent_device`.
- Приложение крутится через `pm2` (процесс `pm2 list`, рестарт `pm2 restart 0`, логи `pm2 logs 0`).
- Бэкенд запускается c `python app.py` (или gunicorn) под управлением pm2.
- База данных расположена на том же сервере (localhost:5432).

### Автодеплой
Workflow `.github/workflows/deploy.yml`:
1. триггерится на `push` в `main`;
2. подключается по SSH к серверу;
3. выполняет `cd /root/rent_device && git pull && pm2 restart 0`.

Для ручного деплоя достаточно выполнить те же команды через SSH.

## 7. Диагностика
- Проверка текущей схемы: `alembic current`.
- Состояние устройств/очереди: см. раздел "Devices" на главной странице (данные тянутся из `/api/devices`).
- В случае ошибок входа/оплаты — смотрите таблицу `audit_log` и логи pm2.
