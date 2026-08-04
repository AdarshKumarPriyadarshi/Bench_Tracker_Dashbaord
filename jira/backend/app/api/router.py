from fastapi import APIRouter

from app.api.defects import router as defects_router

api_router = APIRouter()
api_router.include_router(defects_router)
