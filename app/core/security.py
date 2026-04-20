import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services.users import User, get_user


bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _sign(message: str, secret_key: str) -> str:
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return _b64encode(digest.digest())


def create_access_token(username: str, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expire_minutes)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "role": role, "exp": int(expires_at.timestamp())}

    header_part = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}"
    signature = _sign(signing_input, settings.secret_key)
    return f"{signing_input}.{signature}", expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        header_part, payload_part, signature = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected_signature = _sign(signing_input, settings.secret_key)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("invalid signature")
        payload = json.loads(_b64decode(payload_part))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed access token.",
        ) from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please log in again.",
        )
    return payload


def authenticate_user(username: str, password: str) -> User | None:
    user = get_user(username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token. Log in first and send Authorization: Bearer <token>.",
        )

    payload = decode_access_token(credentials.credentials)
    username = payload.get("sub")
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
