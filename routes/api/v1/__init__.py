from fastapi import APIRouter

from .gitops_routes import router as gitops_router
from .webhook_routes import router as webhook_router

api_v1_router = APIRouter()
api_v1_router.include_router(gitops_router, prefix="/gitops", tags=["GitOps"])
api_v1_router.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])
