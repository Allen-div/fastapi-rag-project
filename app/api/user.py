from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.user import UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get('/userinfo', response_model=UserResponse)
async def get_user(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    """获取用户"""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id=current_user.id)
    return user