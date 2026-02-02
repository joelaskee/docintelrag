
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.routers.auth import get_password_hash
# Assuming Tenant model exists and is imported via base or direct
# But wait, where is Tenant defined? 
# Usually models are imported in main or base. 
# Let's inspect user.py again to see where Tenant is imported from if at all.
# It says `tenant = relationship("Tenant", ...)`
# If Tenant is not imported, SQLAlchemy might complain if we try to use it.
# But let's try to find it.

from app.models.user import Base # hopefully Base has all models registered if they were terminated
# Or try import
try:
    from app.models.tenant import Tenant
except ImportError:
    # Maybe defined in same file? No.
    # Maybe define a dummy class if we only need ID? No, need to query table.
    pass

def create_user():
    db = SessionLocal()
    try:
        # Check tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            print("Creating tenant...")
            tenant = Tenant(name="Default Tenant")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        
        print(f"Using tenant: {tenant.id}")

        email = "admin@example.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print("Creating user...")
            user = User(
                email=email,
                hashed_password=get_password_hash("admin"),
                tenant_id=tenant.id,
                role=UserRole.ADMIN,
                full_name="Admin User",
                is_active="Y"
            )
            db.add(user)
            db.commit()
            print("User created successfully")
        else:
            print("User already exists, updating password...")
            user.hashed_password = get_password_hash("admin")
            user.is_active = "Y"
            db.commit()
            print("User updated")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_user()
