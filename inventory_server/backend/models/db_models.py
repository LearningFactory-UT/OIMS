from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON

from db_engine import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_id = Column(String, unique=True, nullable=False)
    original_ws_id = Column(String, nullable=False)
    ws_id = Column(String, nullable=False)
    side = Column(String, nullable=False)
    creation_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    urgent = Column(Boolean, default=False, nullable=False)
    items_json = Column(JSON, nullable=False)
    source = Column(String, default="mqtt_v1", nullable=False)
    end_time = Column(DateTime, nullable=True)
    end_reason = Column(String, nullable=True)

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "station_id": self.original_ws_id,
            "original_ws_id": self.original_ws_id,
            "ws_id": self.ws_id,
            "display_name": self.ws_id,
            "side": self.side,
            "creation_time": self.creation_time.isoformat(),
            "urgent": self.urgent,
            "items_dict": self.items_json,
            "source": self.source,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "end_reason": self.end_reason,
        }


class TimerModel(Base):
    __tablename__ = "timers"

    id = Column(Integer, primary_key=True)
    state = Column(String, default="stopped", nullable=False)
    timer_running = Column(Boolean, default=False, nullable=False)
    start_time = Column(DateTime, nullable=True)
    total_seconds = Column(Integer, default=0, nullable=False)
    paused_seconds = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SystemStateModel(Base):
    __tablename__ = "system_state"

    id = Column(Integer, primary_key=True)
    assembly_type = Column(String, default="standard", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StationModel(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True)
    original_ws_id = Column(String, unique=True, nullable=False)
    ws_id = Column(String, unique=True, nullable=False)
    role = Column(String, default="workstation", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    capabilities_json = Column(JSON, nullable=False, default=lambda: ["L", "R"])
    client_type = Column(String, default="legacy-mqtt", nullable=False)
    assignment_token = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StationSideStateModel(Base):
    __tablename__ = "station_side_states"
    __table_args__ = (UniqueConstraint("original_ws_id", "side", name="uq_station_side"),)

    id = Column(Integer, primary_key=True)
    original_ws_id = Column(String, nullable=False)
    side = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    manual_state = Column(String, default="reset", nullable=False)
    help_id = Column(String, nullable=True)
    help_idle = Column(Boolean, default=False, nullable=False)
    help_created_at = Column(DateTime, nullable=True)
    prev_ws_order_id = Column(String, nullable=True)
    prev_ws_order_idle = Column(Boolean, default=False, nullable=False)
    prev_ws_order_created_at = Column(DateTime, nullable=True)
    ready_for_next_id = Column(String, nullable=True)
    ready_for_next_created_at = Column(DateTime, nullable=True)
    andon_code = Column(String, default="R", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EventLogModel(Base):
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    station_id = Column(String, nullable=True)
    side = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
