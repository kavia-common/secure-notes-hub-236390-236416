from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db
from src.api.core.security import create_access_token, hash_password, verify_password
from src.api.models.user import User
from src.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create an account with email/password (password is bcrypt-hashed). Returns a JWT access token.",
    operation_id="auth_register",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Register a user.

    - Enforces unique email (case-insensitive in DB via CITEXT).
    - Stores a password hash only.
    - Returns access_token for immediate login.
    """
    user = User(email=str(payload.email), password_hash=hash_password(payload.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    await db.refresh(user)
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, token_type="bearer")


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Verify email/password and return a JWT access token.",
    operation_id="auth_login",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Login a user by email/password.

    Returns 401 for invalid credentials.
    """
    res = await db.execute(select(User).where(User.email == str(payload.email)))
    user = res.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, token_type="bearer")
