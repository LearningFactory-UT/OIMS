# backend/routes/help_routes.py
from flask import Blueprint, request, jsonify
from services.inventory_service import InventoryService

help_bp = Blueprint("help_bp", __name__)
inventory_service = InventoryService.get_instance()

@help_bp.route("/", methods=["POST"])
def request_help():
    """
    POST /api/help
    Example body:
      {
        "help_id":"help-123",
        "ws_id":"WS-2",
        "side":"L",
        "help":true,
        "idle":false
      }
    """
    data = request.get_json()
    inventory_service.update_help(data)
    return jsonify({"message": "Help request updated."}), 200