from flask import Blueprint, jsonify, request
import logging

from auth.access import require_roles
from mqtt.mqtt_service import MQTTService
from services.timer_service import TimerService


timer_bp = Blueprint("timer_bp", __name__)
logger = logging.getLogger(__name__)


@timer_bp.route("/", methods=["GET"])
@require_roles("admin", "inventory", "tablet")
def get_timer_state():
    return jsonify(TimerService.get_instance().snapshot().to_dict())


@timer_bp.route("/", methods=["POST"])
@require_roles("admin")
def control_timer():
    data = request.get_json() or {}
    command = data.get("command")
    seconds = int(data.get("seconds", 0))

    timer_service = TimerService.get_instance()

    timer_service.apply_command(command, seconds=seconds, source="api")
    try:
        mqtt_service = MQTTService.get_instance()
        mqtt_service.publish_timer_command(
            command,
            seconds=seconds,
            initiator="inventory_server_api",
            handled_by_server=True,
        )
    except Exception:
        logger.exception("Failed to publish compatibility timer command.")

    return jsonify(timer_service.snapshot().to_dict()), 200


@timer_bp.route("/remaining", methods=["GET"])
@require_roles("admin", "inventory", "tablet")
def get_remaining():
    remaining = TimerService.get_instance().get_remaining_seconds()
    return jsonify({"remaining_seconds": remaining})
