from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme)
) -> User:
    """从 JWT 直接解析当前用户，不查数据库，减少一次 MySQL 往返。

    注意：JWT 在过期前即使账号被禁用/删除也仍有效，如需即时吊销可改为查库或加 Redis 缓存。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    username = payload.get("username")
    user_id_raw = payload.get("sub")

    if username is None or user_id_raw is None:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise credentials_exception

    # 构造轻量 User 对象（detached），业务层仅读取 id/username 等字段
    return User(id=user_id, username=username, is_active=True)


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
) -> Optional[User]:
    """可选地获取当前用户（用于公开API）"""
    if not token:
        return None

    try:
        return await get_current_user(token)
    except HTTPException:
        return None