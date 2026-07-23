import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(subject: str, token_version: int = 0) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": subject, "ver": token_version, "exp": expires},
        settings.secret_key,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> tuple[str, int] | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        subject = payload.get("sub")
        if not subject:
            return None
        return subject, int(payload.get("ver", 0))
    except jwt.PyJWTError:
        return None


def create_csrf_token(subject: str, token_version: int) -> str:
    nonce = secrets.token_urlsafe(32)
    message = f"{nonce}:{subject}:{token_version}".encode()
    signature = hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()
    return f"{nonce}.{signature}"


def verify_csrf_token(token: str, subject: str, token_version: int) -> bool:
    try:
        nonce, signature = token.rsplit(".", 1)
    except ValueError:
        return False
    if not nonce or not signature:
        return False
    message = f"{nonce}:{subject}:{token_version}".encode()
    expected = hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
