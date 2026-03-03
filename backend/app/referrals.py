from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, ReferralReward, User

REFERRAL_WELCOME_DISCOUNT = 20
REFERRAL_OWNER_DISCOUNT = 50


@dataclass(slots=True)
class ReferralBookingOutcome:
    discount_percent: int = 0
    discount_label: str | None = None
    reward_owner_telegram_id: int | None = None


def describe_discount(discount_percent: int, discount_source: str | None) -> str | None:
    if discount_source == "referral_welcome":
        return 'Скидка 20% по акции "Приведи друга"'
    if discount_source == "referral_reward":
        return 'Скидка 50% за друга'
    if discount_percent > 0:
        return f"Скидка {discount_percent}%"
    return None


async def count_available_rewards(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(ReferralReward.id)).where(
            ReferralReward.owner_user_id == user_id,
            ReferralReward.status == "available",
        )
    )
    return int(result.scalar_one() or 0)


async def get_current_slot_discount_percent(session: AsyncSession, user: User) -> int:
    reward_count = await count_available_rewards(session, user.id)
    if reward_count > 0:
        return REFERRAL_OWNER_DISCOUNT
    if user.referred_by_user_id and user.referred_discount_used_at is None:
        return REFERRAL_WELCOME_DISCOUNT
    return 0


async def touch_referral_copy(session: AsyncSession, user: User) -> None:
    user.referral_link_copied_at = datetime.now(UTC)
    user.referral_link_copy_count += 1
    await session.commit()
    await session.refresh(user)


async def register_referral_from_start(
    session: AsyncSession,
    user: User,
    referrer_telegram_id: int | None,
) -> bool:
    if referrer_telegram_id is None:
        return False
    if user.referred_by_user_id is not None or user.telegram_id == referrer_telegram_id:
        return False
    existing_booking = await session.execute(
        select(Booking.id).where(Booking.user_id == user.id).limit(1)
    )
    if existing_booking.scalar_one_or_none() is not None:
        return False

    result = await session.execute(select(User).where(User.telegram_id == referrer_telegram_id).limit(1))
    referrer = result.scalar_one_or_none()
    if referrer is None or referrer.id == user.id:
        return False

    user.referred_by_user_id = referrer.id
    await session.commit()
    await session.refresh(user)
    return True


async def apply_referral_to_booking(
    session: AsyncSession,
    booking: Booking,
    user: User,
) -> ReferralBookingOutcome:
    now = datetime.now(UTC)

    reward_result = await session.execute(
        select(ReferralReward)
        .where(
            ReferralReward.owner_user_id == user.id,
            ReferralReward.status == "available",
        )
        .order_by(ReferralReward.granted_at.asc())
        .limit(1)
    )
    reward = reward_result.scalar_one_or_none()
    if reward is not None:
        reward.status = "used"
        reward.used_at = now
        reward.used_booking_id = booking.id
        booking.discount_percent = reward.reward_percent
        booking.discount_source = "referral_reward"
        return ReferralBookingOutcome(
            discount_percent=booking.discount_percent,
            discount_label=describe_discount(booking.discount_percent, booking.discount_source),
        )

    if user.referred_by_user_id and user.referred_discount_used_at is None:
        user.referred_discount_used_at = now
        booking.discount_percent = REFERRAL_WELCOME_DISCOUNT
        booking.discount_source = "referral_welcome"

        owner_result = await session.execute(
            select(User).where(User.id == user.referred_by_user_id).limit(1)
        )
        owner = owner_result.scalar_one_or_none()

        reward = ReferralReward(
            owner_user_id=user.referred_by_user_id,
            invitee_user_id=user.id,
            source_booking_id=booking.id,
            reward_percent=REFERRAL_OWNER_DISCOUNT,
            status="available",
        )
        session.add(reward)
        return ReferralBookingOutcome(
            discount_percent=booking.discount_percent,
            discount_label=describe_discount(booking.discount_percent, booking.discount_source),
            reward_owner_telegram_id=owner.telegram_id if owner else None,
        )

    return ReferralBookingOutcome()


async def rollback_referral_on_cancellation(
    session: AsyncSession,
    booking: Booking,
    booking_owner: User,
) -> None:
    if booking.discount_source == "referral_reward":
        reward_result = await session.execute(
            select(ReferralReward)
            .where(
                ReferralReward.used_booking_id == booking.id,
                ReferralReward.status == "used",
            )
            .limit(1)
        )
        reward = reward_result.scalar_one_or_none()
        if reward is not None:
            reward.status = "available"
            reward.used_booking_id = None
            reward.used_at = None

    if booking.discount_source == "referral_welcome":
        reward_result = await session.execute(
            select(ReferralReward)
            .where(
                ReferralReward.source_booking_id == booking.id,
                ReferralReward.status == "available",
            )
            .limit(1)
        )
        reward = reward_result.scalar_one_or_none()
        if reward is not None:
            reward.status = "revoked"

        other_discounted_booking = await session.execute(
            select(Booking.id)
            .where(
                Booking.user_id == booking_owner.id,
                Booking.discount_source == "referral_welcome",
                Booking.id != booking.id,
            )
            .limit(1)
        )
        if other_discounted_booking.scalar_one_or_none() is None:
            booking_owner.referred_discount_used_at = None
