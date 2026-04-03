from flask import Blueprint, jsonify, request

from auth.access import get_current_access_context, require_roles, require_station_access
from services.inventory_service import InventoryService


help_bp = Blueprint("help_bp", __name__)


@help_bp.route("/", methods=["POST"])
@require_roles("admin", "tablet")
def request_help():
    data = request.get_json() or {}
    station_id = data.get("original_ws_id") or data.get("ws_id") or data.get("station_id")
    if get_current_access_context().role == "tablet":
        try:
            require_station_access(station_id)
        except PermissionError as error:
            return jsonify({"error": str(error)}), 403
    state = InventoryService.get_instance().update_help(data)
    return jsonify(state), 200
