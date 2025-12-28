# app/__init__.py
import os
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text
from .routes import public, admin, local_admin, esp

from .db import db

login_manager = LoginManager()


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
    )
    app.config.from_object("config.Config")

    login_manager.init_app(app)
    login_manager.login_view = "public.login"
    login_manager.login_message = None
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(hours=12)

    db.init_app(app)

    # user loader — импортируем User внутри функции, чтобы избежать циклов импорта
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # --- блюпринты ---
    app.register_blueprint(public.bp)
    app.register_blueprint(admin.bp, url_prefix="/admin")
    app.register_blueprint(local_admin.bp, url_prefix="/local")
    app.register_blueprint(esp.bp)

    # --- инициализация БД + миграции без Alembic ---
    with app.app_context():
        db.create_all()
        ensure_schema()
        ensure_superadmin()

    return app


def ensure_schema():
    """
    Мягкие миграции (ALTER IF NOT EXISTS), чтобы не падать на чистой/старой БД.
    Добавляет поля для user/worker и device, индексы и FK.
    """
    stmts = [
        # ---- user ----
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS parent_id INTEGER NULL',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS worker_password TEXT',
        'CREATE INDEX IF NOT EXISTS idx_user_parent_id ON "user"(parent_id)',
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='user_parent_fk') THEN
            ALTER TABLE "user" ADD CONSTRAINT user_parent_fk
              FOREIGN KEY (parent_id) REFERENCES "user"(id) ON DELETE SET NULL;
          END IF;
        END $$;
        """,

        # ---- device ----
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS device_uid VARCHAR(64)',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS price_per_minute INTEGER NOT NULL DEFAULT 0',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS relay_state BOOLEAN NOT NULL DEFAULT FALSE',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS active_until TIMESTAMP NULL',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS relay_start_at TIMESTAMP NULL',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP NULL',
        'ALTER TABLE device ADD COLUMN IF NOT EXISTS allowed_minutes JSONB',
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='device_device_uid_key') THEN
            ALTER TABLE device ADD CONSTRAINT device_device_uid_key UNIQUE (device_uid);
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          -- если когда-то ставили unique на name, снимаем его
          IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name='device' AND constraint_type='UNIQUE' AND constraint_name='device_name_key'
          ) THEN
            ALTER TABLE device DROP CONSTRAINT device_name_key;
          END IF;
        END $$;
        """,

    ]

    for s in stmts:
        db.session.execute(text(s))
    db.session.commit()
    print("[INIT] ensure_schema: OK")


def ensure_superadmin():
    """Создаёт суперадмина admin/admin, если его нет"""
    from .models import User
    u = User.query.filter_by(email="admin").first()
    if not u:
        u = User(email="admin", role="superadmin", is_enabled=True)
        u.set_password("admin")
        db.session.add(u)
        db.session.commit()
        print("[INIT] Суперадмин admin/admin создан")
    else:
        print(f"[INIT] Суперадмин уже есть (id={u.id})")
