# app/routes/admin.py
from flask import Blueprint, request, redirect, url_for, render_template, jsonify, session
from flask_login import login_required, current_user, login_user
from app.db import db
from app.models import User, Device, Order

bp = Blueprint("admin", __name__)

# ---- Политика доступа ----

def require_superadmin():
    return current_user.is_authenticated and current_user.role == "superadmin"

def forbid():
    return "403 Forbidden", 403

# ---- Меню суперадмина ----
@bp.route("/")
@login_required
def dashboard():
    if not require_superadmin():
        return forbid()
    return render_template("admin/dashboard.html")

# ---- Отдельные страницы ----
@bp.route("/users")
@login_required
def users_page():
    if not require_superadmin():
        return forbid()
    return render_template("admin/users_list.html")

@bp.route("/users/new")
@login_required
def users_new_page():
    if not require_superadmin():
        return forbid()
    return render_template("admin/users_add.html")

# ---- Analytics pages ----
@bp.route("/analytics")
@login_required
def analytics_page():
    if not require_superadmin():
        return forbid()
    return render_template("admin/analytics.html")

# ==================== USERS API ====================
@bp.route("/api/users", methods=["GET"])
@login_required
def api_users_list():
    if not require_superadmin():
        return forbid()
    users = User.query.order_by(User.id.asc()).all()
    data = [{"id": u.id, "email": u.email, "role": u.role, "is_enabled": getattr(u, "is_enabled", True)} for u in users]
    return jsonify(data)

@bp.route("/api/users", methods=["POST"])
@login_required
def api_users_add():
    if not require_superadmin():
        return forbid()
    payload = request.get_json(force=True)
    email = (payload.get("email") or "").strip()
    password = (payload.get("password") or "").strip()
    role = payload.get("role", "localadmin")
    if not email or not password or role not in ("localadmin", "superadmin"):
        return jsonify({"error": "bad input"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "exists"}), 409
    u = User(email=email, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return jsonify({"ok": True, "id": u.id})

@bp.route("/api/users/<int:uid>", methods=["DELETE"])
@login_required
def api_users_delete(uid):
    if not require_superadmin():
        return forbid()
    if uid == current_user.id:
        return jsonify({"error":"cannot delete yourself"}), 400
    u = User.query.get(uid)
    if not u:
        return jsonify({"error": "not found"}), 404
    if u.role == "superadmin":
        return jsonify({"error":"cannot delete superadmin"}), 400
    db.session.delete(u)
    db.session.commit()
    return jsonify({"ok": True})

# ==================== ANALYTICS API ====================
@bp.route("/api/analytics/summary", methods=["GET"])
@login_required
def api_analytics_summary():
    if not require_superadmin():
        return forbid()
    from datetime import datetime, timedelta
    range_ = request.args.get("range", "month")
    now = datetime.utcnow()
    since = None
    if range_ == "day":
        since = now - timedelta(days=1)
    elif range_ == "week":
        since = now - timedelta(days=7)
    elif range_ == "month":
        since = now - timedelta(days=30)

    total_orders = db.session.query(db.func.count(Order.id)).scalar() or 0
    if since:
        total_amount = db.session.query(db.func.coalesce(db.func.sum(Order.amount), 0)).filter(Order.created_at >= since).scalar() or 0
    else:
        total_amount = db.session.query(db.func.coalesce(db.func.sum(Order.amount), 0)).scalar() or 0

    devices = Device.query.order_by(Device.id.asc()).all()
    by_device = []
    for d in devices:
        base = db.session.query(Order).filter(Order.device_id == (d.device_uid or str(d.id)))
        if since:
            base = base.filter(Order.created_at >= since)
        cnt = base.with_entities(db.func.count(Order.id)).scalar() or 0
        amt = base.with_entities(db.func.coalesce(db.func.sum(Order.amount), 0)).scalar() or 0
        by_device.append({"id": d.id, "name": d.name, "orders": int(cnt), "amount": int(amt)})
    return jsonify({
        "total_orders": int(total_orders),
        "total_amount": int(total_amount),
        "by_device": by_device,
    })

@bp.route("/api/analytics/export.xlsx", methods=["GET"])
@login_required
def api_analytics_export():
    if not require_superadmin():
        return forbid()
    # Generate XLSX with all orders
    from io import BytesIO
    try:
        import openpyxl
    except Exception:
        return jsonify({"error": "xlsx_not_supported"}), 500
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(["ID", "Created At", "Amount (kopecks)", "Currency", "Device ID", "Customer ID"])
    for o in Order.query.order_by(Order.created_at.asc()).all():
        ws.append([o.id, o.created_at.isoformat(), int(o.amount), o.currency, o.device_id, o.customer_id])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    from flask import send_file
    return send_file(buf, as_attachment=True, download_name="analytics_full.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@bp.route("/api/users/<int:uid>/toggle", methods=["POST"])
@login_required
def api_users_toggle(uid):
    if not require_superadmin():
        return forbid()
    u = User.query.get(uid)
    if not u:
        return jsonify({"error":"not found"}), 404
    if u.role != "localadmin":
        return jsonify({"error":"only localadmin can be toggled"}), 400
    enabled = not getattr(u, "is_enabled", True)
    # если у модели ещё нет поля (на старой БД) — считаем включённым
    try:
        u.is_enabled = enabled
        from app.models import User as U
        U.query.filter_by(parent_id=u.id).update({"is_enabled": True if enabled else False})
        db.session.commit()
    except Exception:
        pass
    Device.query.filter_by(owner_id=u.id).update({"is_active": True if enabled else False})
    db.session.commit()
    return jsonify({"ok": True, "is_enabled": enabled})

@bp.route("/impersonate/<int:uid>", methods=["POST"])
@login_required
def impersonate(uid):
    if not require_superadmin():
        return forbid()
    target = User.query.get(uid)
    if not target or target.role != "localadmin":
        return jsonify({"error":"not found"}), 404
    if getattr(target, "is_enabled", True) is False:
        return jsonify({"error":"admin is disabled"}), 400
    session["sudo_original_id"] = current_user.id
    login_user(target, force=True)
    return jsonify({"ok": True, "redirect": url_for("local_admin.dashboard")})

@bp.route("/unsudo", methods=["POST"])
@login_required
def unsudo():
    orig_id = session.pop("sudo_original_id", None)
    if not orig_id:
        return jsonify({"ok": False}), 400
    admin = User.query.get(orig_id)
    if not admin or admin.role != "superadmin":
        return jsonify({"ok": False}), 400
    login_user(admin, force=True)
    return jsonify({"ok": True, "redirect": url_for("admin.dashboard")})
