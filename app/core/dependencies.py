from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("username")
    user_id: int = payload.get("sub")

    if username is None or user_id is None:
        raise credentials_exception

    token_data = TokenData(username=username, user_id=user_id)

    result = await db.execute(
        select(User).where(User.id == token_data.user_id, User.username == token_data.username)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# async def get_current_active_user(
#         current_user: User = Depends(get_current_user),
# ) -> User:
#     """获取当前活跃用户"""
#     if not current_user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Inactive user"
#         )
#     return current_user
#

async def get_current_user_optional(
        token: Optional[str] = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """可选地获取当前用户（用于公开API）"""
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None