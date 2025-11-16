import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "devkey")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:demos1110@localhost:5432/rentdb"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ALFABANK_ENABLED = _env_bool("ALFABANK_ENABLED", False)
    ALFABANK_API_URL = os.environ.get("ALFABANK_API_URL", "https://alfa.rbsuat.com/payment/rest")
    ALFABANK_TOKEN = os.environ.get("ALFABANK_TOKEN", "")
    ALFABANK_LOGIN = os.environ.get("ALFABANK_LOGIN", "")
    ALFABANK_PASSWORD = os.environ.get("ALFABANK_PASSWORD", "")
    # Валюта опциональна, если не указана - не передаём в API
    _currency = os.environ.get("ALFABANK_CURRENCY", "")
    ALFABANK_CURRENCY = int(_currency) if _currency and _currency.isdigit() else None
    ALFABANK_PAGE_VIEW = os.environ.get("ALFABANK_PAGE_VIEW", "") or None