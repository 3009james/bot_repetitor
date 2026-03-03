from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def get_app_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def format_slot_range(start_at: datetime, end_at: datetime) -> tuple[str, str]:
    tz = get_app_timezone()
    local_start = start_at.astimezone(tz)
    local_end = end_at.astimezone(tz)
    return local_start.strftime("%d.%m.%Y %H:%M"), local_end.strftime("%H:%M")
