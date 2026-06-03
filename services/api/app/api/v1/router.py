"""API v1 Router — aggregates all endpoint routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.avatar import router as avatar_router
from app.api.v1.design import router as design_router
from app.api.v1.search import router as search_router
from app.api.v1.wardrobe import router as wardrobe_router
from app.api.v1.tailor import router as tailor_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(avatar_router, prefix="/avatar", tags=["Avatar"])
api_router.include_router(design_router, prefix="/design", tags=["Design"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(wardrobe_router, prefix="/wardrobe", tags=["Wardrobe"])
api_router.include_router(tailor_router, prefix="/tailor", tags=["Tailoring"])
