import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from app.bot import notify_student_reminder
from app.db import SessionLocal
from app.models import AvailabilitySlot, Booking, User

REMINDER_WINDOW_HOURS = 8
REMINDER_CHECK_INTERVAL_SECONDS = 300


async def ensure_runtime_schema() -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS referred_by_user_id INTEGER NULL
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS referred_discount_used_at TIMESTAMPTZ NULL
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS referral_link_copied_at TIMESTAMPTZ NULL
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS referral_link_copy_count INTEGER NOT NULL DEFAULT 0
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE bookings
                ADD COLUMN IF NOT EXISTS discount_percent INTEGER NOT NULL DEFAULT 0
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE bookings
                ADD COLUMN IF NOT EXISTS discount_source VARCHAR(64) NULL
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE bookings
                ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ NULL
                """
            )
        )
        await session.commit()


async def send_due_reminders() -> None:
    now = datetime.now(UTC)
    reminder_threshold = now + timedelta(hours=REMINDER_WINDOW_HOURS)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Booking, User, AvailabilitySlot)
            .join(User, Booking.user_id == User.id)
            .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
            .where(
                Booking.reminder_sent_at.is_(None),
                AvailabilitySlot.start_at > now,
                AvailabilitySlot.start_at <= reminder_threshold,
            )
            .order_by(AvailabilitySlot.start_at.asc())
        )
        rows = result.all()

        for booking, user, slot in rows:
            start_at = slot.start_at.astimezone().strftime("%d.%m.%Y %H:%M")
            end_at = slot.end_at.astimezone().strftime("%H:%M")
            await notify_student_reminder(
                telegram_id=user.telegram_id,
                start_at=start_at,
                end_at=end_at,
            )
            booking.reminder_sent_at = now

        if rows:
            await session.commit()


async def reminder_worker() -> None:
    while True:
        try:
            await send_due_reminders()
        except Exception:
            pass
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)
