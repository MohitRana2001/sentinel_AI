from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, constr

from models import RBACLevel


class UserBase(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=64)  # type: ignore[var-annotated]
    rbac_level: RBACLevel
    manager_id: Optional[int] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    rbac_level: str
    manager_id: Optional[int] = None
    exp: int
