import os
import hmac
import hashlib
import re
import secrets
import time

from fastapi import Header, HTTPException, Request, status


PRINTER_DIGEST_NONCE_MAX_AGE_SECONDS = 300


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_KEY", "dev-secret")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def require_printer_digest_auth(request: Request) -> str:
    realm = os.getenv("PRINTER_POLL_REALM", "epson-sdp")
    password = os.getenv("PRINTER_POLL_PASSWORD", "dev-printer-secret")
    authorization = request.headers.get("authorization")

    if not authorization or not authorization.lower().startswith("digest "):
        raise _printer_digest_challenge(realm)

    digest_fields = _parse_digest_authorization(authorization.split(" ", 1)[1])
    username = digest_fields.get("username")
    nonce = digest_fields.get("nonce")
    uri = digest_fields.get("uri")
    response = digest_fields.get("response")
    qop = digest_fields.get("qop")
    nc = digest_fields.get("nc")
    cnonce = digest_fields.get("cnonce")

    if (
        not username
        or digest_fields.get("realm") != realm
        or not nonce
        or not uri
        or not response
        or not _valid_digest_nonce(nonce)
    ):
        raise _printer_digest_challenge(realm)

    request_uri = request.url.path
    if request.url.query:
        request_uri = f"{request_uri}?{request.url.query}"
    if uri != request_uri:
        raise _printer_digest_challenge(realm)

    ha1 = _md5_hex(f"{username}:{realm}:{password}")
    ha2 = _md5_hex(f"{request.method}:{uri}")
    if qop:
        if qop != "auth" or not nc or not cnonce:
            raise _printer_digest_challenge(realm)
        expected_response = _md5_hex(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    else:
        expected_response = _md5_hex(f"{ha1}:{nonce}:{ha2}")

    if not hmac.compare_digest(response, expected_response):
        raise _printer_digest_challenge(realm)

    return username


def _printer_digest_challenge(realm: str) -> HTTPException:
    nonce = _make_digest_nonce()
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing printer credentials",
        headers={
            "WWW-Authenticate": (
                f'Digest realm="{realm}", '
                f'nonce="{nonce}", '
                'algorithm=MD5, '
                'qop="auth"'
            )
        },
    )


def _make_digest_nonce() -> str:
    timestamp = str(int(time.time()))
    random_value = secrets.token_urlsafe(12)
    value = f"{timestamp}:{random_value}"
    signature = hmac.new(_digest_nonce_secret(), value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{value}:{signature}"


def _valid_digest_nonce(nonce: str) -> bool:
    parts = nonce.split(":")
    if len(parts) != 3:
        return False

    timestamp, random_value, signature = parts
    try:
        age = time.time() - int(timestamp)
    except ValueError:
        return False
    if age < 0 or age > PRINTER_DIGEST_NONCE_MAX_AGE_SECONDS:
        return False

    value = f"{timestamp}:{random_value}"
    expected_signature = hmac.new(_digest_nonce_secret(), value.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def _digest_nonce_secret() -> bytes:
    secret = os.getenv("PRINTER_POLL_NONCE_SECRET") or os.getenv("API_KEY", "dev-secret")
    return secret.encode("utf-8")


def _parse_digest_authorization(value: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pattern = re.compile(r'(\w+)=(?:"((?:[^"\\]|\\.)*)"|([^,]*))')
    for match in pattern.finditer(value):
        raw_value = match.group(2) if match.group(2) is not None else match.group(3)
        fields[match.group(1)] = raw_value.replace(r"\"", '"').strip()
    return fields


def _md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()
