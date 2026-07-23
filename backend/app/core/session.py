from fastapi import Response

from app.core.config import settings
from app.core.security import create_access_token, create_csrf_token


def issue_session(response: Response, subject: str, token_version: int) -> None:
    max_age = settings.session_max_age_seconds
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_access_token(subject, token_version),
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=create_csrf_token(subject, token_version),
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )
    response.headers["Cache-Control"] = "no-store"
