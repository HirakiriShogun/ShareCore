"""Fix database integrity and add constraints

Revision ID: 07e6d9d1eda6
Revises: 1be49a789bed
Create Date: 2025-10-05 14:25:00.000000

Исправления:
1. Добавление DEFAULT значений для всех полей
2. Добавление CHECK constraints для ENUM-полей
3. Исправление Foreign Keys с CASCADE
4. Добавление device_table_id в order для правильной связи
5. Исправление старых заказов (pending -> succeeded)
6. Добавление updated_at для tracking
7. Добавление deleted_at для soft delete

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '07e6d9d1eda6'
down_revision: Union[str, None] = '1be49a789bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применение улучшений к БД"""
    
    # ============================================================
    # 1. ТАБЛИЦА USER - Добавление DEFAULT и constraints
    # ============================================================
    
    # Добавляем DEFAULT для существующих полей
    op.alter_column('user', 'role',
                    existing_type=sa.VARCHAR(length=20),
                    server_default='localadmin',
                    existing_nullable=True)
    
    op.alter_column('user', 'is_enabled',
                    existing_type=sa.BOOLEAN(),
                    server_default='true',
                    existing_nullable=True)
    
    op.alter_column('user', 'created_at',
                    existing_type=postgresql.TIMESTAMP(),
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    existing_nullable=True)
    
    # Добавляем CHECK constraint для role
    op.create_check_constraint(
        'user_role_check',
        'user',
        "role IN ('superadmin', 'localadmin', 'worker')"
    )
    
    # Добавляем новые поля для soft delete и tracking
    op.add_column('user', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('user', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
    
    # Создаем индекс для deleted_at (для быстрого поиска активных пользователей)
    op.create_index('ix_user_deleted_at', 'user', ['deleted_at'])
    
    # ============================================================
    # 2. ТАБЛИЦА DEVICE - Добавление DEFAULT и улучшения
    # ============================================================
    
    op.alter_column('device', 'is_active',
                    existing_type=sa.BOOLEAN(),
                    server_default='true',
                    existing_nullable=True)
    
    op.alter_column('device', 'created_at',
                    existing_type=postgresql.TIMESTAMP(),
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    existing_nullable=True)
    
    # Добавляем поля для tracking и soft delete
    op.add_column('device', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('device', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
    
    # Индекс для deleted_at
    op.create_index('ix_device_deleted_at', 'device', ['deleted_at'])
    
    # ============================================================
    # 3. ТАБЛИЦА ORDER - Критические исправления
    # ============================================================
    
    # Добавляем DEFAULT для created_at
    op.alter_column('order', 'created_at',
                    existing_type=postgresql.TIMESTAMP(),
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    existing_nullable=True)
    
    # Добавляем DEFAULT для currency
    op.alter_column('order', 'currency',
                    existing_type=sa.VARCHAR(length=8),
                    server_default='RUB',
                    existing_nullable=True)
    
    # Добавляем CHECK constraint для payment_status
    op.create_check_constraint(
        'order_payment_status_check',
        'order',
        "payment_status IN ('pending', 'succeeded', 'canceled')"
    )
    
    # Добавляем CHECK constraint для currency
    op.create_check_constraint(
        'order_currency_check',
        'order',
        "currency IN ('RUB', 'USD', 'EUR')"
    )
    
    # Добавляем device_table_id для правильной связи с device.id
    op.add_column('order', sa.Column('device_table_id', sa.Integer(), nullable=True))
    
    # Создаем индекс для device_table_id
    op.create_index('ix_order_device_table_id', 'order', ['device_table_id'])
    
    # Добавляем updated_at для tracking изменений статуса
    op.add_column('order', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
    
    # Заполняем device_table_id из device_id (через JOIN с device по device_uid)
    op.execute("""
        UPDATE "order" o
        SET device_table_id = d.id
        FROM device d
        WHERE o.device_id = d.device_uid
    """)
    
    # Добавляем Foreign Key для device_table_id
    op.create_foreign_key(
        'order_device_table_id_fkey',
        'order', 'device',
        ['device_table_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Исправляем старые заказы: pending -> succeeded (для старых заказов без payment_id)
    op.execute("""
        UPDATE "order"
        SET payment_status = 'succeeded'
        WHERE payment_id IS NULL 
          AND payment_status = 'pending'
          AND created_at < CURRENT_TIMESTAMP - INTERVAL '1 day'
    """)
    
    # ============================================================
    # 4. ИСПРАВЛЕНИЕ FOREIGN KEYS - Добавление CASCADE
    # ============================================================
    
    # Удаляем старый FK для parent_id
    op.drop_constraint('user_parent_fk', 'user', type_='foreignkey')
    
    # Создаем новый FK с CASCADE (при удалении родителя удаляются дети)
    op.create_foreign_key(
        'user_parent_fk',
        'user', 'user',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Удаляем старый FK для owner_id
    op.drop_constraint('device_owner_id_fkey', 'device', type_='foreignkey')
    
    # Создаем новый FK с SET NULL (при удалении owner устройство не удаляется)
    op.create_foreign_key(
        'device_owner_id_fkey',
        'device', 'user',
        ['owner_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Откат изменений"""
    
    # Откат Foreign Keys
    op.drop_constraint('device_owner_id_fkey', 'device', type_='foreignkey')
    op.create_foreign_key('device_owner_id_fkey', 'device', 'user', ['owner_id'], ['id'])
    
    op.drop_constraint('user_parent_fk', 'user', type_='foreignkey')
    op.create_foreign_key('user_parent_fk', 'user', 'user', ['parent_id'], ['id'])
    
    # Откат ORDER
    op.drop_constraint('order_device_table_id_fkey', 'order', type_='foreignkey')
    op.drop_index('ix_order_device_table_id', 'order')
    op.drop_column('order', 'updated_at')
    op.drop_column('order', 'device_table_id')
    op.drop_constraint('order_currency_check', 'order', type_='check')
    op.drop_constraint('order_payment_status_check', 'order', type_='check')
    
    op.alter_column('order', 'currency', server_default=None)
    op.alter_column('order', 'created_at', server_default=None)
    
    # Откат DEVICE
    op.drop_index('ix_device_deleted_at', 'device')
    op.drop_column('device', 'deleted_at')
    op.drop_column('device', 'updated_at')
    op.alter_column('device', 'created_at', server_default=None)
    op.alter_column('device', 'is_active', server_default=None)
    
    # Откат USER
    op.drop_index('ix_user_deleted_at', 'user')
    op.drop_column('user', 'deleted_at')
    op.drop_column('user', 'updated_at')
    op.drop_constraint('user_role_check', 'user', type_='check')
    op.alter_column('user', 'created_at', server_default=None)
    op.alter_column('user', 'is_enabled', server_default=None)
    op.alter_column('user', 'role', server_default=None)
