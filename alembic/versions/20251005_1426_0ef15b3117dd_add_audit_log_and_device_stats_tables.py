"""Add audit log and device stats tables

Revision ID: 0ef15b3117dd
Revises: 07e6d9d1eda6
Create Date: 2025-10-05 14:26:00.000000

Добавление:
1. Таблица audit_log для отслеживания всех изменений
2. Таблица device_stats для агрегированной статистики
3. Индексы для быстрого поиска

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0ef15b3117dd'
down_revision: Union[str, None] = '07e6d9d1eda6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание audit_log и device_stats"""
    
    # ============================================================
    # 1. AUDIT_LOG - Журнал всех изменений в системе
    # ============================================================
    
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('table_name', sa.String(50), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('old_data', postgresql.JSONB(), nullable=True),
        sa.Column('new_data', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для быстрого поиска
    op.create_index('ix_audit_log_table_name', 'audit_log', ['table_name'])
    op.create_index('ix_audit_log_record_id', 'audit_log', ['record_id'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_changed_by', 'audit_log', ['changed_by'])
    op.create_index('ix_audit_log_changed_at', 'audit_log', ['changed_at'])
    
    # Составной индекс для частого запроса
    op.create_index('ix_audit_log_table_record', 'audit_log', ['table_name', 'record_id'])
    
    # CHECK constraint для action
    op.create_check_constraint(
        'audit_log_action_check',
        'audit_log',
        "action IN ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'PAYMENT')"
    )
    
    # ============================================================
    # 2. DEVICE_STATS - Агрегированная статистика по устройствам
    # ============================================================
    
    op.create_table(
        'device_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_orders', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_revenue', sa.Integer(), server_default='0', nullable=False, comment='В копейках'),
        sa.Column('total_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('avg_order_value', sa.Integer(), server_default='0', nullable=False, comment='В копейках'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['device.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id', 'date', name='uq_device_stats_device_date')
    )
    
    # Индексы
    op.create_index('ix_device_stats_device_id', 'device_stats', ['device_id'])
    op.create_index('ix_device_stats_date', 'device_stats', ['date'])
    
    # Составной индекс для частых запросов
    op.create_index('ix_device_stats_device_date', 'device_stats', ['device_id', 'date'])


def downgrade() -> None:
    """Откат - удаление таблиц"""
    
    # Удаление device_stats
    op.drop_index('ix_device_stats_device_date', 'device_stats')
    op.drop_index('ix_device_stats_date', 'device_stats')
    op.drop_index('ix_device_stats_device_id', 'device_stats')
    op.drop_table('device_stats')
    
    # Удаление audit_log
    op.drop_constraint('audit_log_action_check', 'audit_log', type_='check')
    op.drop_index('ix_audit_log_table_record', 'audit_log')
    op.drop_index('ix_audit_log_changed_at', 'audit_log')
    op.drop_index('ix_audit_log_changed_by', 'audit_log')
    op.drop_index('ix_audit_log_action', 'audit_log')
    op.drop_index('ix_audit_log_record_id', 'audit_log')
    op.drop_index('ix_audit_log_table_name', 'audit_log')
    op.drop_table('audit_log')
