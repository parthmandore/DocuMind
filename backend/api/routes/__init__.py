from fastapi import APIRouter
from backend.api.routes.documents import router as documents_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.health import router as health_router
from backend.api.routes.search import router as search_router
from backend.api.routes.query import router as query_router
from backend.api.routes.conversations import router as conversations_router
from backend.api.routes.settings import router as settings_router
from backend.api.routes.analytics import router as analytics_router
from backend.api.routes.support import router as support_router

api_router = APIRouter(prefix="/api")
api_router.include_router(documents_router)
api_router.include_router(jobs_router)
api_router.include_router(health_router)
api_router.include_router(search_router)
api_router.include_router(query_router)
api_router.include_router(conversations_router)
api_router.include_router(settings_router)
api_router.include_router(analytics_router)
api_router.include_router(support_router)

__all__ = ["api_router"]
