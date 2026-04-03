from flask import Blueprint, jsonify, request

from auth.access import require_roles
from mqtt.mqtt_service import MQTTService
from services.inventory_service import InventoryService


manager_bp = Blueprint("manager_bp", __name__)


@manager_bp.route("/assembly", methods=["POST"])
@require_roles("admin")
def set_assembly_type():
    data = request.get_json() or {}
    atype = data.get("assembly_type", "standard")

    inventory_service = InventoryService.get_instance()
    mqtt_service = MQTTService.get_instance()

    inventory_service.set_assembly_type(atype)
    mqtt_service.publish_assembly_type(atype, handled_by_server=True)

    return jsonify({"assembly_type": atype}), 200


@manager_bp.route("/disable", methods=["POST"])
@require_roles("admin")
def disable_workstation():
    data = request.get_json() or {}
    ws_ids = data.get("ws_ids") or data.get("original_ws_ids") or []

    inventory_service = InventoryService.get_instance()
    mqtt_service = MQTTService.get_instance()

    updated = inventory_service.disable_workstation(ws_ids)
    mqtt_service.publish_workstation_toggle(
        "disable",
        ws_ids,
        handled_by_server=True,
    )

    return jsonify({"stations": updated}), 200


@manager_bp.route("/enable", methods=["POST"])
@require_roles("admin")
def enable_workstation():
    data = request.get_json() or {}
    ws_ids = data.get("ws_ids") or data.get("original_ws_ids") or []

    inventory_service = InventoryService.get_instance()
    mqtt_service = MQTTService.get_instance()

    updated = inventory_service.enable_workstation(ws_ids)
    mqtt_service.publish_workstation_toggle(
        "enable",
        ws_ids,
        handled_by_server=True,
    )

    return jsonify({"stations": updated}), 200
