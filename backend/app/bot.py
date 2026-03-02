from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo

from app.config import get_settings

settings = get_settings()
bot = Bot(token=settings.bot_token)
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start(message: Message) -> None:
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
