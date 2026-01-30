"""Seed script to create initial tenant and admin user."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.routers.auth import get_password_hash


def seed_database():
    """Create initial tenant and admin user."""
    db = SessionLocal()
    
    try:
        # Check if tenant exists
        tenant = db.query(Tenant).filter(Tenant.name == "Default").first()
        
        if not tenant:
            print("Creating default tenant...")
            tenant = Tenant(
                name="Default",
                config={"features": ["ocr", "classification", "rag"]}
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"Created tenant: {tenant.id}")
        else:
            print(f"Tenant already exists: {tenant.id}")
        
        # Check if admin user exists
        admin = db.query(User).filter(User.email == "admin").first()
        
        if not admin:
            print("Creating admin user...")
            admin = User(
                tenant_id=tenant.id,
                email="admin",
                hashed_password=get_password_hash("admin"),
                full_name="Administrator",
                role="admin",
                is_active="Y"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Created admin user: {admin.id}")
            print("  Username: admin")
            print("  Password: admin")
        else:
            print(f"Admin user already exists: {admin.id}")
        
        # Create operatore user
        operatore = db.query(User).filter(User.email == "user").first()
        
        if not operatore:
            print("Creating operatore user...")
            operatore = User(
                tenant_id=tenant.id,
                email="user",
                hashed_password=get_password_hash("user"),
                full_name="Operatore Demo",
                role="operatore",
                is_active="Y"
            )
            db.add(operatore)
            db.commit()
            print(f"Created operatore user: {operatore.id}")
            print("  Username: user")
            print("  Password: user")
        
        # Create manager user
        manager = db.query(User).filter(User.email == "manager@docintelrag.local").first()
        
        if not manager:
            print("Creating manager user...")
            manager = User(
                tenant_id=tenant.id,
                email="manager@docintelrag.local",
                hashed_password=get_password_hash("manager123"),
                full_name="Manager Demo",
                role="manager",
                is_active="Y"
            )
            db.add(manager)
            db.commit()
            print(f"Created manager user: {manager.id}")
            print("  Email: manager@docintelrag.local")
            print("  Password: manager123")
        
        print("\n✅ Seed completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
