from flask import Blueprint, jsonify, request

from contracts.legacy_order import build_legacy_order_payload
from mqtt.mqtt_service import MQTTService
from services.inventory_service import InventoryService


station_bp = Blueprint("station_bp", __name__)


def _publish_legacy_order(order: dict):
    if not order:
        return

    MQTTService.get_instance().publish_legacy_order(build_legacy_order_payload(order))


@station_bp.route("/", methods=["GET"])
def list_stations():
    inventory_service = InventoryService.get_instance()
    stations = inventory_service.get_state_snapshot()["stations"]
    return jsonify(stations)


@station_bp.route("/register", methods=["POST"])
def register_station():
    data = request.get_json() or {}
    station_id = data.get("station_id") or data.get("original_ws_id") or data.get("ws_id")
    if not station_id:
        return jsonify({"error": "station_id is required"}), 400

    inventory_service = InventoryService.get_instance()
    station = inventory_service.register_station(
        station_id=station_id,
        ws_id=data.get("display_name") or data.get("ws_id") or station_id,
        role=data.get("role", "workstation"),
        client_type=data.get("client_type", "web-tablet"),
        capabilities=data.get("capabilities"),
        metadata={
            "assignment_token": data.get("assignment_token"),
            "provisioned_by": data.get("provisioned_by", "api"),
        },
    )
    return jsonify(station), 200


@station_bp.route("/<station_id>", methods=["GET"])
def get_station(station_id):
    inventory_service = InventoryService.get_instance()
    return jsonify(inventory_service.get_station_state(station_id))


@station_bp.route("/<station_id>/heartbeat", methods=["POST"])
def heartbeat(station_id):
    data = request.get_json() or {}
    inventory_service = InventoryService.get_instance()
    station = inventory_service.heartbeat_station(
        station_id,
        client_type=data.get("client_type"),
    )
    return jsonify(station), 200


@station_bp.route("/<station_id>/orders", methods=["POST"])
def create_station_order(station_id):
    data = request.get_json() or {}
    payload = {
        "station_id": station_id,
        "side": data["side"],
        "urgent": bool(data.get("urgent", False)),
        "items": data.get("items", {}),
        "order_id": data.get("order_id"),
    }
    order = InventoryService.get_instance().add_order(payload, source="web_workstation")
    _publish_legacy_order(order)
    return jsonify(order), 201


@station_bp.route("/<station_id>/help", methods=["POST"])
def update_help(station_id):
    data = request.get_json() or {}
    payload = {
        "original_ws_id": station_id,
        "side": data["side"],
        "help": bool(data.get("active", False)),
        "idle": bool(data.get("idle", False)),
        "help_id": data.get("help_id") or f"{station_id}_{data['side']}_help",
    }
    state = InventoryService.get_instance().update_help(payload, source="web_workstation")
    return jsonify(state), 200


@station_bp.route("/<station_id>/waiting-previous", methods=["POST"])
def update_waiting_previous(station_id):
    data = request.get_json() or {}
    payload = {
        "original_ws_id": station_id,
        "side": data["side"],
        "pending": bool(data.get("active", False)),
        "idle": bool(data.get("idle", False)),
        "prev_ws_order_id": data.get("request_id")
        or f"{station_id}_{data['side']}_from_previous",
    }
    state = InventoryService.get_instance().update_order_from_prev_ws(
        payload,
        source="web_workstation",
    )
    return jsonify(state), 200


@station_bp.route("/<station_id>/ready-next", methods=["POST"])
def update_ready_next(station_id):
    data = request.get_json() or {}
    payload = {
        "original_ws_id": station_id,
        "side": data["side"],
        "ready": bool(data.get("active", False)),
        "ready_for_next_id": data.get("request_id")
        or f"{station_id}_{data['side']}_ready_next",
    }
    state = InventoryService.get_instance().update_order_for_next_ws(
        payload,
        source="web_workstation",
    )
    return jsonify(state), 200


@station_bp.route("/<station_id>/manual", methods=["POST"])
def update_manual(station_id):
    data = request.get_json() or {}
    state = InventoryService.get_instance().manual_start_stop(
        station_id,
        data["side"],
        data["command"],
    )
    return jsonify(state), 200
