"""User and auth schemas."""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    """Base user schema."""
    email: str
    full_name: str | None = None
    role: str = "operatore"


class UserCreate(UserBase):
    """Create user request."""
    password: str
    tenant_id: UUID


class UserUpdate(BaseModel):
    """Update user request."""
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    password: str | None = None
    is_active: str | None = None


class UserRead(UserBase):
    """User response."""
    id: UUID
    tenant_id: UUID
    is_active: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token payload."""
    user_id: UUID | None = None
    tenant_id: UUID | None = None
    role: str | None = None

