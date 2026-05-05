from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AdminSession, AdminUser


SESSION_COOKIE_NAME = "sdp_admin_session"
SESSION_DAYS = 7
PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


def create_admin_session(user: AdminUser, response: Response, db: Session) -> None:
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=SESSION_DAYS)
    db.add(AdminSession(token_hash=_hash_token(raw_token), user_id=user.id, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_admin_session(response: Response, token: str | None, db: Session) -> None:
    if token:
        session = db.query(AdminSession).filter(AdminSession.token_hash == _hash_token(token)).first()
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def require_admin_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AdminUser:
    if not session_token:
        raise _unauthorized()

    session = db.query(AdminSession).filter(AdminSession.token_hash == _hash_token(session_token)).first()
    if not session or session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        if session:
            db.delete(session)
            db.commit()
        raise _unauthorized()

    user = db.get(AdminUser, session.user_id)
    if not user:
        raise _unauthorized()
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin login required")
