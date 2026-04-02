from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen


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


def api_request(config: dict, path: str, method: str = "GET", payload: dict | None = None):
    request = Request(
        f"{config['api_base_url'].rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def choose_station(stations: list[dict]) -> str:
    if not stations:
        return ""

    print("Available stations:")
    for index, station in enumerate(stations, start=1):
        print(f"{index}. {station['display_name']} ({station['station_id']})")

    selection = input("Select a station number or press Enter to create a new one: ").strip()
    if not selection:
        return ""
    return stations[int(selection) - 1]["station_id"]


def main():
    config = load_config()
    stations = api_request(config, "/api/stations/")
    station_id = choose_station(stations)

    if not station_id:
      station_id = input("Stable station ID: ").strip()
      display_name = input("Display name (optional): ").strip() or station_id
      created = api_request(
          config,
          "/api/stations/register",
          method="POST",
          payload={
              "station_id": station_id,
              "display_name": display_name,
              "client_type": "tablet-launcher",
              "provisioned_by": "launcher-cli",
          },
      )
      station_id = created["station_id"]

    config["station_id"] = station_id
    save_config(config)
    print(f"Saved station assignment: {station_id}")


if __name__ == "__main__":
    main()
