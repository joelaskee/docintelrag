"""Admin router for tenant and user management."""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.routers.auth import get_current_user, require_role, get_password_hash
from app.schemas.tenant import TenantCreate, TenantRead, TenantUpdate
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


# ============ Tenant Management ============

@router.get("/tenants", response_model=List[TenantRead])
async def list_tenants(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all tenants (super admin only in multi-tenant setup)."""
    return db.query(Tenant).all()


@router.post("/tenants", response_model=TenantRead)
async def create_tenant(
    tenant: TenantCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Create a new tenant."""
    existing = db.query(Tenant).filter(Tenant.name == tenant.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant name already exists")
    
    db_tenant = Tenant(**tenant.model_dump())
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@router.patch("/tenants/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: UUID,
    update: TenantUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Update tenant configuration."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    return tenant


# ============ User Management ============

@router.get("/users", response_model=List[UserRead])
async def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all users in current tenant."""
    return db.query(User).filter(User.tenant_id == current_user.tenant_id).all()


@router.post("/users", response_model=UserRead)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Create a new user."""
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant not found")
    
    # Check email uniqueness
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = User(
        tenant_id=user.tenant_id,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    update: UserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Update a user."""
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Deactivate a user."""
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user.is_active = "N"
    db.commit()
    return {"message": "User deactivated"}


# ============ Audit Log ============

@router.get("/audit")
async def get_audit_log(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get audit log entries for current tenant."""
    from app.models.extraction import FieldEvent
    
    events = db.query(FieldEvent).join(User).filter(
        User.tenant_id == current_user.tenant_id
    ).order_by(FieldEvent.created_at.desc()).limit(100).all()
    
    return [
        {
            "id": str(e.id),
            "field_id": str(e.field_id),
            "user_id": str(e.user_id),
            "event_type": e.event_type.value,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "comment": e.comment,
            "created_at": e.created_at.isoformat()
        }
        for e in events
    ]
