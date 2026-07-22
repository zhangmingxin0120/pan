import hashlib
import hmac
import secrets

from app.core.config import settings


def api_key_hash(api_key: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    prefix = secrets.token_hex(6)
    api_key = f"pan_{prefix}_{secrets.token_urlsafe(32)}"
    return api_key, prefix, api_key_hash(api_key)


def api_key_prefix(api_key: str) -> str | None:
    parts = api_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "pan" or len(parts[1]) != 12:
        return None
    return parts[1]
