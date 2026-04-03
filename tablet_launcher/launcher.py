from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import urlopen


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config.example.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def workstation_url(config: dict) -> str:
    station_id = config.get("station_id")
    device_role = config.get("device_role", "tablet")
    device_token = config.get("device_token", "")
    if not device_token:
        raise RuntimeError("No device_token configured. Run provision.py first.")
    if device_role == "tablet" and not station_id:
        raise RuntimeError("No station_id configured. Run provision.py first.")
    ui_base_url = config.get("ui_base_url", "").rstrip("/")
    if device_role == "inventory":
        return f"{ui_base_url}/inventory?token={quote(device_token)}"
    return f"{ui_base_url}/tablet?token={quote(device_token)}"


def healthcheck_url(config: dict) -> str:
    return f"{config.get('api_base_url', '').rstrip('/')}/api/system/health"


def detect_browser_command(url: str, explicit_command: list[str]) -> list[str]:
    if explicit_command:
        return [*explicit_command, url]

    system = platform.system().lower()
    if system == "darwin":
        return ["open", "-a", "Google Chrome", url, "--args", "--kiosk"]

    for candidate in ["chromium-browser", "chromium", "google-chrome", "google-chrome-stable"]:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved, "--kiosk", url]

    return [sys.executable, "-m", "webbrowser", "-t", url]


def launch_browser(config: dict):
    url = workstation_url(config)
    command = detect_browser_command(url, config.get("browser_command", []))
    return subprocess.Popen(command)


def backend_is_healthy(config: dict) -> bool:
    try:
        with urlopen(healthcheck_url(config), timeout=5) as response:
            return response.status == 200
    except URLError:
        return False


def main():
    config = load_config()
    browser_process = launch_browser(config)
    interval_seconds = int(config.get("healthcheck_interval_seconds", 15))

    try:
        while True:
            time.sleep(interval_seconds)
            if browser_process.poll() is not None:
                browser_process = launch_browser(config)
                continue
            if not backend_is_healthy(config):
                print("Backend healthcheck failed. Waiting for the control plane to recover...")
    except KeyboardInterrupt:
        if browser_process.poll() is None:
            browser_process.terminate()


if __name__ == "__main__":
    main()
