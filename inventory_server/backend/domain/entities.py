from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Literal, Optional


OperatorSide = Literal["L", "R"]
ManualState = Literal["reset", "start", "stop"]


@dataclass
class Order:
    order_id: str
    station_id: str
    station_display_name: str
    side: OperatorSide
    creation_time: datetime
    urgent: bool
    items_dict: Dict[str, int]
    source: str = "mqtt_v1"
    end_time: Optional[datetime] = None
    end_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "station_id": self.station_id,
            "original_ws_id": self.station_id,
            "ws_id": self.station_id,
            "display_name": self.station_display_name,
            "side": self.side,
            "creation_time": self.creation_time.isoformat(),
            "urgent": self.urgent,
            "items_dict": self.items_dict,
            "source": self.source,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "end_reason": self.end_reason,
        }


@dataclass
class HelpRequest:
    request_id: str
    station_id: str
    side: OperatorSide
    idle: bool
    active: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.created_at:
            payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass
class TransferRequest:
    request_id: str
    station_id: str
    side: OperatorSide
    kind: Literal["from_previous", "for_next"]
    idle: bool = False
    active: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.created_at:
            payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass
class TimerState:
    state: Literal["stopped", "running", "paused"]
    total_seconds: int = 0
    remaining_seconds: int = 0
    paused_seconds: int = 0
    start_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "total_seconds": self.total_seconds,
            "remaining_seconds": self.remaining_seconds,
            "paused_seconds": self.paused_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }


@dataclass
class OperatorState:
    side: OperatorSide
    enabled: bool = True
    manual_state: ManualState = "reset"
    pending_orders: int = 0
    urgent_orders: int = 0
    help_request: Optional[HelpRequest] = None
    waiting_from_previous: Optional[TransferRequest] = None
    ready_for_next: Optional[TransferRequest] = None
    andon_code: str = "R"

    def to_dict(self) -> dict:
        return {
            "side": self.side,
            "enabled": self.enabled,
            "manual_state": self.manual_state,
            "pending_orders": self.pending_orders,
            "urgent_orders": self.urgent_orders,
            "help_request": self.help_request.to_dict() if self.help_request else None,
            "waiting_from_previous": (
                self.waiting_from_previous.to_dict() if self.waiting_from_previous else None
            ),
            "ready_for_next": self.ready_for_next.to_dict() if self.ready_for_next else None,
            "andon_code": self.andon_code,
        }


@dataclass
class Station:
    station_id: str
    display_name: str
    role: str = "workstation"
    enabled: bool = True
    capabilities: list[str] = field(default_factory=lambda: ["L", "R"])
    client_type: str = "legacy-mqtt"
    last_seen: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    sides: Dict[OperatorSide, OperatorState] = field(
        default_factory=lambda: {
            "L": OperatorState(side="L"),
            "R": OperatorState(side="R"),
        }
    )

    def to_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "display_name": self.display_name,
            "role": self.role,
            "enabled": self.enabled,
            "capabilities": self.capabilities,
            "client_type": self.client_type,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
            "sides": {side: state.to_dict() for side, state in self.sides.items()},
        }


@dataclass
class AndonState:
    station_id: str
    side: OperatorSide
    code: str
    active: bool
    idle: bool
    stopped: bool

    def to_dict(self) -> dict:
        return asdict(self)
