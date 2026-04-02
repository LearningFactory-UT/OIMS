from flask import Blueprint, jsonify, request

from services.inventory_service import InventoryService


help_bp = Blueprint("help_bp", __name__)


@help_bp.route("/", methods=["POST"])
def request_help():
    data = request.get_json() or {}
    state = InventoryService.get_instance().update_help(data)
    return jsonify(state), 200
