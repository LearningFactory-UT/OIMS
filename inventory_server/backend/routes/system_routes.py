from flask import Blueprint, jsonify, request

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
def state():
    return jsonify(InventoryService.get_instance().get_state_snapshot())


@system_bp.route("/events", methods=["GET"])
def recent_events():
    limit = int(request.args.get("limit", 20))
    return jsonify(InventoryService.get_instance().get_recent_events(limit=limit))


@socketio.on("connect")
def handle_connect():
    inventory_service = InventoryService.get_instance()
    timer_service = TimerService.get_instance()
    inventory_service.emit_state_snapshot(sid=request.sid)
    socketio.emit("timer_state", timer_service.snapshot().to_dict(), room=request.sid)

