from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.user_service import UserService

router = APIRouter()


@router.post('/register', response_model=UserResponse)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    existing_user = await service.get_user_by_username(username=user_data.username)
    if existing_user:
        raise ValueError(f"用户: username={user_data.username}已存在")

    try:
        user = await service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post('/login',  response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    username = form_data.username
    password = form_data.password
    user = await service.get_user_by_username(username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
    )
    return Token(access_token=token, token_type='bearer')

