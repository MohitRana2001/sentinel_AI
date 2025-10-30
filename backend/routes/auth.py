"""
Authentication and authorization API routes
"""
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from config import settings
from database import get_db
from schemas import Token, UserCreate, UserLogin, UserRead, TokenPayload
from security import (
    bearer_scheme,
    create_access_token,
    get_current_user,
    get_password_hash,
    revoke_token,
    verify_password,
)

router = APIRouter(
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["auth"],
)


def _validate_rbac_scope(payload: UserCreate) -> None:
    """
    Ensure RBAC hierarchy metadata is present for the user's role.
    Station level requires station/district/state.
    District level requires district/state.
    State level requires state.
    """
    rbac_level = payload.rbac_level

    if rbac_level == models.RBACLevel.STATION:
        if not payload.station_id or not payload.district_id or not payload.state_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Station level users must include station_id, district_id and state_id",
            )
    elif rbac_level == models.RBACLevel.DISTRICT:
        if not payload.district_id or not payload.state_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="District level users must include district_id and state_id",
            )
    elif rbac_level == models.RBACLevel.STATE:
        if not payload.state_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="State level users must include state_id",
            )


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> models.User:
    """Create a new user with hashed password and RBAC metadata"""
    _validate_rbac_scope(payload)

    existing_user = (
        db.query(models.User)
        .filter(or_(models.User.email == payload.email, models.User.username == payload.username))
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email or username already exists",
        )

    user = models.User(
        email=str(payload.email).lower(),
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        rbac_level=payload.rbac_level,
        station_id=payload.station_id,
        district_id=payload.district_id,
        state_id=payload.state_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Authenticate user and issue JWT access token"""
    email = str(payload.email).lower()
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token_payload = {
        "sub": str(user.id),
        "rbac_level": user.rbac_level.value,
        "station_id": user.station_id,
        "district_id": user.district_id,
        "state_id": user.state_id,
    }

    access_token, expires_at = create_access_token(
        token_payload,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    expires_in = int((expires_at - datetime.now(timezone.utc)).total_seconds())

    return Token(access_token=access_token, expires_in=expires_in)


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """
    Invalidate the current token by adding it to the Redis blacklist.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        expires_at = datetime.fromtimestamp(token_data.exp, tz=timezone.utc)
        revoke_token(token, expires_at)
    except Exception:
        pass

    return {"message": f"User {current_user.username} logged out successfully"}


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Return the authenticated user's profile"""
    return current_user
