import uuid
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str
    role: str


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    exp: Optional[int] = None


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[str] = "staff"


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True
