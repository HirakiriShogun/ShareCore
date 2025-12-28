from flask import Blueprint, jsonify, current_app
from datetime import datetime, timedelta

from app.models import Device, Order, schedule_activation, clear_expired_activation
from app.db import db
from app.integrations import alfa_bank
from app.integrations.alfa_bank import AlfaBankError

bp = Blueprint("esp", __name__)

@bp.route("/esp/poll/<uid>", methods=["GET"])
def esp_poll(uid):
    now = datetime.utcnow()
    d = Device.query.filter_by(device_uid=uid).first()
    if not d:
        return jsonify({"relay": "off", "remaining": 0}), 404

    # --- фикс: отмечаем, что устройство в сети ---
    d.last_seen_at = now

    # Авто-очистка если активация просрочена
    if d.relay_state and d.active_until and d.active_until <= now:
        clear_expired_activation(d, now=now)

    # НОВОЕ: Проверяем зависшие платежи для этого устройства
    _check_pending_payments_for_device(d)

    remaining = 0
    relay_on = False
    if d.relay_state and d.active_until and d.active_until > now:
        remaining = int((d.active_until - now).total_seconds())
        if d.relay_start_at and d.relay_start_at > now:
            relay_on = False
        else:
            relay_on = True

    db.session.commit()
    return jsonify({
        "relay": "on" if relay_on else "off",
        "remaining": remaining
    })


def _check_pending_payments_for_device(device):
    """Проверяет зависшие платежи для конкретного устройства."""

    if not alfa_bank.is_enabled():
        return

    pending_orders = Order.query.filter(
        Order.device_id == device.device_uid,
        Order.payment_status == "pending",
        Order.payment_id.isnot(None)
    ).all()

    if not pending_orders:
        return

    now = datetime.utcnow()
    recent_cutoff = now - timedelta(seconds=10)

    for order in pending_orders:
        if order.updated_at and order.updated_at >= recent_cutoff:
            continue

        try:
            payload = alfa_bank.fetch_order_status(
                order_id=order.payment_id,
                order_number=str(order.id),
            )
        except AlfaBankError:
            continue

        status, _code = alfa_bank.normalize_status(payload)
        order.updated_at = now

        if status == "succeeded" and order.payment_status != "succeeded":
            order.payment_status = "succeeded"
            if device.is_active and order.minutes:
                delay_seconds = int(current_app.config.get("RELAY_DELAY_SECONDS", 0) or 0)
                schedule_activation(device, order.minutes, now=now, delay_seconds=delay_seconds)
        elif status == "canceled" and order.payment_status != "canceled":
            order.payment_status = "canceled"
