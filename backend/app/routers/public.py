from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import (
    get_bot_username,
    notify_admin_booking,
    notify_admin_cancellation,
    notify_referral_reward,
    notify_student_booking,
    notify_student_cancellation,
)
from app.db import get_session
from app.dependencies import get_current_user
from app.models import AvailabilitySlot, Booking, TutorProfile, User
from app.referrals import (
    apply_referral_to_booking,
    count_available_rewards,
    describe_discount,
    get_current_slot_discount_percent,
    rollback_referral_on_cancellation,
    touch_referral_copy,
)
from app.schemas import BookingInfo, MeResponse, ReferralInfoOut, SlotOut, TutorProfileOut, UserSummary

router = APIRouter(prefix="/api", tags=["public"])


async def get_or_create_profile(session: AsyncSession) -> TutorProfile:
    profile = await session.get(TutorProfile, 1)
    if profile is None:
        profile = TutorProfile(id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


def build_referral_link(user: User) -> str | None:
    bot_username = get_bot_username()
    if not bot_username:
        return None
    return f"https://t.me/{bot_username}?start=ref_{user.telegram_id}"


async def build_referral_info(session: AsyncSession, current_user: User) -> ReferralInfoOut:
    current_discount_percent = await get_current_slot_discount_percent(session, current_user)
    reward_count = await count_available_rewards(session, current_user.id)
    return ReferralInfoOut(
        referral_link=build_referral_link(current_user),
        link_copied=current_user.referral_link_copied_at is not None,
        current_slot_discount_percent=current_discount_percent,
        reward_count=reward_count,
        referred_discount_available=bool(
            current_user.referred_by_user_id and current_user.referred_discount_used_at is None
        ),
    )


@router.get("/me", response_model=MeResponse)
async def read_me(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    profile = await get_or_create_profile(session)

    booking_result = await session.execute(
        select(Booking, AvailabilitySlot)
        .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
        .where(
            Booking.user_id == current_user.id,
            AvailabilitySlot.start_at >= datetime.now(UTC),
        )
        .order_by(AvailabilitySlot.start_at.asc())
    )
    upcoming_bookings = [
        BookingInfo(
            id=booking.id,
            slot_id=slot.id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            created_at=booking.created_at,
            discount_percent=booking.discount_percent,
            discount_label=describe_discount(booking.discount_percent, booking.discount_source),
        )
        for booking, slot in booking_result.all()
    ]

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
        referral=await build_referral_info(session, current_user),
    )


@router.get("/slots", response_model=list[SlotOut])
async def list_slots(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[SlotOut]:
    current_discount_percent = await get_current_slot_discount_percent(session, current_user)
    result = await session.execute(
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
    return [
        SlotOut(
            id=slot.id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            discount_percent=current_discount_percent,
        )
        for slot in result.scalars().all()
    ]


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
    await session.flush()
    referral_outcome = await apply_referral_to_booking(session, booking, current_user)
    await session.commit()
    await session.refresh(booking)

    slot_start = slot.start_at.astimezone().strftime("%d.%m.%Y %H:%M")
    slot_end = slot.end_at.astimezone().strftime("%H:%M")
    start_label = slot_start
    if referral_outcome.discount_label:
        start_label = f"{slot_start} | {referral_outcome.discount_label}"

    await notify_admin_booking(
        student_name=current_user.first_name,
        student_username=current_user.username,
        student_telegram_id=current_user.telegram_id,
        start_at=start_label,
        end_at=slot_end,
    )
    await notify_student_booking(
        telegram_id=current_user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
    )
    if referral_outcome.reward_owner_telegram_id:
        await notify_referral_reward(
            telegram_id=referral_outcome.reward_owner_telegram_id,
            invited_name=current_user.first_name,
        )

    return BookingInfo(
        id=booking.id,
        slot_id=slot.id,
        start_at=slot.start_at,
        end_at=slot.end_at,
        created_at=booking.created_at,
        discount_percent=booking.discount_percent,
        discount_label=describe_discount(booking.discount_percent, booking.discount_source),
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

    await rollback_referral_on_cancellation(session, booking, current_user)
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


@router.post("/referrals/copy", response_model=ReferralInfoOut)
async def copy_referral_link(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReferralInfoOut:
    await touch_referral_copy(session, current_user)
    return await build_referral_info(session, current_user)
