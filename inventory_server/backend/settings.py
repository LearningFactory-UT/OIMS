from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
CONFIG_JSON_PATH = BACKEND_DIR / "config" / "config.json"
DEFAULT_DATABASE_PATH = BACKEND_DIR / "my_persistent_data.db"


def _load_json_defaults() -> dict:
    if not CONFIG_JSON_PATH.exists():
        return {}
    with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sqlite_url_for(path: Path) -> str:
    return f"sqlite:///{path.resolve()}"


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    secret_key: str
    broker_hostname: str
    broker_port: int
    database_url: str
    cors_origins: list[str]
    bootstrap_token: str
    station_heartbeat_timeout_seconds: int


def load_settings() -> Settings:
    json_defaults = _load_json_defaults()
    database_url = os.getenv("OIMS_DATABASE_URL") or _sqlite_url_for(DEFAULT_DATABASE_PATH)
    cors_origins = [
        origin.strip()
        for origin in os.getenv("OIMS_CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    return Settings(
        host=os.getenv("OIMS_HOST", "0.0.0.0"),
        port=int(os.getenv("OIMS_PORT", "3010")),
        secret_key=os.getenv("OIMS_SECRET_KEY", "oims-development-secret"),
        broker_hostname=os.getenv(
            "OIMS_BROKER_HOSTNAME",
            json_defaults.get("broker_hostname", "rtlsserver.local"),
        ),
        broker_port=int(os.getenv("OIMS_BROKER_PORT", json_defaults.get("port", 1883))),
        database_url=database_url,
        cors_origins=cors_origins or ["*"],
        bootstrap_token=os.getenv("OIMS_BOOTSTRAP_TOKEN", "learning-factory-bootstrap"),
        station_heartbeat_timeout_seconds=int(
            os.getenv("OIMS_STATION_HEARTBEAT_TIMEOUT_SECONDS", "45")
        ),
    )


settings = load_settings()

