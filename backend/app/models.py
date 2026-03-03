from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referred_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    referred_discount_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_link_copied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_link_copy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    referred_by: Mapped["User | None"] = relationship(remote_side=[id])
    referral_rewards: Mapped[list["ReferralReward"]] = relationship(
        back_populates="owner",
        foreign_keys="ReferralReward.owner_user_id",
    )


class TutorProfile(Base):
    __tablename__ = "tutor_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    tutor_name: Mapped[str] = mapped_column(String(255), default="Ваш репетитор")
    about_text: Mapped[str] = mapped_column(Text, default="Добавьте информацию о себе в админ-панели.")
    tutor_photo_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booking: Mapped["Booking | None"] = relationship(back_populates="slot", uselist=False)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("slot_id", name="uq_booking_slot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("availability_slots.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="bookings")
    slot: Mapped[AvailabilitySlot] = relationship(back_populates="booking")


class ReferralReward(Base):
    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invitee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_percent: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[User] = relationship(
        back_populates="referral_rewards",
        foreign_keys=[owner_user_id],
    )
