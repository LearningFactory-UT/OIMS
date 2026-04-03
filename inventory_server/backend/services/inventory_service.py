from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from domain.andon import AndonInputs, derive_andon_state
from domain.entities import HelpRequest, OperatorState, Order, Station, TransferRequest
from models.db_models import (
    EventLogModel,
    OrderModel,
    StationModel,
    StationSideStateModel,
    SystemStateModel,
)
from services.andon_service import AndonService
from socketio_instance import socketio
from db_engine import SessionLocal
from settings import settings


class InventoryService:
    _instance = None

    @staticmethod
    def get_instance():
        if InventoryService._instance is None:
            InventoryService._instance = InventoryService()
        return InventoryService._instance

    def __init__(self):
        if InventoryService._instance is not None:
            raise Exception("Use InventoryService.get_instance() instead.")

        self.orders_dict: dict[str, Order] = {}
        self.past_orders_dict: dict[str, Order] = {}
        self.station_registry: dict[str, Station] = {}
        self.station_alias_index: dict[str, str] = {}
        self.side_state_store: dict[str, dict[str, dict[str, Any]]] = {}
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=50)
        self.assembly_type = "standard"

        self.andon_service = AndonService.get_instance()

        self._load_state_from_db()

    # ------------------------------------------------------------------
    # Bootstrapping and persistence
    # ------------------------------------------------------------------
    def _load_state_from_db(self):
        session = SessionLocal()
        try:
            system_state = session.get(SystemStateModel, 1)
            if system_state is None:
                system_state = SystemStateModel(id=1, assembly_type="standard")
                session.add(system_state)
                session.commit()
            self.assembly_type = system_state.assembly_type

            station_records = (
                session.query(StationModel).order_by(StationModel.ws_id.asc()).all()
            )
            side_records = session.query(StationSideStateModel).all()
            active_orders = (
                session.query(OrderModel)
                .filter(OrderModel.end_time.is_(None))
                .order_by(OrderModel.creation_time.asc())
                .all()
            )
            recent_events = (
                session.query(EventLogModel)
                .order_by(EventLogModel.created_at.desc())
                .limit(50)
                .all()
            )

            self.station_registry.clear()
            self.station_alias_index.clear()
            self.side_state_store.clear()
            self.orders_dict.clear()
            self.recent_events.clear()

            for record in station_records:
                self._load_station_record(record)

            for side_record in side_records:
                self._load_side_record(side_record)

            for order_record in active_orders:
                station = self.station_registry.get(order_record.original_ws_id)
                order = Order(
                    order_id=order_record.order_id,
                    station_id=order_record.original_ws_id,
                    station_display_name=(
                        order_record.display_name
                        or (station.display_name if station else None)
                        or order_record.ws_id
                    ),
                    side=order_record.side,
                    creation_time=order_record.creation_time,
                    urgent=order_record.urgent,
                    items_dict=order_record.items_json,
                    source=order_record.source,
                    end_time=order_record.end_time,
                    end_reason=order_record.end_reason,
                )
                self.orders_dict[order.order_id] = order

            for event_record in reversed(recent_events):
                self.recent_events.append(
                    {
                        "event_type": event_record.event_type,
                        "station_id": event_record.station_id,
                        "side": event_record.side,
                        "payload": event_record.payload_json,
                        "created_at": event_record.created_at.isoformat(),
                    }
                )
        finally:
            session.close()

        self._rebuild_derived_state()

    def _load_station_record(self, record: StationModel):
        station = Station(
            station_id=record.original_ws_id,
            display_name=record.ws_id,
            role=record.role,
            enabled=record.enabled,
            capabilities=record.capabilities_json or ["L", "R"],
            client_type=record.client_type,
            last_seen=record.last_seen,
            metadata=record.metadata_json or {},
            sides={
                "L": OperatorState(side="L", enabled=record.enabled),
                "R": OperatorState(side="R", enabled=record.enabled),
            },
        )
        self.station_registry[station.station_id] = station
        self.station_alias_index[station.display_name] = station.station_id
        self.side_state_store[station.station_id] = {
            "L": self._default_side_state(enabled=record.enabled),
            "R": self._default_side_state(enabled=record.enabled),
        }

    def _load_side_record(self, record: StationSideStateModel):
        station_id = record.original_ws_id
        self._ensure_station_placeholder(station_id)
        self.side_state_store[station_id][record.side] = {
            "enabled": record.enabled,
            "manual_state": record.manual_state,
            "help_id": record.help_id,
            "help_idle": record.help_idle,
            "help_created_at": record.help_created_at,
            "prev_ws_order_id": record.prev_ws_order_id,
            "prev_ws_order_idle": record.prev_ws_order_idle,
            "prev_ws_order_created_at": record.prev_ws_order_created_at,
            "ready_for_next_id": record.ready_for_next_id,
            "ready_for_next_created_at": record.ready_for_next_created_at,
            "andon_code": record.andon_code or "R",
            "updated_at": record.updated_at,
        }

    def _default_side_state(self, enabled: bool = True) -> dict[str, Any]:
        return {
            "enabled": enabled,
            "manual_state": "reset",
            "help_id": None,
            "help_idle": False,
            "help_created_at": None,
            "prev_ws_order_id": None,
            "prev_ws_order_idle": False,
            "prev_ws_order_created_at": None,
            "ready_for_next_id": None,
            "ready_for_next_created_at": None,
            "andon_code": "R",
            "updated_at": datetime.utcnow(),
        }

    def _ensure_station_placeholder(self, station_id: str):
        if station_id in self.station_registry:
            return
        station = Station(
            station_id=station_id,
            display_name=station_id,
            enabled=True,
            client_type="legacy-mqtt",
            metadata={},
        )
        self.station_registry[station_id] = station
        self.station_alias_index[station.display_name] = station.station_id
        self.side_state_store[station_id] = {
            "L": self._default_side_state(),
            "R": self._default_side_state(),
        }

    def _rebuild_derived_state(self):
        for station_id in list(self.station_registry.keys()):
            self._refresh_station_projection(station_id, persist=False, emit_lights=False)

    def _persist_system_state(self):
        session = SessionLocal()
        try:
            record = session.get(SystemStateModel, 1)
            if record is None:
                record = SystemStateModel(id=1)
                session.add(record)
            record.assembly_type = self.assembly_type
            record.updated_at = datetime.utcnow()
            session.commit()
        finally:
            session.close()

    def _persist_station_record(self, station_id: str):
        station = self.station_registry[station_id]
        session = SessionLocal()
        try:
            record = (
                session.query(StationModel)
                .filter_by(original_ws_id=station.station_id)
                .first()
            )
            if record is None:
                record = StationModel(original_ws_id=station.station_id)
                session.add(record)

            record.ws_id = station.display_name
            record.role = station.role
            record.enabled = station.enabled
            record.capabilities_json = station.capabilities
            record.client_type = station.client_type
            record.assignment_token = station.metadata.get("assignment_token")
            record.metadata_json = station.metadata
            record.last_seen = station.last_seen or datetime.utcnow()
            record.updated_at = datetime.utcnow()
            session.commit()
        finally:
            session.close()

    def _persist_side_state(self, station_id: str, side: str):
        station = self.station_registry[station_id]
        side_state = self.side_state_store[station_id][side]
        session = SessionLocal()
        try:
            record = (
                session.query(StationSideStateModel)
                .filter_by(original_ws_id=station_id, side=side)
                .first()
            )
            if record is None:
                record = StationSideStateModel(original_ws_id=station_id, side=side)
                session.add(record)

            record.enabled = station.enabled and side_state["enabled"]
            record.manual_state = side_state["manual_state"]
            record.help_id = side_state["help_id"]
            record.help_idle = side_state["help_idle"]
            record.help_created_at = side_state["help_created_at"]
            record.prev_ws_order_id = side_state["prev_ws_order_id"]
            record.prev_ws_order_idle = side_state["prev_ws_order_idle"]
            record.prev_ws_order_created_at = side_state["prev_ws_order_created_at"]
            record.ready_for_next_id = side_state["ready_for_next_id"]
            record.ready_for_next_created_at = side_state["ready_for_next_created_at"]
            record.andon_code = side_state["andon_code"]
            record.updated_at = datetime.utcnow()
            session.commit()
        finally:
            session.close()

    def _record_event(
        self,
        event_type: str,
        station_id: Optional[str] = None,
        side: Optional[str] = None,
        payload: Optional[dict] = None,
    ):
        payload = payload or {}
        event = {
            "event_type": event_type,
            "station_id": station_id,
            "side": side,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.recent_events.append(event)

        session = SessionLocal()
        try:
            session.add(
                EventLogModel(
                    event_type=event_type,
                    station_id=station_id,
                    side=side,
                    payload_json=payload,
                    created_at=datetime.utcnow(),
                )
            )
            session.commit()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Station registration and state
    # ------------------------------------------------------------------
    def resolve_station_id(
        self,
        ws_id: Optional[str] = None,
        original_ws_id: Optional[str] = None,
    ) -> str:
        if original_ws_id:
            original_ws_id = str(original_ws_id)
            if original_ws_id not in self.station_registry:
                self.register_station(original_ws_id, ws_id=ws_id or original_ws_id)
            return original_ws_id

        if ws_id:
            ws_id = str(ws_id)
            station_id = self.station_alias_index.get(ws_id)
            if station_id:
                return station_id
            if ws_id in self.station_registry:
                return ws_id
            self.register_station(ws_id, ws_id=ws_id)
            return ws_id

        raise ValueError("Unable to resolve a workstation identity.")

    def register_station(
        self,
        station_id: str,
        ws_id: Optional[str] = None,
        role: str = "workstation",
        client_type: str = "legacy-mqtt",
        capabilities: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
        emit: bool = True,
    ) -> dict:
        station_id = str(station_id)
        display_name = str(ws_id or station_id)

        alias_owner = self.station_alias_index.get(display_name)
        if alias_owner and alias_owner != station_id:
            raise ValueError(f"The workstation alias '{display_name}' is already in use.")

        station = self.station_registry.get(station_id)
        if station is None:
            station = Station(
                station_id=station_id,
                display_name=display_name,
                role=role,
                enabled=True,
                capabilities=capabilities or ["L", "R"],
                client_type=client_type,
                last_seen=datetime.utcnow(),
                metadata=metadata or {},
            )
            self.station_registry[station_id] = station
            self.side_state_store[station_id] = {
                "L": self._default_side_state(),
                "R": self._default_side_state(),
            }
        else:
            old_display_name = station.display_name
            if old_display_name != display_name:
                self.station_alias_index.pop(old_display_name, None)
            station.display_name = display_name
            station.role = role or station.role
            station.capabilities = capabilities or station.capabilities
            station.client_type = client_type or station.client_type
            station.last_seen = datetime.utcnow()
            if metadata:
                station.metadata.update(metadata)

        self.station_alias_index[display_name] = station_id
        self._persist_station_record(station_id)
        self._persist_side_state(station_id, "L")
        self._persist_side_state(station_id, "R")

        self._record_event(
            "station_registered",
            station_id=station_id,
            payload={"display_name": display_name, "client_type": client_type},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)

        if emit:
            self.emit_state_snapshot()

        return self.get_station_state(station_id)

    def heartbeat_station(self, station_id: str, client_type: Optional[str] = None) -> dict:
        station_id = self.resolve_station_id(original_ws_id=station_id)
        station = self.station_registry[station_id]
        station.last_seen = datetime.utcnow()
        if client_type:
            station.client_type = client_type
        self._persist_station_record(station_id)
        self._refresh_station_projection(station_id, persist=True, emit_lights=False)
        self.emit_state_snapshot()
        return self.get_station_state(station_id)

    def set_ws_id(self, original_ws_id: str, ws_id: str) -> dict:
        original_ws_id = str(original_ws_id)
        ws_id = str(ws_id).strip() or original_ws_id

        alias_owner = self.station_alias_index.get(ws_id)
        if alias_owner and alias_owner != original_ws_id:
            current_station = self.station_registry.get(original_ws_id)
            return {
                "original_ws_id": original_ws_id,
                "ws_id": current_station.display_name if current_station else False,
            }

        self.register_station(
            original_ws_id,
            ws_id=ws_id,
            client_type="legacy-mqtt",
            emit=False,
        )

        session = SessionLocal()
        try:
            (
                session.query(OrderModel)
                .filter(
                    OrderModel.original_ws_id == original_ws_id,
                    OrderModel.end_time.is_(None),
                )
                .update({"display_name": ws_id}, synchronize_session=False)
            )
            session.commit()
        finally:
            session.close()

        for order in self.orders_dict.values():
            if order.station_id == original_ws_id:
                order.station_display_name = ws_id

        self._record_event(
            "station_alias_updated",
            station_id=original_ws_id,
            payload={"display_name": ws_id},
        )
        self.emit_state_snapshot()
        return {"original_ws_id": original_ws_id, "ws_id": ws_id}

    def set_ws_info(self, info_dict: dict):
        station_id = self.resolve_station_id(
            ws_id=info_dict.get("ws_id"),
            original_ws_id=info_dict.get("original_ws_id"),
        )
        display_name = info_dict.get("ws_id") or station_id
        self.register_station(
            station_id,
            ws_id=display_name,
            client_type="legacy-mqtt",
            metadata={"last_snapshot_source": "mqtt_v1"},
            emit=False,
        )

        for order_payload in (info_dict.get("pending_orders") or {}).values():
            normalized = {
                "attributes": {
                    "order_id": order_payload["order_id"],
                    "ws_id": display_name,
                    "original_ws_id": station_id,
                    "operator_side": order_payload["side"],
                    "urgent": order_payload.get("urgent", False),
                },
                "items": order_payload.get("items_dict", {}),
            }
            self.add_order(normalized, source="legacy_snapshot", emit=False)

        pending_help = info_dict.get("pending_help") or {}
        for side in ["L", "R"]:
            side_payload = pending_help.get(side)
            if side_payload:
                self.update_help(
                    {
                        "help_id": side_payload["help_id"],
                        "original_ws_id": station_id,
                        "side": side,
                        "help": True,
                        "idle": side_payload.get("idle", False),
                    },
                    source="legacy_snapshot",
                    emit=False,
                )

        pending_previous = info_dict.get("pending_order_from_previous_ws") or {}
        for side in ["L", "R"]:
            side_payload = pending_previous.get(side)
            if side_payload:
                self.update_order_from_prev_ws(
                    {
                        "prev_ws_order_id": side_payload["prev_ws_order_id"],
                        "original_ws_id": station_id,
                        "side": side,
                        "pending": True,
                        "idle": side_payload.get("idle", False),
                    },
                    source="legacy_snapshot",
                    emit=False,
                )

        self._record_event(
            "station_snapshot_received",
            station_id=station_id,
            payload={"pending_orders": len(info_dict.get("pending_orders") or {})},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)
        self.emit_state_snapshot()
        return self.get_station_state(station_id)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def _generate_order_id(self, station_id: str) -> str:
        timestamp = datetime.utcnow().strftime("%H%M%S%f")
        return f"WS{station_id}_{timestamp}"

    def _normalize_order_payload(self, order_data: dict, source: str) -> dict:
        if "attributes" in order_data:
            attributes = order_data["attributes"]
            items = order_data.get("items", {})
            station_id = self.resolve_station_id(
                ws_id=attributes.get("display_name") or attributes.get("ws_id"),
                original_ws_id=attributes.get("original_ws_id"),
            )
            station = self.station_registry[station_id]
            order_id = attributes.get("order_id") or self._generate_order_id(station_id)
            return {
                "order_id": order_id,
                "station_id": station_id,
                "display_name": station.display_name,
                "side": attributes["operator_side"],
                "urgent": bool(attributes.get("urgent", False)),
                "items": items,
                "source": source,
            }

        station_id = self.resolve_station_id(
            ws_id=order_data.get("ws_id") or order_data.get("display_name"),
            original_ws_id=order_data.get("station_id") or order_data.get("original_ws_id"),
        )
        station = self.station_registry[station_id]
        return {
            "order_id": order_data.get("order_id") or self._generate_order_id(station_id),
            "station_id": station_id,
            "display_name": station.display_name,
            "side": order_data["side"],
            "urgent": bool(order_data.get("urgent", False)),
            "items": order_data.get("items") or order_data.get("items_dict") or {},
            "source": source,
        }

    def add_order(self, order_data: dict, source: str = "mqtt_v1", emit: bool = True) -> dict:
        normalized = self._normalize_order_payload(order_data, source)
        if not normalized["items"]:
            return {}

        order_id = normalized["order_id"]
        if order_id in self.orders_dict:
            return self.orders_dict[order_id].to_dict()

        station_id = normalized["station_id"]
        self.register_station(station_id, ws_id=normalized["display_name"], emit=False)

        new_order = Order(
            order_id=order_id,
            station_id=station_id,
            station_display_name=normalized["display_name"],
            side=normalized["side"],
            creation_time=datetime.utcnow(),
            urgent=normalized["urgent"],
            items_dict=normalized["items"],
            source=normalized["source"],
        )
        self.orders_dict[order_id] = new_order

        session = SessionLocal()
        try:
            existing = session.query(OrderModel).filter_by(order_id=order_id).first()
            if existing is None:
                session.add(
                    OrderModel(
                        order_id=new_order.order_id,
                        original_ws_id=new_order.station_id,
                        ws_id=new_order.station_id,
                        display_name=new_order.station_display_name,
                        side=new_order.side,
                        creation_time=new_order.creation_time,
                        urgent=new_order.urgent,
                        items_json=new_order.items_dict,
                        source=new_order.source,
                    )
                )
            else:
                existing.original_ws_id = new_order.station_id
                existing.ws_id = new_order.station_id
                existing.display_name = new_order.station_display_name
                existing.side = new_order.side
                existing.urgent = new_order.urgent
                existing.items_json = new_order.items_dict
                existing.source = new_order.source
                existing.end_time = None
                existing.end_reason = None
            session.commit()
        finally:
            session.close()

        self._record_event(
            "order_created",
            station_id=station_id,
            side=new_order.side,
            payload={"order_id": order_id, "urgent": new_order.urgent},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)

        socketio.emit("orders_updated", {"orders": self.get_active_orders()})
        if emit:
            self.emit_state_snapshot()
        return new_order.to_dict()

    def remove_order(self, order_data: dict | str, reason: str = "manual", emit: bool = True) -> dict:
        order_id = order_data if isinstance(order_data, str) else order_data["order_id"]

        order = self.orders_dict.pop(order_id, None)
        if order is None:
            return {}

        order.end_time = datetime.utcnow()
        order.end_reason = reason
        self.past_orders_dict[order_id] = order

        session = SessionLocal()
        try:
            record = session.query(OrderModel).filter_by(order_id=order_id).first()
            if record is not None:
                record.end_time = order.end_time
                record.end_reason = reason
            session.commit()
        finally:
            session.close()

        self._record_event(
            "order_removed",
            station_id=order.station_id,
            side=order.side,
            payload={"order_id": order_id, "reason": reason},
        )
        self._refresh_station_projection(order.station_id, persist=True, emit_lights=True)

        socketio.emit("order_removed", {"order_id": order_id, "reason": reason})
        socketio.emit("orders_updated", {"orders": self.get_active_orders()})
        if emit:
            self.emit_state_snapshot()
        return order.to_dict()

    def update_order(self, update_order_dict: dict, emit: bool = True) -> dict:
        order_id = update_order_dict["order_id"]
        order = self.orders_dict.get(order_id)
        if order is None:
            return {}

        urgent = bool(update_order_dict.get("urgent", order.urgent))
        order.urgent = urgent

        session = SessionLocal()
        try:
            record = session.query(OrderModel).filter_by(order_id=order_id).first()
            if record is not None:
                record.urgent = urgent
            session.commit()
        finally:
            session.close()

        self._record_event(
            "order_updated",
            station_id=order.station_id,
            side=order.side,
            payload={"order_id": order_id, "urgent": urgent},
        )
        self._refresh_station_projection(order.station_id, persist=True, emit_lights=True)

        socketio.emit("order_updated", {"order_id": order_id, "urgent": urgent})
        socketio.emit("orders_updated", {"orders": self.get_active_orders()})
        if emit:
            self.emit_state_snapshot()
        return order.to_dict()

    def clear_all_orders(self, reason: str = "timer"):
        for order_id in list(self.orders_dict.keys()):
            self.remove_order(order_id, reason=reason, emit=False)
        self.sync_all_andon_states(emit=False)
        self.emit_state_snapshot()

    def get_active_orders(self) -> list[dict]:
        return [
            order.to_dict()
            for order in sorted(
                self.orders_dict.values(), key=lambda current_order: current_order.creation_time
            )
        ]

    def get_order_station_id(self, order_id: str) -> Optional[str]:
        order = self.orders_dict.get(order_id)
        if order is None:
            return None
        return order.station_id

    # ------------------------------------------------------------------
    # Operator-side state
    # ------------------------------------------------------------------
    def update_help(self, help_dict: dict, source: str = "mqtt_v1", emit: bool = True) -> dict:
        station_id = self.resolve_station_id(
            ws_id=help_dict.get("ws_id"),
            original_ws_id=help_dict.get("original_ws_id"),
        )
        side = help_dict["side"]
        self.register_station(station_id, emit=False)

        side_state = self.side_state_store[station_id][side]
        if help_dict["help"]:
            side_state["help_id"] = help_dict["help_id"]
            side_state["help_idle"] = bool(help_dict.get("idle", False))
            side_state["help_created_at"] = datetime.utcnow()
            event_name = "help_requested"
        else:
            side_state["help_id"] = None
            side_state["help_idle"] = False
            side_state["help_created_at"] = None
            event_name = "help_cleared"

        self._persist_side_state(station_id, side)
        self._record_event(
            event_name,
            station_id=station_id,
            side=side,
            payload={"source": source, "idle": bool(help_dict.get("idle", False))},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)
        if emit:
            self.emit_state_snapshot()
        return self.get_station_state(station_id)

    def update_order_from_prev_ws(
        self,
        prev_ws_order_dict: dict,
        source: str = "mqtt_v1",
        emit: bool = True,
    ) -> dict:
        station_id = self.resolve_station_id(
            ws_id=prev_ws_order_dict.get("ws_id"),
            original_ws_id=prev_ws_order_dict.get("original_ws_id"),
        )
        side = prev_ws_order_dict["side"]
        self.register_station(station_id, emit=False)

        side_state = self.side_state_store[station_id][side]
        if prev_ws_order_dict["pending"]:
            side_state["prev_ws_order_id"] = prev_ws_order_dict["prev_ws_order_id"]
            side_state["prev_ws_order_idle"] = bool(prev_ws_order_dict.get("idle", False))
            side_state["prev_ws_order_created_at"] = datetime.utcnow()
            event_name = "waiting_from_previous_requested"
        else:
            side_state["prev_ws_order_id"] = None
            side_state["prev_ws_order_idle"] = False
            side_state["prev_ws_order_created_at"] = None
            event_name = "waiting_from_previous_cleared"

        self._persist_side_state(station_id, side)
        self._record_event(
            event_name,
            station_id=station_id,
            side=side,
            payload={"source": source, "idle": bool(prev_ws_order_dict.get("idle", False))},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)
        if emit:
            self.emit_state_snapshot()
        return self.get_station_state(station_id)

    def update_order_for_next_ws(
        self,
        ready_for_next_dict: dict,
        source: str = "mqtt_v1",
        emit: bool = True,
    ) -> dict:
        station_id = self.resolve_station_id(
            ws_id=ready_for_next_dict.get("ws_id"),
            original_ws_id=ready_for_next_dict.get("original_ws_id"),
        )
        side = ready_for_next_dict["side"]
        self.register_station(station_id, emit=False)

        side_state = self.side_state_store[station_id][side]
        if ready_for_next_dict["ready"]:
            side_state["ready_for_next_id"] = ready_for_next_dict["ready_for_next_id"]
            side_state["ready_for_next_created_at"] = datetime.utcnow()
            event_name = "ready_for_next_requested"
        else:
            side_state["ready_for_next_id"] = None
            side_state["ready_for_next_created_at"] = None
            event_name = "ready_for_next_cleared"

        self._persist_side_state(station_id, side)
        self._record_event(
            event_name,
            station_id=station_id,
            side=side,
            payload={"source": source},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)
        if emit:
            self.emit_state_snapshot()
        return self.get_station_state(station_id)

    def manual_start_stop(self, ws_id: str, side: str, command: str, emit: bool = True) -> dict:
        station_id = self.resolve_station_id(original_ws_id=ws_id, ws_id=ws_id)
        self.register_station(station_id, emit=False)

        side_state = self.side_state_store[station_id][side]
        if command not in {"start", "stop", "reset"}:
            raise ValueError(f"Unsupported manual command '{command}'.")

        side_state["manual_state"] = command
        self._persist_side_state(station_id, side)
        self._record_event(
            "manual_state_changed",
            station_id=station_id,
            side=side,
            payload={"command": command},
        )
        self._refresh_station_projection(station_id, persist=True, emit_lights=True)
        if emit:
            self.emit_state_snapshot()
        return self.get_station_state(station_id)

    def disable_workstation(self, ws_ids: list[str], emit: bool = True) -> list[dict]:
        updated = []
        for ws_id in ws_ids:
            station_id = self.resolve_station_id(ws_id=ws_id, original_ws_id=ws_id)
            station = self.station_registry[station_id]
            station.enabled = False
            for side in ["L", "R"]:
                self.side_state_store[station_id][side]["enabled"] = False
                self._persist_side_state(station_id, side)
            self._persist_station_record(station_id)
            self._record_event("workstation_disabled", station_id=station_id)
            self._refresh_station_projection(station_id, persist=True, emit_lights=True)
            updated.append(self.get_station_state(station_id))

        if emit:
            self.emit_state_snapshot()
        return updated

    def enable_workstation(self, ws_ids: list[str], emit: bool = True) -> list[dict]:
        updated = []
        for ws_id in ws_ids:
            station_id = self.resolve_station_id(ws_id=ws_id, original_ws_id=ws_id)
            station = self.station_registry[station_id]
            station.enabled = True
            for side in ["L", "R"]:
                self.side_state_store[station_id][side]["enabled"] = True
                self._persist_side_state(station_id, side)
            self._persist_station_record(station_id)
            self._record_event("workstation_enabled", station_id=station_id)
            self._refresh_station_projection(station_id, persist=True, emit_lights=True)
            updated.append(self.get_station_state(station_id))

        if emit:
            self.emit_state_snapshot()
        return updated

    # ------------------------------------------------------------------
    # Assembly type and projections
    # ------------------------------------------------------------------
    def set_assembly_type(self, atype: str):
        if atype not in {"standard", "simplified"}:
            raise ValueError("Unsupported assembly type.")
        self.assembly_type = atype
        self._persist_system_state()
        self._record_event("assembly_type_changed", payload={"assembly_type": atype})
        self.emit_state_snapshot()

    def get_assembly_type(self) -> str:
        return self.assembly_type

    def _get_station_health(self, station: Station) -> str:
        if station.last_seen is None:
            return "unknown"
        if datetime.utcnow() - station.last_seen <= timedelta(
            seconds=settings.station_heartbeat_timeout_seconds
        ):
            return "online"
        return "offline"

    def _build_operator_state(self, station_id: str, side: str) -> OperatorState:
        station = self.station_registry[station_id]
        side_state = self.side_state_store[station_id][side]
        pending_orders = [
            order
            for order in self.orders_dict.values()
            if order.station_id == station_id and order.side == side
        ]
        urgent_orders = [order for order in pending_orders if order.urgent]

        help_request = None
        if side_state["help_id"]:
            help_request = HelpRequest(
                request_id=side_state["help_id"],
                station_id=station_id,
                side=side,
                idle=side_state["help_idle"],
                created_at=side_state["help_created_at"],
            )

        waiting_from_previous = None
        if side_state["prev_ws_order_id"]:
            waiting_from_previous = TransferRequest(
                request_id=side_state["prev_ws_order_id"],
                station_id=station_id,
                side=side,
                kind="from_previous",
                idle=side_state["prev_ws_order_idle"],
                created_at=side_state["prev_ws_order_created_at"],
            )

        ready_for_next = None
        if side_state["ready_for_next_id"]:
            ready_for_next = TransferRequest(
                request_id=side_state["ready_for_next_id"],
                station_id=station_id,
                side=side,
                kind="for_next",
                idle=False,
                created_at=side_state["ready_for_next_created_at"],
            )

        return OperatorState(
            side=side,
            enabled=station.enabled and side_state["enabled"],
            manual_state=side_state["manual_state"],
            pending_orders=len(pending_orders),
            urgent_orders=len(urgent_orders),
            help_request=help_request,
            waiting_from_previous=waiting_from_previous,
            ready_for_next=ready_for_next,
            andon_code=side_state["andon_code"],
        )

    def _is_timer_running(self) -> bool:
        from services.timer_service import TimerService

        timer_service = TimerService._instance
        if timer_service is None:
            return False
        return timer_service.is_timer_running()

    def _refresh_station_projection(
        self,
        station_id: str,
        persist: bool = True,
        emit_lights: bool = True,
    ):
        if station_id not in self.station_registry:
            return

        station = self.station_registry[station_id]
        station.sides = {
            "L": self._build_operator_state(station_id, "L"),
            "R": self._build_operator_state(station_id, "R"),
        }

        timer_running = self._is_timer_running()
        for side in ["L", "R"]:
            operator_state = station.sides[side]
            inputs = AndonInputs(
                station_id=station_id,
                side=side,
                timer_running=timer_running,
                enabled=operator_state.enabled,
                manual_state=operator_state.manual_state,
                pending_orders=operator_state.pending_orders,
                urgent_orders=operator_state.urgent_orders,
                help_requested=operator_state.help_request is not None,
                help_idle=operator_state.help_request.idle if operator_state.help_request else False,
                waiting_from_previous=operator_state.waiting_from_previous is not None,
                waiting_from_previous_idle=(
                    operator_state.waiting_from_previous.idle
                    if operator_state.waiting_from_previous
                    else False
                ),
                ready_for_next=operator_state.ready_for_next is not None,
            )
            andon_state = derive_andon_state(inputs)
            self.side_state_store[station_id][side]["andon_code"] = andon_state.code
            operator_state.andon_code = andon_state.code
            if persist:
                self._persist_side_state(station_id, side)
            if emit_lights:
                self.andon_service.update_lights(station_id, side, andon_state.code)

    def sync_all_andon_states(self, emit: bool = True):
        for station_id in list(self.station_registry.keys()):
            self._refresh_station_projection(station_id, persist=True, emit_lights=True)
        if emit:
            self.emit_state_snapshot()

    def get_station_state(self, station_id: str) -> dict:
        station_id = self.resolve_station_id(original_ws_id=station_id)
        station = self.station_registry[station_id]
        self._refresh_station_projection(station_id, persist=False, emit_lights=False)
        station_payload = station.to_dict()
        station_payload["health"] = self._get_station_health(station)
        station_payload["active_orders"] = [
            order.to_dict()
            for order in self.orders_dict.values()
            if order.station_id == station_id
        ]
        return station_payload

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        return list(self.recent_events)[-limit:][::-1]

    def _build_full_state_snapshot(self) -> dict:
        from services.timer_service import TimerService

        timer_service = TimerService.get_instance()
        stations = [
            self.get_station_state(station_id)
            for station_id in sorted(
                self.station_registry.keys(),
                key=lambda current_id: self.station_registry[current_id].display_name,
            )
        ]
        orders = self.get_active_orders()
        return {
            "assembly_type": self.assembly_type,
            "timer": timer_service.snapshot().to_dict(),
            "stations": stations,
            "orders": orders,
            "summary": {
                "active_orders": len(orders),
                "urgent_orders": len([order for order in orders if order["urgent"]]),
                "stations": len(stations),
            },
            "recent_events": self.get_recent_events(),
        }

    def _filter_state_snapshot(self, snapshot: dict, access_context=None) -> dict:
        if access_context is None or not access_context.authenticated:
            return {
                "assembly_type": snapshot["assembly_type"],
                "timer": snapshot["timer"],
                "stations": [],
                "orders": [],
                "summary": {
                    "active_orders": 0,
                    "urgent_orders": 0,
                    "stations": 0,
                },
                "recent_events": [],
                "devices": [],
            }

        if access_context.is_admin:
            from services.auth_service import AuthService

            admin_snapshot = dict(snapshot)
            admin_snapshot["devices"] = AuthService.get_instance().list_devices()
            return admin_snapshot

        if access_context.role == "inventory":
            orders = snapshot["orders"]
            return {
                "assembly_type": snapshot["assembly_type"],
                "timer": snapshot["timer"],
                "stations": [],
                "orders": orders,
                "summary": {
                    "active_orders": len(orders),
                    "urgent_orders": len([order for order in orders if order["urgent"]]),
                    "stations": 0,
                },
                "recent_events": [],
                "devices": [],
            }

        if access_context.role == "tablet":
            station_id = str(access_context.station_id or "")
            stations = [
                station for station in snapshot["stations"] if station["station_id"] == station_id
            ]
            orders = [
                order for order in snapshot["orders"] if order["station_id"] == station_id
            ]
            return {
                "assembly_type": snapshot["assembly_type"],
                "timer": snapshot["timer"],
                "stations": stations,
                "orders": orders,
                "summary": {
                    "active_orders": len(orders),
                    "urgent_orders": len([order for order in orders if order["urgent"]]),
                    "stations": len(stations),
                },
                "recent_events": [],
                "devices": [],
            }

        return {
            "assembly_type": snapshot["assembly_type"],
            "timer": snapshot["timer"],
            "stations": [],
            "orders": [],
            "summary": {
                "active_orders": 0,
                "urgent_orders": 0,
                "stations": 0,
            },
            "recent_events": [],
            "devices": [],
        }

    def get_state_snapshot(self, access_context=None) -> dict:
        return self._filter_state_snapshot(self._build_full_state_snapshot(), access_context)

    def emit_state_snapshot(self, sid: Optional[str] = None):
        from auth.access import get_current_access_context, get_socket_context, iter_socket_contexts

        if sid is not None:
            access_context = get_socket_context(sid) or get_current_access_context()
            snapshot = self.get_state_snapshot(access_context)
            socketio.emit("state_snapshot", snapshot, room=sid)
            return snapshot

        full_snapshot = self._build_full_state_snapshot()
        socket_contexts = iter_socket_contexts()
        if not socket_contexts:
            return full_snapshot

        for current_sid, access_context in socket_contexts:
            filtered_snapshot = self._filter_state_snapshot(full_snapshot, access_context)
            socketio.emit("state_snapshot", filtered_snapshot, room=current_sid)
        return full_snapshot
