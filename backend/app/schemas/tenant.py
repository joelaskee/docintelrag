"""Tenant schemas."""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TenantBase(BaseModel):
    """Base tenant schema."""
    name: str
    config: dict = {}


class TenantCreate(TenantBase):
    """Create tenant request."""
    pass


class TenantUpdate(BaseModel):
    """Update tenant request."""
    name: str | None = None
    config: dict | None = None


class TenantRead(TenantBase):
    """Tenant response."""
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)
