from __future__ import annotations

import hashlib
import secrets

from settings import settings


DEVICE_TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_device_id() -> str:
    return f"dev_{secrets.token_hex(6)}"


def generate_device_token(_role: str) -> str:
    return "".join(
        secrets.choice(DEVICE_TOKEN_ALPHABET)
        for _ in range(settings.device_token_length)
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_hint(token: str) -> str:
    return token[-6:]
