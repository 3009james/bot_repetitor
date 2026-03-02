from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import User
from app.security import TelegramAuthUser, validate_init_data


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_telegram_init_data: Annotated[str | None, Header()] = None,
    x_debug_user_id: Annotated[int | None, Header()] = None,
    x_debug_user_name: Annotated[str | None, Header()] = None,
    x_debug_is_admin: Annotated[bool | None, Header()] = None,
) -> User:
    settings = get_settings()

    if settings.dev_bypass_auth and x_debug_user_id:
        auth_user = TelegramAuthUser(
            telegram_id=x_debug_user_id,
            first_name=x_debug_user_name or "Debug User",
            last_name=None,
            username=None,
            photo_url=None,
        )
        force_admin = bool(x_debug_is_admin)
    else:
        if not x_telegram_init_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram auth required")
        auth_user = validate_init_data(x_telegram_init_data, settings.bot_token)
        force_admin = auth_user.telegram_id == settings.admin_telegram_id

    result = await session.execute(select(User).where(User.telegram_id == auth_user.telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=auth_user.telegram_id,
            first_name=auth_user.first_name,
            last_name=auth_user.last_name,
            username=auth_user.username,
            photo_url=auth_user.photo_url,
            is_admin=force_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    user.first_name = auth_user.first_name
    user.last_name = auth_user.last_name
    user.username = auth_user.username
    user.photo_url = auth_user.photo_url
    user.is_admin = force_admin
    await session.commit()
    await session.refresh(user)
    return user


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

