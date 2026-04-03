from __future__ import annotations

import hashlib
import secrets


def generate_device_id() -> str:
    return f"dev_{secrets.token_hex(6)}"


def generate_device_token(role: str) -> str:
    return f"oims_{role}_{secrets.token_urlsafe(24)}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_hint(token: str) -> str:
    return token[-6:]
