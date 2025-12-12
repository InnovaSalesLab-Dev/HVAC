from .ghl import router as ghl_router
from .demo import router as demo_router
from fastapi import APIRouter

# Combine routers
router = APIRouter()
router.include_router(ghl_router)
router.include_router(demo_router)

__all__ = ["router"]


