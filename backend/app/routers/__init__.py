"""API routers."""
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.ingestion import router as ingestion_router
from app.routers.chat import router as chat_router
from app.routers.dashboard import router as dashboard_router
from app.routers.admin import router as admin_router

__all__ = [
    "health_router",
    "auth_router", 
    "documents_router",
    "ingestion_router",
    "chat_router",
    "dashboard_router",
    "admin_router",
]
