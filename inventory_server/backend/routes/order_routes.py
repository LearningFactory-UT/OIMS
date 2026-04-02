from flask import Blueprint, jsonify, request

from contracts.legacy_order import build_legacy_order_payload
from mqtt.mqtt_service import MQTTService
from services.inventory_service import InventoryService


order_bp = Blueprint("order_bp", __name__)


def _publish_legacy_order(order: dict):
    if not order:
        return

    MQTTService.get_instance().publish_legacy_order(build_legacy_order_payload(order))


@order_bp.route("/", methods=["GET"])
def get_all_orders():
    return jsonify(InventoryService.get_instance().get_active_orders())


@order_bp.route("/", methods=["POST"])
def create_order():
    payload = request.get_json() or {}
    order = InventoryService.get_instance().add_order(payload, source="api")
    _publish_legacy_order(order)
    return jsonify(order), 201


@order_bp.route("/<order_id>", methods=["PATCH"])
def update_order(order_id):
    payload = request.get_json() or {}
    payload["order_id"] = order_id
    order = InventoryService.get_instance().update_order(payload)
    return jsonify(order), 200


@order_bp.route("/<order_id>/deliver", methods=["POST"])
def deliver_order(order_id):
    order = InventoryService.get_instance().remove_order(order_id, reason="delivered")
    return jsonify(order), 200


@order_bp.route("/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = InventoryService.get_instance().remove_order(order_id, reason="deleted")
    return jsonify(order), 200
