from flask import Blueprint, jsonify, request

from auth.access import (
    clear_auth_session,
    get_current_access_context,
    require_roles,
    set_admin_session,
    set_device_session,
)
from services.auth_service import AuthService
from services.inventory_service import InventoryService


auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/session", methods=["GET"])
def get_session():
    context = get_current_access_context()
    return jsonify(context.to_dict()), 200


@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    auth_service = AuthService.get_instance()
    if not auth_service.authenticate_admin(username, password):
        return jsonify({"error": "Invalid admin credentials"}), 401

    set_admin_session()
    return jsonify(get_current_access_context().to_dict()), 200


@auth_bp.route("/device-login", methods=["POST"])
def device_login():
    data = request.get_json() or {}
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify({"error": "Device token is required"}), 400

    device_payload = AuthService.get_instance().authenticate_device_token(token)
    if device_payload is None:
        return jsonify({"error": "Invalid or disabled device token"}), 401

    set_device_session(device_payload)
    return jsonify(get_current_access_context().to_dict()), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    clear_auth_session()
    return ("", 204)


@auth_bp.route("/devices", methods=["GET"])
@require_roles("admin")
def list_devices():
    return jsonify(AuthService.get_instance().list_devices()), 200


@auth_bp.route("/devices", methods=["POST"])
@require_roles("admin")
def create_device():
    data = request.get_json() or {}
    try:
        payload = AuthService.get_instance().create_device(
            role=data.get("role", "tablet"),
            label=data.get("label", ""),
            station_id=data.get("station_id"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    InventoryService.get_instance().emit_state_snapshot()
    return jsonify(payload), 201


@auth_bp.route("/devices/<device_id>", methods=["PATCH"])
@require_roles("admin")
def update_device(device_id):
    data = request.get_json() or {}
    try:
        payload = AuthService.get_instance().update_device(
            device_id,
            enabled=data.get("enabled"),
            label=data.get("label"),
            station_id=data.get("station_id"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    InventoryService.get_instance().emit_state_snapshot()
    return jsonify(payload), 200


@auth_bp.route("/devices/<device_id>/rotate", methods=["POST"])
@require_roles("admin")
def rotate_device(device_id):
    try:
        payload = AuthService.get_instance().rotate_device_token(device_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    InventoryService.get_instance().emit_state_snapshot()
    return jsonify(payload), 200
