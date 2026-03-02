import hashlib
import hmac
import json
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import HTTPException, status


@dataclass(slots=True)
class TelegramAuthUser:
    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None


def validate_init_data(init_data: str, bot_token: str) -> TelegramAuthUser:
    parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Telegram hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram signature")

    raw_user = parsed_data.get("user")
    if not raw_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Telegram user")

    user = json.loads(raw_user)
    return TelegramAuthUser(
        telegram_id=user["id"],
        first_name=user.get("first_name", "Ученик"),
        last_name=user.get("last_name"),
        username=user.get("username"),
        photo_url=user.get("photo_url"),
    )

