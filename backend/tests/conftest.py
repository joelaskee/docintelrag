"""Pytest configuration and fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.config import Settings


@pytest.fixture(scope="session")
def settings():
    """Test settings."""
    return Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        secret_key="test-secret-key",
        debug=True,
    )


@pytest.fixture(scope="function")
def db_session(settings):
    """Create a test database session."""
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_tenant(db_session):
    """Create a sample tenant."""
    from app.models.tenant import Tenant
    
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_user(db_session, sample_tenant):
    """Create a sample user."""
    from app.models.user import User, UserRole
    from app.routers.auth import get_password_hash
    
    user = User(
        tenant_id=sample_tenant.id,
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role=UserRole.ADMIN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
