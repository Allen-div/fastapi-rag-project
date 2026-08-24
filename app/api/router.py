from app.api import auth, document, chat

from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(document.router, prefix='/document', tags=['文档'])
api_router.include_router(chat.router, prefix='/chat', tags=['对话'])
