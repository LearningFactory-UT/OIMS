# backend/routes/inventory_routes.py
from flask import Blueprint, jsonify
from services.inventory_service import InventoryService

inventory_bp = Blueprint("inventory_bp", __name__)
inventory_service = InventoryService.get_instance()

@inventory_bp.route("/urgent", methods=["GET"])
def get_urgent_orders():
    urgent_orders = [o for o in inventory_service.orders_dict.values() if o.urgent]
    return jsonify([o.to_serializable_dict() for o in urgent_orders])