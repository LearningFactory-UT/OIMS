# backend/models/db_models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.sqlite import JSON
from db_engine import Base
from datetime import datetime

class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_id = Column(String, unique=True, nullable=False)
    ws_id = Column(String, nullable=False)  # Single “workstation ID”
    side = Column(String, nullable=False)
    creation_time = Column(DateTime, default=datetime.utcnow)
    urgent = Column(Boolean, default=False)
    items_json = Column(JSON, nullable=False)
    end_time = Column(DateTime, nullable=True)
    end_reason = Column(String, nullable=True)

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "ws_id": self.ws_id,
            "side": self.side,
            "creation_time": self.creation_time.isoformat(),
            "urgent": self.urgent,
            "items_dict": self.items_json,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "end_reason": self.end_reason,
        }


class TimerModel(Base):
    __tablename__ = "timers"

    id = Column(Integer, primary_key=True)
    timer_running = Column(Boolean, default=False)
    start_time = Column(DateTime, nullable=True)
    total_seconds = Column(Integer, default=0)