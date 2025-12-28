# app/models.py
from datetime import datetime, timedelta
from typing import Optional
from .db import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="localadmin")  # superadmin | localadmin | worker
    is_enabled = db.Column(db.Boolean, default=True, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True, index=True)
    worker_password = db.Column(db.Text, nullable=True)  # TODO: убрать в будущем (security risk)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    def set_password(self, password: str) -> None:
        if not password:
            self.password_hash = ""
            return
        try:
            self.password_hash = generate_password_hash(password, method="scrypt")
        except Exception:
            # fallback для сборок без scrypt
            self.password_hash = generate_password_hash(password)  # pbkdf2:sha256

    def check_password(self, password: str) -> bool:
        try:
            return bool(self.password_hash) and check_password_hash(self.password_hash, password)
        except Exception:
            return False


class Device(db.Model):
    __tablename__ = "device"
    
    id = db.Column(db.Integer, primary_key=True)
    device_uid = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    price_per_minute = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, index=True)
    relay_state = db.Column(db.Boolean, default=False, nullable=False)
    active_until = db.Column(db.DateTime, nullable=True)
    relay_start_at = db.Column(db.DateTime, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    allowed_minutes = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)


class Order(db.Model):
    __tablename__ = "order"
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    amount = db.Column(db.Integer, nullable=False)  # в копейках
    currency = db.Column(db.String(8), default="RUB")
    device_id = db.Column(db.String(64), index=True)   # UID устройства (legacy)
    device_table_id = db.Column(db.Integer, db.ForeignKey("device.id", ondelete="SET NULL"), nullable=True, index=True)  # Правильная связь
    customer_id = db.Column(db.String(64), index=True)
    minutes = db.Column(db.Integer, nullable=True)
    
    # Поля для платёжного шлюза
    payment_id = db.Column(db.String(128), unique=True, nullable=True, index=True)
    payment_status = db.Column(db.String(32), default="pending")  # pending, succeeded, canceled
    payment_url = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_log"
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=True, index=True)
    action = db.Column(db.String(20), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, PAYMENT
    changed_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    old_data = db.Column(db.JSON, nullable=True)
    new_data = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)


class DeviceStats(db.Model):
    __tablename__ = "device_stats"
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id", ondelete="CASCADE"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    total_orders = db.Column(db.Integer, default=0, nullable=False)
    total_revenue = db.Column(db.Integer, default=0, nullable=False)  # В копейках
    total_minutes = db.Column(db.Integer, default=0, nullable=False)
    avg_order_value = db.Column(db.Integer, default=0, nullable=False)  # В копейках
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('device_id', 'date', name='uq_device_stats_device_date'),
    )


def is_online(device, timeout=20):
    return bool(device.last_seen_at and (datetime.utcnow() - device.last_seen_at).total_seconds() < timeout)


class ClientConsent(db.Model):
    __tablename__ = "client_consent"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id", ondelete="SET NULL"), nullable=True, index=True)
    consent_date = db.Column(db.Date, nullable=False, index=True)
    consent_time = db.Column(db.Time, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    agreed = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def schedule_activation(device, minutes: int, *, now: Optional[datetime] = None, delay_seconds: int = 0):
    now = now or datetime.utcnow()
    delay = max(0, int(delay_seconds or 0))
    start_at = now + timedelta(seconds=delay) if delay else now
    device.relay_state = True
    device.relay_start_at = start_at if delay else None
    device.active_until = start_at + timedelta(minutes=minutes)
    return device.active_until


def clear_expired_activation(device, *, now: Optional[datetime] = None):
    now = now or datetime.utcnow()
    if device.relay_state and device.active_until and device.active_until <= now:
        device.relay_state = False
        device.active_until = None
        device.relay_start_at = None
