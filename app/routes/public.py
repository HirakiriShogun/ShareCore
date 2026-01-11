from datetime import datetime
from typing import Optional



from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app

from app.db import db

from app.models import User, Device, Order, ClientConsent, is_online, schedule_activation, clear_expired_activation
from flask_login import login_user, logout_user, login_required, current_user

from app.integrations import alfa_bank

from app.integrations.alfa_bank import AlfaBankError



bp = Blueprint("public", __name__)





def _activate_device(device: Device, minutes: int, *, now: Optional[datetime] = None) -> datetime:
    now = now or datetime.utcnow()
    delay_seconds = int(current_app.config.get("RELAY_DELAY_SECONDS", 0) or 0)
    schedule_activation(device, minutes, now=now, delay_seconds=delay_seconds)
    return device.active_until


def _is_control_user() -> bool:
    return bool(current_user.is_authenticated and current_user.role in ("worker", "localadmin", "superadmin"))




def _refresh_order_state(order: Order, *, device: Optional[Device] = None):
    try:

        payload = alfa_bank.fetch_order_status(order_id=order.payment_id, order_number=str(order.id))

    except AlfaBankError:

        return None



    status, _code = alfa_bank.normalize_status(payload)

    now = datetime.utcnow()



    if status == "succeeded" and order.payment_status != "succeeded":

        order.payment_status = "succeeded"

        order.updated_at = now

        target = device or Device.query.filter_by(device_uid=order.device_id).first()

        if target and target.is_active and (order.minutes or 0) > 0:

            _activate_device(target, order.minutes, now=now)

    elif status == "canceled" and order.payment_status != "canceled":

        order.payment_status = "canceled"

        order.updated_at = now

    else:

        order.updated_at = now



    return status, payload





def _render_successful_payment(order: Order):

    device = Device.query.filter_by(device_uid=order.device_id).first()

    if device and device.relay_state and device.active_until:

        remaining = int((device.active_until - datetime.utcnow()).total_seconds())

        if remaining > 0:

            minutes_left = max(1, remaining // 60)

            return render_template(

                "payment_result.html",

                success=True,

                message=f"Оплата прошла успешно! Устройство работает ещё {minutes_left} мин.",

                device_uid=order.device_id,

            )



    return render_template(

        "payment_result.html",

        success=True,

        message=f"Оплата прошла успешно! Устройство запущено на {order.minutes} мин.",

        device_uid=order.device_id,

    )



@bp.route("/")

def root_redirect():

    # Главная страница доступна всем (залогиненным и незалогиненным)

    return render_template("home.html")





# ---------- Логин админов/сотрудников ----------

@bp.route("/login", methods=["GET", "POST"])

def login():

    if request.method == "POST":

        email = (request.form.get("email") or "").strip()

        password = (request.form.get("password") or "").strip()

        user = User.query.filter_by(email=email).first()



        if not user or not getattr(user, "check_password", lambda _: False)(password):

            return render_template("login/index.html", error="Неверный логин или пароль")



        if hasattr(user, "is_enabled") and not user.is_enabled:

            return render_template("login/index.html", error="Профиль отключён")



        login_user(user)



        # Роутинг по ролям

        if user.role == "superadmin":

            return redirect(url_for("admin.dashboard"))

        elif user.role == "localadmin":

            return redirect(url_for("local_admin.dashboard"))

        elif user.role == "worker":

            return redirect(url_for("local_admin.worker_page"))

        return redirect(url_for("public.login"))  # запасной вариант



    return render_template("login/index.html")





@bp.route("/logout")

@login_required

def logout():

    logout_user()

    return redirect(url_for("public.login"))





# ---------- Публичная страница устройства (через QR) ----------

@bp.route("/device/<uid>")

def public_device(uid):

    d = Device.query.filter_by(device_uid=uid, is_active=True).first()

    if not d or not is_online(d):

        return render_template("device_offline.html"), 503

    return render_template("device.html", device=d)





# ---------- API: список всех активных устройств ----------

@bp.route("/api/devices", methods=["GET"])

def api_devices_list():
    """Возвращает список активных устройств для внутренних панелей"""
    if not _is_control_user():
        return jsonify({"error": "forbidden"}), 403
    now = datetime.utcnow()
    

    # Получаем только активные устройства от активных владельцев

    devices = Device.query.filter_by(is_active=True).all()

    

    result = []

    for d in devices:

        # Проверяем, что владелец активен

        if d.owner_id:

            owner = User.query.get(d.owner_id)

            if not owner or owner.role != "localadmin" or not owner.is_enabled:

                continue

        

        remaining = 0

        if d.relay_state and d.active_until:
            if d.active_until > now:
                remaining = int((d.active_until - now).total_seconds())
            else:
                clear_expired_activation(d, now=now)
                db.session.commit()
        

        default_minutes = [5, 10, 15, 30, 60]

        result.append({

            "id": d.device_uid or str(d.id),

            "name": d.name,

            "price_per_minute": int(d.price_per_minute or 0),  # копейки

            "busy": remaining > 0,

            "remaining_seconds": remaining,

            "online": is_online(d),

            "allowed_minutes": d.allowed_minutes if d.allowed_minutes else default_minutes

        })

    

    return jsonify(result)





# ---------- API: статус устройства ----------

@bp.route("/api/device/<uid>", methods=["GET"])

def api_public_device(uid):
    now = datetime.utcnow()
    d = Device.query.filter_by(device_uid=uid, is_active=True).first()
    if not d:
        return jsonify({"error": "not_found"}), 404

    remaining = 0
    if d.relay_state and d.active_until:
        if d.active_until > now:
            remaining = int((d.active_until - now).total_seconds())
        else:
            clear_expired_activation(d, now=now)
            db.session.commit()


    default_minutes = [5, 10, 15, 30, 60]

    return jsonify({

        "id": d.id,

        "name": d.name,

        "price_per_minute": int(d.price_per_minute or 0),  # копейки

        "busy": remaining > 0,

        "remaining_seconds": remaining,

        "online": is_online(d),

        "allowed_minutes": d.allowed_minutes if d.allowed_minutes else default_minutes

    })





# ---------- API: эмуляция оплаты / запуск активации ----------

@bp.route("/api/rent", methods=["POST"])

def api_public_rent():
    if not _is_control_user():
        return jsonify({"error": "forbidden"}), 403
    p = request.get_json(force=True) or {}
    minutes = int(p.get("minutes") or 0)

    if minutes <= 0 or minutes > 720:

        return jsonify({"error": "bad_input"}), 400



    uid = (p.get("device_uid") or "").strip()

    did = p.get("device_id")



    d = None

    if uid:

        d = Device.query.filter_by(device_uid=uid).first()

    elif did:

        d = Device.query.get(did)



    if not d or not d.is_active or not is_online(d):

        return jsonify({"error": "device_unavailable"}), 404



    owner = User.query.get(d.owner_id) if d.owner_id else None

    if not owner or owner.role != "localadmin" or not owner.is_enabled:

        return jsonify({"error": "device_unavailable"}), 404



    now = datetime.utcnow()

    if d.relay_state and d.active_until and d.active_until > now:

        rem = int((d.active_until - now).total_seconds())

        return jsonify({"error": "busy", "remaining_seconds": rem}), 409



    # Ограничение по допустимым вариантам длительности

    if d.allowed_minutes:

        try:

            normalize = sorted({int(x) for x in d.allowed_minutes})

        except Exception:

            normalize = None

        if normalize and minutes not in normalize:

            return jsonify({"error": "minutes_not_allowed"}), 400



    # Запуск активации

    _activate_device(d, minutes, now=now)



    # Записываем заказ (в копейках)

    amount = int(d.price_per_minute or 0) * minutes

    db.session.add(Order(

        amount=amount, 

        currency="RUB", 

        device_id=d.device_uid or str(d.id),

        device_table_id=d.id,  # Правильная связь

        minutes=minutes,

        payment_status="succeeded"  # Прямая активация без эквайринга

    ))



    db.session.commit()

    return jsonify({

        "ok": True,

        "until": d.active_until.isoformat() + "Z",

        "amount": amount

    })





# ---------- API: создание платежа через Альфа-Банк ----------

def _handle_payment_create(payload):
    if current_app.config.get("PAYMENTS_DISABLED"):
        return jsonify({
            "error": "acquiring_disabled",
            "message": "Онлайн-оплата временно отключена, устройство активируем сразу"
        }), 400

    if not alfa_bank.is_enabled():
        return jsonify({"error": "acquiring_disabled"}), 400

    minutes = int(payload.get("minutes") or 0)
    if minutes <= 0 or minutes > 720:
        return jsonify({"error": "bad_input"}), 400

    uid = (payload.get("device_uid") or "").strip()
    device = Device.query.filter_by(device_uid=uid).first()

    if not device or not device.is_active or not is_online(device):
        return jsonify({"error": "device_unavailable"}), 404

    owner = User.query.get(device.owner_id) if device.owner_id else None
    if not owner or owner.role != "localadmin" or not owner.is_enabled:
        return jsonify({"error": "device_unavailable"}), 404

    now = datetime.utcnow()
    if device.relay_state and device.active_until and device.active_until > now:
        remaining = int((device.active_until - now).total_seconds())
        return jsonify({"error": "busy", "remaining_seconds": remaining}), 409

    if device.allowed_minutes:
        try:
            normalize = sorted({int(x) for x in device.allowed_minutes})
        except Exception:
            normalize = None
        if normalize and minutes not in normalize:
            return jsonify({"error": "minutes_not_allowed"}), 400

    amount = int(device.price_per_minute or 0) * minutes

    order = Order(
        amount=amount,
        currency="RUB",
        device_id=device.device_uid or str(device.id),
        device_table_id=device.id,
        minutes=minutes,
        payment_status="pending",
    )
    db.session.add(order)
    db.session.flush()

    return_url = url_for("public.payment_success", order_id=order.id, _external=True)
    fail_url = url_for("public.payment_fail", order_id=order.id, _external=True)
    callback_url = url_for("public.payment_callback", _external=True)

    client_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()

    try:
        gateway_response = alfa_bank.register_order(
            order_number=str(order.id),
            amount=amount,
            return_url=return_url,
            fail_url=fail_url,
            description=f"Активация {device.name} на {minutes} мин",
            callback_url=callback_url,
            extra_json={
                "order_id": order.id,
                "device_uid": device.device_uid,
                "minutes": minutes,
            },
            client_ip=client_ip or None,
        )
    except AlfaBankError as exc:
        db.session.rollback()
        return jsonify({"error": "payment_creation_failed", "message": str(exc)}), 502
    except Exception as exc:  # pragma: no cover - safety net
        db.session.rollback()
        return jsonify({"error": "payment_creation_failed", "message": str(exc)}), 500

    order.payment_id = gateway_response.get("orderId")
    order.payment_url = gateway_response.get("formUrl")
    order.updated_at = datetime.utcnow()

    db.session.commit()

    if not order.payment_url:
        return jsonify({"error": "payment_creation_failed", "message": "Нет ссылки на оплату"}), 502

    return jsonify({
        "ok": True,
        "payment_url": order.payment_url,
        "payment_id": order.payment_id,
        "order_id": order.id,
    })


@bp.route("/api/payment/create", methods=["POST"])
def api_create_payment():
    payload = request.get_json(force=True) or {}
    if not _is_control_user() and not payload.get("device_uid"):
        return jsonify({"error": "forbidden"}), 403
    return _handle_payment_create(payload)


@bp.route("/api/payment/public/create", methods=["POST"])
def api_create_payment_public():
    payload = request.get_json(force=True) or {}
    return _handle_payment_create(payload)

# ---------- Страница возврата после оплаты ----------

@bp.route("/payment/success")

def payment_success():

    order_id = request.args.get("order_id", type=int)

    if not order_id:

        return render_template("payment_result.html", success=False, message="Заказ не найден")



    order = Order.query.get(order_id)

    if not order:

        return render_template("payment_result.html", success=False, message="Заказ не найден")

    md_order = request.args.get("orderId") or request.args.get("mdOrder")

    if md_order and (not order.payment_id or order.payment_id != md_order):

        order.payment_id = md_order



    status_payload = None

    if order.payment_status not in ("succeeded", "canceled") and alfa_bank.is_enabled():

        status_payload = _refresh_order_state(order)

        db.session.commit()

    if order.payment_status == "succeeded":

        return _render_successful_payment(order)



    if order.payment_status == "canceled":

        message = "Оплата отменена"

        if status_payload and status_payload[1].get("actionCodeDescription"):

            message = status_payload[1]["actionCodeDescription"]

        return render_template("payment_result.html", success=False, message=message)



    message = "Ожидается подтверждение оплаты..."

    if status_payload and status_payload[1].get("actionCodeDescription"):

        message = status_payload[1]["actionCodeDescription"]

    return render_template("payment_result.html", success=False, message=message)





@bp.route("/payment/fail")

def payment_fail():

    order_id = request.args.get("order_id", type=int)

    if not order_id:

        return render_template("payment_result.html", success=False, message="Оплата не завершена")



    order = Order.query.get(order_id)

    if not order:

        return render_template("payment_result.html", success=False, message="Оплата не найдена")

    md_order = request.args.get("orderId") or request.args.get("mdOrder")

    if md_order and (not order.payment_id or order.payment_id != md_order):

        order.payment_id = md_order



    status_payload = None

    if alfa_bank.is_enabled():

        status_payload = _refresh_order_state(order)

        db.session.commit()

    if order.payment_status == "succeeded":

        return _render_successful_payment(order)



    message = "Оплата не завершена"

    if status_payload and status_payload[1].get("actionCodeDescription"):

        message = status_payload[1]["actionCodeDescription"]

    return render_template("payment_result.html", success=False, message=message)





# ---------- Webhook от Альфа-Банка ----------

@bp.route("/payment/callback", methods=["POST"])

def payment_callback():
    if not alfa_bank.is_enabled():

        return jsonify({"error": "disabled"}), 400



    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        data = request.form.to_dict()

    if not isinstance(data, dict):

        data = {}



    order_number = data.get("orderNumber") or data.get("order_id")

    md_order = data.get("mdOrder") or data.get("orderId")



    order = None

    if order_number is not None:

        try:

            order = Order.query.get(int(order_number))

        except (TypeError, ValueError):

            order = None



    if order is None and md_order:

        order = Order.query.filter_by(payment_id=md_order).first()



    if order is None:

        return jsonify({"error": "order_not_found"}), 404



    if md_order and not order.payment_id:

        order.payment_id = md_order



    refreshed = _refresh_order_state(order)

    db.session.commit()



    response = {"ok": True, "status": order.payment_status}

    if refreshed:

        status, payload = refreshed

        response["gateway_status"] = status

        message = payload.get("actionCodeDescription") or payload.get("errorMessage")

        if message:

            response["message"] = message



    return jsonify(response), 200


@bp.route("/api/consent", methods=["POST"])
def api_client_consent():
    payload = request.get_json(force=True) or {}
    uid = (payload.get("device_uid") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    agreed = bool(payload.get("agreed"))

    if not uid or not email:
        return jsonify({"error": "bad_input"}), 400
    if "@" not in email or len(email) > 120:
        return jsonify({"error": "bad_email"}), 400
    if not agreed:
        return jsonify({"error": "consent_required"}), 400

    device = Device.query.filter_by(device_uid=uid, is_active=True).first()
    if not device:
        return jsonify({"error": "device_unavailable"}), 404

    owner = User.query.get(device.owner_id) if device.owner_id else None
    if not owner or owner.role != "localadmin" or not owner.is_enabled:
        return jsonify({"error": "device_unavailable"}), 404

    now = datetime.utcnow()
    consent = ClientConsent(
        owner_id=owner.id,
        device_id=device.id,
        consent_date=now.date(),
        consent_time=now.time().replace(microsecond=0),
        email=email,
        agreed=True,
    )
    db.session.add(consent)
    db.session.commit()

    return jsonify({"ok": True})
