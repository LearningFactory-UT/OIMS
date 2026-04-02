from flask import Blueprint, jsonify, request

from mqtt.mqtt_service import MQTTService
from services.timer_service import TimerService


timer_bp = Blueprint("timer_bp", __name__)


@timer_bp.route("/", methods=["GET"])
def get_timer_state():
    return jsonify(TimerService.get_instance().snapshot().to_dict())


@timer_bp.route("/", methods=["POST"])
def control_timer():
    data = request.get_json() or {}
    command = data.get("command")
    seconds = int(data.get("seconds", 0))

    timer_service = TimerService.get_instance()
    mqtt_service = MQTTService.get_instance()

    timer_service.apply_command(command, seconds=seconds, source="api")
    mqtt_service.publish_timer_command(
        command,
        seconds=seconds,
        initiator="inventory_server_api",
        handled_by_server=True,
    )

    return jsonify(timer_service.snapshot().to_dict()), 200


@timer_bp.route("/remaining", methods=["GET"])
def get_remaining():
    remaining = TimerService.get_instance().get_remaining_seconds()
    return jsonify({"remaining_seconds": remaining})
