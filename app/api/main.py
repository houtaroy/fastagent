from fastapi import APIRouter

from app.api.routes import session

api_router = APIRouter()
api_router.include_router(session.router)
