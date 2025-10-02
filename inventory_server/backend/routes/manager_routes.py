# backend/routes/manager_routes.py
from flask import Blueprint, request, jsonify
from services.inventory_service import InventoryService
from socketio_instance import socketio
from services.timer_service import TimerService
from flask import request
from mqtt.mqtt_service import MQTTService

manager_bp = Blueprint("manager_bp", __name__)

inventory_service = None
mqtt_service = None

def init_manager_routes(inv_service, mqtt_svc):
    """
    Called once from run.py or app.py to inject actual references.
    """
    global inventory_service, mqtt_service
    inventory_service = inv_service
    mqtt_service = mqtt_svc

@manager_bp.route("/assembly", methods=["POST"])
def set_assembly_type():
    data = request.get_json()
    atype = data.get("assembly_type", "standard")

    # 1. Update local state in InventoryService
    inventory_service.set_assembly_type(atype)

    # 2. Publish to MQTT so external devices know
    payload = {"assembly_type": atype}
    mqtt_service.publish("/ws_manager/set_assembly_type", payload)

    return jsonify({"message": f"Assembly type set to {atype}"}), 200

@manager_bp.route("/disable", methods=["POST"])
def disable_workstation():
    data = request.get_json()
    # If the payload key is "original_ws_ids", treat them as ws_ids
    ws_ids = data.get("ws_ids") or data.get("original_ws_ids") or []
    inventory_service.disable_workstation(ws_ids)
    return jsonify({"message": f"Disabled {ws_ids}"}), 200

@manager_bp.route("/enable", methods=["POST"])
def enable_workstation():
    data = request.get_json()
    ws_ids = data.get("ws_ids") or data.get("original_ws_ids") or []
    inventory_service.enable_workstation(ws_ids)
    return jsonify({"message": f"Enabled {ws_ids}"}), 200

@socketio.on('connect')
def handle_connect():
    print(f"[Socket.IO] Client connected: {request.sid}")
    tservice = TimerService.get_instance()
    if tservice.timer_running:
        remaining = tservice.get_remaining_seconds()
        socketio.emit('timer_start', {"duration": remaining}, room=request.sid)
    else:
        pass