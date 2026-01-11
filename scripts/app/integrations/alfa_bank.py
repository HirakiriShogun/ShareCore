"""Alfa-Bank acquiring gateway helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import requests
from flask import current_app


SUCCESS_STATUSES = {1, 2}
FAIL_STATUSES = {3, 4, 6, 7, 9, 10, 11}


class AlfaBankError(Exception):
    """Raised when the Alfa-Bank gateway reports an error."""


def is_enabled() -> bool:
    """Return True if acquiring is configured and enabled."""

    cfg = current_app.config
    enabled = cfg.get("ALFABANK_ENABLED", False)
    base_url = cfg.get("ALFABANK_API_URL")
    token = cfg.get("ALFABANK_TOKEN")
    login = cfg.get("ALFABANK_LOGIN")
    password = cfg.get("ALFABANK_PASSWORD")
    
    # Проверяем что есть либо токен, либо логин+пароль
    has_auth = token or (login and password)
    return bool(enabled and base_url and has_auth)


def register_order(
    order_number: str,
    amount: int,
    return_url: str,
    fail_url: str,
    *,
    description: Optional[str] = None,
    callback_url: Optional[str] = None,
    extra_json: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a payment order in the gateway."""

    payload: Dict[str, Any] = {
        "orderNumber": order_number,
        "amount": amount,
        "returnUrl": return_url,
        "failUrl": fail_url,
        "language": "ru",
    }

    currency = current_app.config.get("ALFABANK_CURRENCY")
    if currency:
        payload["currency"] = currency

    page_view = current_app.config.get("ALFABANK_PAGE_VIEW")
    if page_view:
        payload["pageView"] = page_view

    if description:
        payload["description"] = description[:512]

    json_blob = extra_json.copy() if extra_json else {}
    if callback_url:
        json_blob.setdefault("callbackUrl", callback_url)

    if json_blob:
        payload["jsonParams"] = json.dumps(json_blob, ensure_ascii=False)

    if client_ip:
        payload["clientIp"] = client_ip

    return _call_gateway("register.do", payload)


def fetch_order_status(
    *,
    order_id: Optional[str] = None,
    order_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch status details for an order."""

    if not order_id and not order_number:
        raise AlfaBankError("order_id or order_number required")

    payload: Dict[str, Any] = {}
    if order_id:
        payload["orderId"] = order_id
    if order_number:
        payload["orderNumber"] = order_number

    try:
        return _call_gateway("getOrderStatusExtended.do", payload)
    except AlfaBankError:
        return _call_gateway("getOrderStatus.do", payload)


def normalize_status(data: Dict[str, Any]) -> Tuple[str, Optional[int]]:
    """Return (status_str, status_code) based on gateway payload."""

    raw = data.get("orderStatus")
    try:
        code = int(raw)
    except (TypeError, ValueError):
        return "unknown", None

    if code in SUCCESS_STATUSES:
        return "succeeded", code
    if code in FAIL_STATUSES:
        return "canceled", code
    return "pending", code


def _call_gateway(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    base_url = (current_app.config.get("ALFABANK_API_URL") or "").rstrip("/")
    if not base_url:
        raise AlfaBankError("ALFABANK_API_URL not configured")

    token = current_app.config.get("ALFABANK_TOKEN")
    login = current_app.config.get("ALFABANK_LOGIN")
    password = current_app.config.get("ALFABANK_PASSWORD")

    # Приоритет у токена, если он есть
    if token:
        data = {
            "token": token,
            **payload,
        }
    elif login and password:
        data = {
            "userName": login,
            "password": password,
            **payload,
        }
    else:
        raise AlfaBankError("ALFABANK_TOKEN or ALFABANK_LOGIN/PASSWORD not configured")

    url = f"{base_url}/{endpoint}"

    try:
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise AlfaBankError(f"HTTP error calling gateway: {exc}") from exc

    try:
        body = resp.json()
    except ValueError as exc:
        raise AlfaBankError("Gateway returned non-JSON response") from exc

    error_code = str(body.get("errorCode", "0"))
    if error_code not in ("0", "00", ""):  # non-zero is error
        message = (
            body.get("errorMessage")
            or body.get("errorDescription")
            or body.get("actionCodeDescription")
            or f"Gateway error {error_code}"
        )
        raise AlfaBankError(message)

    return body

