# backend/utils/time_utils.py
from datetime import datetime

def parse_isoformat(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)