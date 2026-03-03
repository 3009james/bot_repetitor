from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import User
from app.referrals import register_referral_from_start

settings = get_settings()
bot = Bot(token=settings.bot_token)
dp = Dispatcher()
bot_username_cache = ""


async def initialize_bot_profile() -> None:
    global bot_username_cache
    me = await bot.get_me()
    bot_username_cache = me.username or ""


def get_bot_username() -> str:
    return bot_username_cache


def parse_start_param(message: Message) -> str | None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip() or None


async def sync_user_from_message(message: Message) -> User | None:
    from_user = message.from_user
    if from_user is None:
        return None

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == from_user.id).limit(1))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=from_user.id,
                first_name=from_user.first_name or "Ученик",
                last_name=from_user.last_name,
                username=from_user.username,
                photo_url=getattr(from_user, "photo_url", None),
                is_admin=from_user.id == settings.admin_telegram_id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            user.first_name = from_user.first_name or user.first_name
            user.last_name = from_user.last_name
            user.username = from_user.username
            user.is_admin = from_user.id == settings.admin_telegram_id
            await session.commit()
            await session.refresh(user)

        start_param = parse_start_param(message)
        referrer_telegram_id = None
        if start_param and start_param.startswith("ref_"):
            raw_id = start_param.removeprefix("ref_")
            if raw_id.isdigit():
                referrer_telegram_id = int(raw_id)
        applied_referral = await register_referral_from_start(session, user, referrer_telegram_id)
        if applied_referral:
            await message.answer(
                'Для вас активирована акция "Приведи друга": первая запись со скидкой 20%.'
            )

        return user


@dp.message(CommandStart())
async def command_start(message: Message) -> None:
    await sync_user_from_message(message)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Открыть приложение",
                    web_app=WebAppInfo(url=settings.app_url),
                )
            ]
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "Откройте приложение, чтобы посмотреть свободное время и записаться на занятие.",
        reply_markup=keyboard,
    )


@dp.message(F.web_app_data)
async def on_web_app_data(message: Message) -> None:
    await message.answer("Данные из приложения получены.")


async def notify_admin_booking(
    student_name: str,
    student_username: str | None,
    student_telegram_id: int,
    start_at: str,
    end_at: str,
) -> None:
    username_part = f"@{student_username}" if student_username else "без username"
    text = (
        "Новая запись\n\n"
        f"Ученик: {student_name}\n"
        f"Username: {username_part}\n"
        f"Telegram ID: {student_telegram_id}\n"
        f"Время: {start_at} - {end_at}"
    )
    try:
        await bot.send_message(settings.admin_telegram_id, text)
    except Exception:
        pass


async def notify_student_booking(
    telegram_id: int,
    start_at: str,
    end_at: str,
) -> None:
    text = f"Вы записаны на занятие: {start_at} - {end_at}"
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        pass


async def notify_admin_cancellation(
    student_name: str,
    student_username: str | None,
    student_telegram_id: int,
    start_at: str,
    end_at: str,
    cancelled_by: str,
) -> None:
    username_part = f"@{student_username}" if student_username else "без username"
    text = (
        "Запись отменена\n\n"
        f"Кем отменено: {cancelled_by}\n"
        f"Ученик: {student_name}\n"
        f"Username: {username_part}\n"
        f"Telegram ID: {student_telegram_id}\n"
        f"Время: {start_at} - {end_at}"
    )
    try:
        await bot.send_message(settings.admin_telegram_id, text)
    except Exception:
        pass


async def notify_student_cancellation(
    telegram_id: int,
    start_at: str,
    end_at: str,
    cancelled_by: str,
) -> None:
    text = f"Запись на {start_at} - {end_at} отменена. Инициатор: {cancelled_by}."
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        pass


async def notify_student_reminder(
    telegram_id: int,
    start_at: str,
    end_at: str,
) -> None:
    text = f"Напоминание: занятие начнется через 8 часов, {start_at} - {end_at}."
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        pass


async def notify_referral_reward(
    telegram_id: int,
    invited_name: str,
) -> None:
    text = (
        f"Ваш друг {invited_name} записался на занятие. "
        'Для вас активирована скидка 50% по акции "Приведи друга".'
    )
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        pass
