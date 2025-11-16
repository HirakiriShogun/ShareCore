# app/routes/local_admin.py
from datetime import datetime, timedelta
from flask import Blueprint, abort, render_template, request, jsonify, session, send_file, url_for
from flask_login import login_required, current_user
from app.db import db
from app.models import Device, User
from app.models import Order
from sqlalchemy.exc import IntegrityError
from datetime import datetime

bp = Blueprint("local_admin", __name__)

def is_local():  return current_user.is_authenticated and current_user.role == "localadmin"
def is_worker(): return current_user.is_authenticated and current_user.role == "worker"

# -------- Pages --------
@bp.route("/")
@login_required
def dashboard():
    if not is_local():
        abort(403)
    is_sudo = bool(session.get("sudo_original_id"))
    return render_template("local/dashboard.html", is_sudo=is_sudo, email=current_user.email)

@bp.route("/devices")
@login_required
def devices_page():
    if not is_local():
        abort(403)
    return render_template("local/devices_list.html")

@bp.route("/devices/new")
@login_required
def devices_new_page():
    if not is_local():
        abort(403)
    return render_template("local/devices_new.html")

@bp.route("/devices/<int:did>")
@login_required
def devices_edit_page(did):
    if not is_local():
        abort(403)
    return render_template("local/devices_edit.html", did=did)

@bp.route("/worker")
@login_required
def worker_page():
    if not (is_local() or is_worker()):
        abort(403)
    can_control = is_local()
    return render_template("local/worker.html", can_control=can_control)

@bp.route("/stats")
@login_required
def stats_page():
    if not (is_local() or is_worker()):
        abort(403)
    return render_template("local/stats.html")

# -------- Local analytics API --------
@bp.route("/api/analytics/summary", methods=["GET"])
@login_required
def api_local_analytics_summary():
    if not is_local():
        abort(403)
    # only devices belonging to current local admin
    devs = Device.query.filter_by(owner_id=current_user.id).all()
    ids = [d.device_uid or str(d.id) for d in devs]
    total_orders = db.session.query(db.func.count(Order.id)).filter(Order.device_id.in_(ids)).scalar() or 0
    total_amount = db.session.query(db.func.coalesce(db.func.sum(Order.amount), 0)).filter(Order.device_id.in_(ids)).scalar() or 0
    by_device = []
    for d in devs:
        did = d.device_uid or str(d.id)
        cnt = db.session.query(db.func.count(Order.id)).filter(Order.device_id == did).scalar() or 0
        amt = db.session.query(db.func.coalesce(db.func.sum(Order.amount), 0)).filter(Order.device_id == did).scalar() or 0
        by_device.append({"id": d.id, "name": d.name, "orders": int(cnt), "amount": int(amt)})
    return jsonify({"total_orders": int(total_orders), "total_amount": int(total_amount), "by_device": by_device})

@bp.route("/api/analytics/export.xlsx", methods=["GET"])
@login_required
def api_local_analytics_export():
    if not is_local():
        abort(403)
    from io import BytesIO
    try:
        import openpyxl
    except Exception:
        return jsonify({"error":"xlsx_not_supported"}), 500
    devs = Device.query.filter_by(owner_id=current_user.id).all()
    ids = [d.device_uid or str(d.id) for d in devs]
    rows = Order.query.filter(Order.device_id.in_(ids)).order_by(Order.created_at.asc()).all()
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Orders"
    ws.append(["ID","Created At","Amount (kopecks)","Currency","Device ID","Customer ID"])
    for o in rows:
        ws.append([o.id, o.created_at.isoformat(), int(o.amount), o.currency, o.device_id, o.customer_id])
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    from flask import send_file
    return send_file(buf, as_attachment=True, download_name="analytics_local.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@bp.route("/workers")
@login_required
def workers_page():
    if not is_local():
        abort(403)
    return render_template("local/workers_list.html")

@bp.route("/workers/new")
@login_required
def workers_new_page():
    if not is_local():
        abort(403)
    return render_template("local/workers_add.html")

# -------- Workers: API --------
@bp.route("/api/workers", methods=["GET"])
@login_required
def api_workers_list():
    if not is_local():
        abort(403)
    rows = User.query.filter_by(parent_id=current_user.id, role="worker").order_by(User.id.asc()).all()
    return jsonify([{"id": u.id, "email": u.email, "is_enabled": u.is_enabled, "password": u.worker_password} for u in rows])

@bp.route("/api/workers", methods=["POST"])
@login_required
def api_workers_add():
    if not is_local():
        abort(403)
    p = request.get_json(force=True)
    email = (p.get("email") or "").strip()
    password = (p.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "bad input"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "exists"}), 409
    u = User(email=email, role="worker", parent_id=current_user.id, is_enabled=True)
    u.set_password(password)
    u.worker_password = password
    db.session.add(u); db.session.commit()
    return jsonify({"ok": True, "id": u.id})

@bp.route("/api/workers/<int:wid>/toggle", methods=["POST"])
@login_required
def api_workers_toggle(wid):
    if not is_local():
        abort(403)
    u = User.query.filter_by(id=wid, parent_id=current_user.id, role="worker").first()
    if not u:
        return jsonify({"error": "not found"}), 404
    u.is_enabled = not u.is_enabled
    db.session.commit()
    return jsonify({"ok": True, "is_enabled": u.is_enabled})

@bp.route("/api/workers/<int:wid>", methods=["DELETE"])
@login_required
def api_workers_delete(wid):
    if not is_local():
        abort(403)
    u = User.query.filter_by(id=wid, parent_id=current_user.id, role="worker").first()
    if not u:
        return jsonify({"error": "not found"}), 404
    db.session.delete(u)
    db.session.commit()
    return jsonify({"ok": True})

# -------- Devices CRUD (локальный только) --------
@bp.route("/api/devices", methods=["GET"])
@login_required
def api_devices_list():
    if not is_local():
        abort(403)
    from app.models import is_online
    rows = Device.query.filter_by(owner_id=current_user.id).order_by(Device.id.asc()).all()
    data = []
    for d in rows:
        data.append(dict(
            id=d.id,
            name=d.name,
            device_uid=d.device_uid,
            price_per_minute=d.price_per_minute,
            is_active=d.is_active,
            relay_state=d.relay_state,
            active_until=d.active_until.isoformat()+"Z" if d.active_until else None,
            last_seen_at=d.last_seen_at.isoformat()+"Z" if d.last_seen_at else None,
            online=is_online(d),
            allowed_minutes=d.allowed_minutes or None
        ))
    return jsonify(data)


@bp.route("/api/devices", methods=["POST"])
@login_required
def api_devices_add():
    if not is_local():
        abort(403)
    p = request.get_json(force=True)
    name = (p.get("name") or "").strip()
    uid = (p.get("device_uid") or "").strip()
    price = int(p.get("price_per_minute") or 0)
    allowed = p.get("allowed_minutes")
    if isinstance(allowed, list):
        try:
            allowed = sorted({int(x) for x in allowed if 1 <= int(x) <= 720})
        except Exception:
            allowed = None
    else:
        allowed = None

    if not name or not uid:
        return jsonify({"error": "Заполните имя и UID"}), 400

    if Device.query.filter_by(device_uid=uid).first():
        return jsonify({"error": "UID уже существует"}), 409

    d = Device(
        name=name, device_uid=uid, price_per_minute=price,
        owner_id=current_user.id, is_active=True, allowed_minutes=allowed
    )
    db.session.add(d)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "UID уже существует"}), 409

    return jsonify({"ok": True, "id": d.id})


@bp.route("/api/devices/<int:did>", methods=["GET"])
@login_required
def api_device_get(did):
    if not is_local():
        abort(403)
    from app.models import is_online
    d = Device.query.filter_by(id=did, owner_id=current_user.id).first()
    if not d:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(
        id=d.id,
        name=d.name,
        device_uid=d.device_uid,
        price_per_minute=d.price_per_minute,
        is_active=d.is_active,
        relay_state=d.relay_state,
        active_until=d.active_until.isoformat()+"Z" if d.active_until else None,
        last_seen_at=d.last_seen_at.isoformat()+"Z" if d.last_seen_at else None,
        online=is_online(d),
        allowed_minutes=d.allowed_minutes or None
    ))


@bp.route("/api/devices/<int:did>", methods=["PUT"])
@login_required
def api_device_update(did):
    if not is_local():
        abort(403)
    d = Device.query.filter_by(id=did, owner_id=current_user.id).first()
    if not d:
        return jsonify({"error": "not found"}), 404
    p = request.get_json(force=True)
    for k in ("name", "device_uid", "price_per_minute", "is_active"):
        if k in p:
            setattr(d, k, p[k])
    if "allowed_minutes" in p:
        allowed = p.get("allowed_minutes")
        if isinstance(allowed, list):
            try:
                allowed = sorted({int(x) for x in allowed if 1 <= int(x) <= 720})
            except Exception:
                allowed = None
        else:
            allowed = None
        d.allowed_minutes = allowed
    db.session.commit()
    return jsonify({"ok": True})

@bp.route("/api/devices/<int:did>", methods=["DELETE"])
@login_required
def api_device_delete(did):
    if not is_local():
        abort(403)
    d = Device.query.filter_by(id=did, owner_id=current_user.id).first()
    if not d:
        return jsonify({"error": "not found"}), 404
    db.session.delete(d)
    db.session.commit()
    return jsonify({"ok": True})

@bp.route("/api/devices/<int:did>/toggle", methods=["POST"])
@login_required
def api_device_toggle(did):
    if not is_local():
        abort(403)
    d = Device.query.filter_by(id=did, owner_id=current_user.id).first()
    if not d:
        return jsonify({"error": "not found"}), 404
    d.is_active = not d.is_active
    db.session.commit()
    return jsonify({"ok": True, "is_active": d.is_active})

# -------- Worker status / bulk --------
def _owner_id_for_status():
    if is_local():
        return current_user.id
    if is_worker():
        return current_user.parent_id
    return None

@bp.route("/api/worker/status")
@login_required
def api_worker_status():
    if current_user.role not in ("localadmin", "worker"):
        return jsonify({"error": "forbidden"}), 403

    if current_user.role == "localadmin":
        owner_id = current_user.id
    else:  # worker
        owner_id = current_user.parent_id

    if not owner_id:
        return jsonify([])

    now = datetime.utcnow()
    from app.models import is_online
    rows = Device.query.filter_by(owner_id=owner_id).all()

    out = []
    for d in rows:
        remaining = 0
        if d.relay_state and d.active_until:
            if d.active_until > now:
                remaining = int((d.active_until - now).total_seconds())
            else:
                d.relay_state = False
                d.active_until = None
        out.append({
            "id": d.id,
            "uid": d.device_uid,
            "name": d.name,
            "is_active": d.is_active,
            "relay_state": d.relay_state,
            "remaining_seconds": remaining,
            "last_seen_at": d.last_seen_at.isoformat()+"Z" if d.last_seen_at else None,
            "online": is_online(d)
        })

    db.session.commit()
    return jsonify(out)

# bulk power endpoint removed by requirement

@bp.route("/devices/<int:did>/qr", methods=["GET"])
@login_required
def device_qr(did):
    # только локальный админ
    if current_user.role != "localadmin":
        abort(403)

    d = Device.query.filter_by(id=did, owner_id=current_user.id).first()
    if not d:
        abort(404)

    # Абсолютная ссылка на публичную страницу устройства
    # endpoint: public.public_device (bp 'public', func 'public_device')
    link = url_for("public.public_device", uid=d.device_uid, _external=True)

    # Генерируем PNG QR
    import qrcode
    from io import BytesIO
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    fname = f"device-{d.device_uid}.png"
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name=fname)

