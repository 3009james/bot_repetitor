from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import notify_admin_cancellation, notify_student_cancellation
from app.config import get_settings
from app.db import get_session
from app.dependencies import require_admin
from app.models import AvailabilitySlot, Booking, User
from app.referrals import rollback_referral_on_cancellation
from app.routers.public import build_profile_payload, get_or_create_profile
from app.schemas import BookingListItem, ProfileUpdate, SlotCreate, SlotOut, TutorProfileOut

router = APIRouter(prefix="/api/admin", tags=["admin"])

PORTFOLIO_SECTION_FIELDS = {
    "articles": "portfolio_articles_photo_path",
    "programs": "portfolio_programs_photo_path",
    "events": "portfolio_events_photo_path",
}


def ensure_upload_dir() -> Path:
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


@router.get("/profile", response_model=TutorProfileOut)
async def get_profile(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> TutorProfileOut:
    profile = await get_or_create_profile(session)
    return build_profile_payload(profile)


@router.patch("/profile", response_model=TutorProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> TutorProfileOut:
    profile = await get_or_create_profile(session)
    profile.tutor_name = payload.tutor_name
    profile.about_text = payload.about_text
    profile.portfolio_articles_text = payload.portfolio_articles_text
    profile.portfolio_programs_text = payload.portfolio_programs_text
    profile.portfolio_events_text = payload.portfolio_events_text
    await session.commit()
    await session.refresh(profile)
    return build_profile_payload(profile)


@router.post("/profile/photo", response_model=TutorProfileOut)
async def upload_profile_photo(
    photo: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> TutorProfileOut:
    profile = await get_or_create_profile(session)
    upload_dir = ensure_upload_dir()
    extension = Path(photo.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{uuid4().hex}{extension}"
    file_path = upload_dir / filename
    file_path.write_bytes(await photo.read())

    profile.tutor_photo_path = f"/uploads/{filename}"
    await session.commit()
    await session.refresh(profile)

    return build_profile_payload(profile)


@router.post("/profile/portfolio-photo/{section}", response_model=TutorProfileOut)
async def upload_portfolio_photo(
    section: str,
    photo: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> TutorProfileOut:
    profile = await get_or_create_profile(session)
    target_field = PORTFOLIO_SECTION_FIELDS.get(section)
    if target_field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Раздел портфолио не найден")

    upload_dir = ensure_upload_dir()
    extension = Path(photo.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{uuid4().hex}{extension}"
    file_path = upload_dir / filename
    file_path.write_bytes(await photo.read())

    setattr(profile, target_field, f"/uploads/{filename}")
    await session.commit()
    await session.refresh(profile)
    return build_profile_payload(profile)


@router.post("/slots", response_model=SlotOut)
async def create_slot(
    payload: SlotCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> SlotOut:
    slot = AvailabilitySlot(
        start_at=payload.start_at,
        end_at=payload.start_at + timedelta(minutes=payload.duration_minutes),
        is_active=True,
    )
    session.add(slot)
    await session.commit()
    await session.refresh(slot)
    return slot


@router.get("/slots", response_model=list[SlotOut])
async def list_all_slots(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> list[SlotOut]:
    result = await session.execute(
        select(AvailabilitySlot)
        .where(AvailabilitySlot.is_active.is_(True))
        .order_by(AvailabilitySlot.start_at.asc())
        .limit(200)
    )
    return list(result.scalars().all())


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> None:
    slot = await session.get(AvailabilitySlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Слот не найден")

    booking_exists = await session.execute(select(Booking.id).where(Booking.slot_id == slot.id))
    if booking_exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя удалить занятый слот")

    slot.is_active = False
    await session.commit()


@router.get("/bookings", response_model=list[BookingListItem])
async def list_bookings(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> list[BookingListItem]:
    result = await session.execute(
        select(Booking, User, AvailabilitySlot)
        .join(User, Booking.user_id == User.id)
        .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
        .order_by(AvailabilitySlot.start_at.asc())
        .limit(200)
    )
    rows = result.all()
    return [
        BookingListItem(
            id=booking.id,
            created_at=booking.created_at,
            user_first_name=user.first_name,
            username=user.username,
            user_telegram_id=user.telegram_id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            discount_percent=booking.discount_percent,
        )
        for booking, user, slot in rows
    ]


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> None:
    result = await session.execute(
        select(Booking, User, AvailabilitySlot)
        .join(User, Booking.user_id == User.id)
        .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
        .where(Booking.id == booking_id)
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")

    booking, user, slot = row
    slot_start = slot.start_at.astimezone().strftime("%d.%m.%Y %H:%M")
    slot_end = slot.end_at.astimezone().strftime("%H:%M")

    await rollback_referral_on_cancellation(session, booking, user)
    await session.delete(booking)
    await session.commit()

    await notify_admin_cancellation(
        student_name=user.first_name,
        student_username=user.username,
        student_telegram_id=user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
        cancelled_by="администратор",
    )
    await notify_student_cancellation(
        telegram_id=user.telegram_id,
        start_at=slot_start,
        end_at=slot_end,
        cancelled_by="администратор",
    )
