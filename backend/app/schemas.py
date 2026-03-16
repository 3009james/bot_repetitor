from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortfolioSectionOut(BaseModel):
    title: str
    text: str
    photo_url: str | None = None


class TutorProfileOut(BaseModel):
    tutor_name: str
    about_text: str
    tutor_photo_url: str | None = None
    portfolio_sections: list[PortfolioSectionOut]


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
    status: str = "confirmed"
    discount_percent: int = 0
    discount_label: str | None = None


class ReferralInfoOut(BaseModel):
    referral_link: str | None = None
    link_copied: bool
    friend_discount_percent: int = 20
    owner_discount_percent: int = 50
    current_slot_discount_percent: int = 0
    reward_count: int = 0
    referred_discount_available: bool = False


class MeResponse(BaseModel):
    user: UserSummary
    profile: TutorProfileOut
    upcoming_bookings: list[BookingInfo]
    referral: ReferralInfoOut
    teacher_contact_url: str | None = None


class SlotOut(BaseModel):
    id: int
    start_at: datetime
    end_at: datetime
    requires_approval: bool = False
    discount_percent: int = 0

    model_config = ConfigDict(from_attributes=True)


class SlotCreate(BaseModel):
    start_at: datetime
    duration_minutes: int = Field(default=60, ge=30, le=240)
    requires_approval: bool = False


class ProfileUpdate(BaseModel):
    tutor_name: str = Field(min_length=2, max_length=255)
    about_text: str = Field(min_length=10, max_length=4000)
    portfolio_articles_text: str = Field(min_length=10, max_length=4000)
    portfolio_programs_text: str = Field(min_length=10, max_length=4000)
    portfolio_events_text: str = Field(min_length=10, max_length=4000)


class BookingListItem(BaseModel):
    id: int
    created_at: datetime
    user_first_name: str
    username: str | None = None
    user_telegram_id: int
    start_at: datetime
    end_at: datetime
    status: str = "confirmed"
    requires_approval: bool = False
    discount_percent: int = 0


class StudentDiscountItem(BaseModel):
    id: int
    telegram_id: int
    first_name: str
    username: str | None = None
    admin_discount_percent: int | None = None
    current_discount_percent: int = 0
    current_discount_label: str | None = None
    bookings_count: int = 0


class StudentDiscountUpdate(BaseModel):
    admin_discount_percent: int | None = Field(default=None, ge=0, le=100)
