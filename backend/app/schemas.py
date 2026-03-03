from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TutorProfileOut(BaseModel):
    tutor_name: str
    about_text: str
    tutor_photo_url: str | None = None


class UserSummary(BaseModel):
    telegram_id: int
    first_name: str
    username: str | None = None
    photo_url: str | None = None
    is_admin: bool


class BookingInfo(BaseModel):
    id: int
    slot_id: int
    start_at: datetime
    end_at: datetime
    created_at: datetime


class MeResponse(BaseModel):
    user: UserSummary
    profile: TutorProfileOut
    upcoming_bookings: list[BookingInfo]


class SlotOut(BaseModel):
    id: int
    start_at: datetime
    end_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlotCreate(BaseModel):
    start_at: datetime
    duration_minutes: int = Field(default=60, ge=30, le=240)


class ProfileUpdate(BaseModel):
    tutor_name: str = Field(min_length=2, max_length=255)
    about_text: str = Field(min_length=10, max_length=4000)


class BookingListItem(BaseModel):
    id: int
    created_at: datetime
    user_first_name: str
    username: str | None = None
    user_telegram_id: int
    start_at: datetime
    end_at: datetime
