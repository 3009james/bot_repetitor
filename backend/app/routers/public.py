from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import (
    notify_admin_booking,
    notify_admin_cancellation,
    notify_student_booking,
    notify_student_cancellation,
)
from app.db import get_session
from app.dependencies import get_current_user
from app.models import AvailabilitySlot, Booking, TutorProfile, User
from app.schemas import BookingInfo, MeResponse, SlotOut, TutorProfileOut, UserSummary

router = APIRouter(prefix="/api", tags=["public"])


async def get_or_create_profile(session: AsyncSession) -> TutorProfile:
    profile = await session.get(TutorProfile, 1)
    if profile is None:
        profile = TutorProfile(id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.get("/me", response_model=MeResponse)
async def read_me(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    profile = await get_or_create_profile(session)

    booking_query = (
        select(Booking, AvailabilitySlot)
        .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
        .where(
            Booking.user_id == current_user.id,
            AvailabilitySlot.start_at >= datetime.now(UTC),
        )
        .order_by(AvailabilitySlot.start_at.asc())
    )
    booking_result = await session.execute(booking_query)
    upcoming_bookings = []
    for booking, slot in booking_result.all():
        upcoming_bookings.append(
            BookingInfo(
            id=booking.id,
            slot_id=slot.id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            created_at=booking.created_at,
        )
        )

    return MeResponse(
        user=UserSummary(
            telegram_id=current_user.telegram_id,
            first_name=current_user.first_name,
            username=current_user.username,
            photo_url=current_user.photo_url,
            is_admin=current_user.is_admin,
        ),
        profile=TutorProfileOut(
            tutor_name=profile.tutor_name,
            about_text=profile.about_text,
            tutor_photo_url=profile.tutor_photo_path,
        ),
        upcoming_bookings=upcoming_bookings,
    )


@router.get("/slots", response_model=list[SlotOut])
async def list_slots(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[SlotOut]:
    query = (
        select(AvailabilitySlot)
        .outerjoin(Booking, Booking.slot_id == AvailabilitySlot.id)
        .where(
            and_(
                AvailabilitySlot.is_active.is_(True),
                AvailabilitySlot.start_at >= datetime.now(UTC),
                Booking.id.is_(None),
            )
        )
        .order_by(AvailabilitySlot.start_at.asc())
        .limit(120)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.post("/bookings/{slot_id}", response_model=BookingInfo)
async def create_booking(
    slot_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingInfo:
    slot_result = await session.execute(
        select(AvailabilitySlot)
        .where(AvailabilitySlot.id == slot_id, AvailabilitySlot.is_active.is_(True))
        .with_for_update()
    )
    slot = slot_result.scalar_one_or_none()
    if slot is None or slot.start_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Слот недоступен")

    booking_exists = await session.execute(select(Booking.id).where(Booking.slot_id == slot.id))
    if booking_exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Это время уже занято")

    booking = Booking(user_id=current_user.id, slot_id=slot.id)
    session.add(booking)
    await session.commit()
    await session.refresh(booking)

    slot_start = slot.start_at.astimezone().strftime("%d.%m.%Y %H:%M")
    slot_end = slot.end_at.astimezone().strftime("%H:%M")

    await notify_admin_booking(
        student_name=current_user.first_name,
        student_username=current_user.username,
        student_telegram_id=current_user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
    )
    await notify_student_booking(
        telegram_id=current_user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
    )

    return BookingInfo(
        id=booking.id,
        slot_id=slot.id,
        start_at=slot.start_at,
        end_at=slot.end_at,
        created_at=booking.created_at,
    )


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    booking_result = await session.execute(
        select(Booking, AvailabilitySlot)
        .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
        .where(
            Booking.user_id == current_user.id,
            Booking.id == booking_id,
            AvailabilitySlot.start_at >= datetime.now(UTC),
        )
        .limit(1)
    )
    booking_row = booking_result.first()
    if not booking_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")

    booking, slot = booking_row
    slot_start = slot.start_at.astimezone().strftime("%d.%m.%Y %H:%M")
    slot_end = slot.end_at.astimezone().strftime("%H:%M")

    await session.delete(booking)
    await session.commit()

    await notify_admin_cancellation(
        student_name=current_user.first_name,
        student_username=current_user.username,
        student_telegram_id=current_user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
        cancelled_by="ученик",
    )
    await notify_student_cancellation(
        telegram_id=current_user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
        cancelled_by="ученик",
    )
