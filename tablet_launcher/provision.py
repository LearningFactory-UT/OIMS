from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config.example.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def main():
    config = load_config()
    role = input("Device role (tablet/inventory) [tablet]: ").strip().lower() or "tablet"
    if role not in {"tablet", "inventory"}:
        raise ValueError("Role must be 'tablet' or 'inventory'.")

    station_id = ""
    if role == "tablet":
        station_id = input("Stable station ID: ").strip()
        if not station_id:
            raise ValueError("A tablet must be assigned to a station_id.")

    device_token = input("Device token: ").strip()
    if not device_token:
        raise ValueError("A device token is required.")

    config["device_role"] = role
    config["station_id"] = station_id
    config["device_token"] = device_token
    save_config(config)
    if role == "inventory":
        print("Saved inventory device configuration.")
        return
    print(f"Saved station assignment: {station_id}")


if __name__ == "__main__":
    main()
