from flask import Blueprint, jsonify, request
from flask_socketio import disconnect

from auth.access import (
    get_current_access_context,
    register_socket_context,
    require_roles,
    unregister_socket_context,
)
from services.inventory_service import InventoryService
from services.timer_service import TimerService
from settings import settings
from socketio_instance import socketio


system_bp = Blueprint("system_bp", __name__)


@system_bp.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "broker_hostname": settings.broker_hostname,
            "broker_port": settings.broker_port,
            "timer_state": TimerService.get_instance().snapshot().to_dict(),
        }
    )


@system_bp.route("/state", methods=["GET"])
@require_roles("admin", "inventory", "tablet")
def state():
    return jsonify(InventoryService.get_instance().get_state_snapshot(get_current_access_context()))


@system_bp.route("/orders", methods=["GET"])
@require_roles("admin", "inventory")
def orders_state():
    return jsonify(InventoryService.get_instance().get_orders_state_snapshot())


@system_bp.route("/tablet-state", methods=["GET"])
@require_roles("tablet")
def tablet_state():
    access_context = get_current_access_context()
    if not access_context.station_id:
        return jsonify({"error": "tablet device is not bound to a station"}), 400
    return jsonify(
        InventoryService.get_instance().get_tablet_state_snapshot(access_context.station_id)
    )


@system_bp.route("/events", methods=["GET"])
@require_roles("admin")
def recent_events():
    limit = int(request.args.get("limit", 20))
    return jsonify(InventoryService.get_instance().get_recent_events(limit=limit))


@socketio.on("connect")
def handle_connect():
    access_context = get_current_access_context()
    if not access_context.authenticated:
        disconnect()
        return False

    register_socket_context(request.sid, access_context)
    inventory_service = InventoryService.get_instance()
    timer_service = TimerService.get_instance()
    inventory_service.emit_state_snapshot(sid=request.sid)
    socketio.emit("timer_state", timer_service.snapshot().to_dict(), room=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    unregister_socket_context(request.sid)
