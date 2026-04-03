from flask import Blueprint, jsonify, request

from auth.access import forbid_unless_order_owner, get_current_access_context, require_roles
from contracts.legacy_order import build_legacy_order_payload
from mqtt.mqtt_service import MQTTService
from services.inventory_service import InventoryService


order_bp = Blueprint("order_bp", __name__)


def _publish_legacy_order(order: dict):
    if not order:
        return

    MQTTService.get_instance().publish_legacy_order(build_legacy_order_payload(order))


@order_bp.route("/", methods=["GET"])
@require_roles("admin", "inventory")
def get_all_orders():
    return jsonify(InventoryService.get_instance().get_active_orders())


@order_bp.route("/", methods=["POST"])
@require_roles("admin")
def create_order():
    payload = request.get_json() or {}
    order = InventoryService.get_instance().add_order(payload, source="api")
    _publish_legacy_order(order)
    return jsonify(order), 201


@order_bp.route("/<order_id>", methods=["PATCH"])
@require_roles("admin", "tablet")
def update_order(order_id):
    if get_current_access_context().role == "tablet":
        station_id = InventoryService.get_instance().get_order_station_id(order_id)
        try:
            forbid_unless_order_owner(station_id or "")
        except PermissionError as error:
            return jsonify({"error": str(error)}), 403
    payload = request.get_json() or {}
    payload["order_id"] = order_id
    order = InventoryService.get_instance().update_order(payload)
    return jsonify(order), 200


@order_bp.route("/<order_id>/deliver", methods=["POST"])
@require_roles("admin", "tablet")
def deliver_order(order_id):
    if get_current_access_context().role == "tablet":
        station_id = InventoryService.get_instance().get_order_station_id(order_id)
        try:
            forbid_unless_order_owner(station_id or "")
        except PermissionError as error:
            return jsonify({"error": str(error)}), 403
    order = InventoryService.get_instance().remove_order(order_id, reason="delivered")
    return jsonify(order), 200


@order_bp.route("/<order_id>", methods=["DELETE"])
@require_roles("admin", "tablet")
def delete_order(order_id):
    if get_current_access_context().role == "tablet":
        station_id = InventoryService.get_instance().get_order_station_id(order_id)
        try:
            forbid_unless_order_owner(station_id or "")
        except PermissionError as error:
            return jsonify({"error": str(error)}), 403
    order = InventoryService.get_instance().remove_order(order_id, reason="deleted")
    return jsonify(order), 200
