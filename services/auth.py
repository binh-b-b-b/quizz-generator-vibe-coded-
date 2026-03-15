import os
import json
import uuid
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

USERS_FILE = Path("users.json")
JWT_SECRET  = os.getenv("JWT_SECRET", "changeme")
ALGORITHM   = "HS256"
TOKEN_EXPIRE_DAYS = 7

bearer  = HTTPBearer()


# ── File helpers ─────────────────────────────────────

def _read_users() -> list:
    if not USERS_FILE.exists():
        return []
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_users(users: list):
    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── Password helpers ─────────────────────────────────

import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── User operations ──────────────────────────────────

def create_user(username: str, password: str) -> dict:
    """Register a new user. Raises if username already taken."""
    users = _read_users()
    if any(u["username"] == username for u in users):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
    }
    users.append(user)
    _write_users(users)
    return user


def authenticate_user(username: str, password: str) -> dict:
    """Check credentials. Raises if invalid."""
    users = _read_users()
    user = next((u for u in users if u["username"] == username), None)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    return user


# ── Token operations ─────────────────────────────────

def create_token(user: dict) -> str:
    """Generate a signed JWT containing the user ID."""
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """
    FastAPI dependency — validates the Bearer token on protected routes.
    Usage: add `user = Depends(get_current_user)` to any endpoint.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return {"id": payload["sub"], "username": payload["username"]}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )