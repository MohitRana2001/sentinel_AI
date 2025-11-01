"""
Pydantic schemas for Sentinel AI backend
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, constr

from models import RBACLevel


class UserBase(BaseModel):
    """Shared attributes for user models"""
    email: EmailStr
    username: constr(min_length=3, max_length=64)  # type: ignore[var-annotated]
    rbac_level: RBACLevel
    station_id: Optional[str] = None
    district_id: Optional[str] = None
    state_id: Optional[str] = None


class UserCreate(UserBase):
    """Payload for creating a new user"""
    password: str


class UserLogin(BaseModel):
    """Payload for authenticating a user"""
    email: EmailStr
    password: str


class UserRead(UserBase):
    """Response model for returning user data"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    """JWT access token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Claims stored inside the JWT token"""
    sub: str
    rbac_level: str
    station_id: Optional[str] = None
    district_id: Optional[str] = None
    state_id: Optional[str] = None
    exp: int
