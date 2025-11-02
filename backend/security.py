from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User
from redis_pubsub import redis_pubsub
from schemas import TokenPayload
from passlib.context import CryptContext

bearer_scheme = HTTPBearer(description="JWT authorization header using the Bearer scheme")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis key prefix for revoked tokens
TOKEN_BLACKLIST_PREFIX = "sentinel:auth:revoked:"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password using bcrypt.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
    """Create a signed JWT with expiry"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, expire


def _blacklist_key(token: str) -> str:
    """Generate Redis key for a revoked token"""
    return f"{TOKEN_BLACKLIST_PREFIX}{token}"


def revoke_token(token: str, expires_at: datetime) -> None:
    """Store token in Redis blacklist until it would naturally expire"""
    if not token:
        return

    ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    if ttl_seconds <= 0:
        return

    try:
        redis_pubsub.redis_client.setex(_blacklist_key(token), ttl_seconds, "1")
    except RedisError as exc:
        # Log and continue; logout still succeeds but token will expire naturally
        print(f"Failed to revoke token in Redis: {exc}")


def is_token_revoked(token: str) -> bool:
    """Check if token exists in blacklist"""
    try:
        return bool(redis_pubsub.redis_client.exists(_blacklist_key(token)))
    except RedisError as exc:
        print(f"Redis lookup failed while validating token: {exc}")
        return False


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the current user from the Authorization header.
    Raises 401 if token invalid/expired/revoked, or user not found.
    """
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")

    token = credentials.credentials

    if is_token_revoked(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print(f"🔍 Decoded JWT payload: {payload}")
        token_data = TokenPayload(**payload)
        print(f"TokenPayload validated successfully")
    except JWTError as e:
        print(f"JWT decode error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    except Exception as e:
        print(f"TokenPayload validation error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = int(token_data.sub)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
