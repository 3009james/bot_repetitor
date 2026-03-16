import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from app.bot import notify_student_reminder
from app.db import SessionLocal
from app.models import AvailabilitySlot, Booking, User
from app.time_utils import format_slot_range

REMINDER_WINDOW_HOURS = 8
REMINDER_CHECK_INTERVAL_SECONDS = 300


async def ensure_runtime_schema() -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS admin_discount_percent INTEGER NULL
                """
            )
        )
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
                ALTER TABLE tutor_profile
                ADD COLUMN IF NOT EXISTS portfolio_articles_text TEXT NOT NULL
                DEFAULT 'Автор: более 10 научных статей в области машинного обучения и нейронных сетей.'
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE tutor_profile
                ADD COLUMN IF NOT EXISTS portfolio_articles_photo_path VARCHAR(1024) NULL
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE tutor_profile
                ADD COLUMN IF NOT EXISTS portfolio_programs_text TEXT NOT NULL
                DEFAULT 'Более 5 государственных регистраций программ ЭВМ.'
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE tutor_profile
                ADD COLUMN IF NOT EXISTS portfolio_programs_photo_path VARCHAR(1024) NULL
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE tutor_profile
                ADD COLUMN IF NOT EXISTS portfolio_events_text TEXT NOT NULL
                DEFAULT 'Участник конференций и хакатонов, в том числе международных.'
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE tutor_profile
                ADD COLUMN IF NOT EXISTS portfolio_events_photo_path VARCHAR(1024) NULL
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
        await session.execute(
            text(
                """
                ALTER TABLE bookings
                ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'confirmed'
                """
            )
        )
        await session.execute(
            text(
                """
                ALTER TABLE availability_slots
                ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN NOT NULL DEFAULT FALSE
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
                Booking.status == "confirmed",
                AvailabilitySlot.start_at > now,
                AvailabilitySlot.start_at <= reminder_threshold,
            )
            .order_by(AvailabilitySlot.start_at.asc())
        )
        rows = result.all()

        for booking, user, slot in rows:
            start_at, end_at = format_slot_range(slot.start_at, slot.end_at)
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
