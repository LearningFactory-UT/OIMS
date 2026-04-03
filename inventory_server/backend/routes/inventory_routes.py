from flask import Blueprint, jsonify

from auth.access import require_roles
from services.inventory_service import InventoryService


inventory_bp = Blueprint("inventory_bp", __name__)


@inventory_bp.route("/urgent", methods=["GET"])
@require_roles("admin", "inventory")
def get_urgent_orders():
    inventory_service = InventoryService.get_instance()
    urgent_orders = [
        order
        for order in inventory_service.get_active_orders()
        if order.get("urgent")
    ]
    return jsonify(urgent_orders)
