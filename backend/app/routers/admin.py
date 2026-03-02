from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.dependencies import require_admin
from app.models import AvailabilitySlot, Booking, User
from app.routers.public import get_or_create_profile
from app.schemas import BookingListItem, ProfileUpdate, SlotCreate, SlotOut, TutorProfileOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
    return TutorProfileOut(
        tutor_name=profile.tutor_name,
        about_text=profile.about_text,
        tutor_photo_url=profile.tutor_photo_path,
    )


@router.patch("/profile", response_model=TutorProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> TutorProfileOut:
    profile = await get_or_create_profile(session)
    profile.tutor_name = payload.tutor_name
    profile.about_text = payload.about_text
    await session.commit()
    await session.refresh(profile)
    return TutorProfileOut(
        tutor_name=profile.tutor_name,
        about_text=profile.about_text,
        tutor_photo_url=profile.tutor_photo_path,
    )


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

    return TutorProfileOut(
        tutor_name=profile.tutor_name,
        about_text=profile.about_text,
        tutor_photo_url=profile.tutor_photo_path,
    )


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
        )
        for booking, user, slot in rows
    ]

