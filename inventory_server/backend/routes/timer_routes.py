# backend/routes/timer_routes.py
from flask import Blueprint, request, jsonify
from services.timer_service import TimerService

timer_bp = Blueprint("timer_bp", __name__)
timer_service = TimerService.get_instance()

@timer_bp.route("/", methods=["POST"])
def control_timer():
    data = request.get_json()
    command = data.get("command")
    if command == "start":
        seconds = data.get("seconds", 0)
        timer_service.start_timer(seconds)
        return jsonify({"message": f"Timer started for {seconds} seconds."})
    elif command == "stop":
        timer_service.stop_timer()
        return jsonify({"message": "Timer stopped."})
    elif command == "pause":
        timer_service.pause_timer()
        return jsonify({"message": "Timer paused."})
    elif command == "resume":
        timer_service.resume_timer()
        return jsonify({"message": "Timer resumed."})
    else:
        return jsonify({"error": "Unknown command"}), 400

@timer_bp.route("/remaining", methods=["GET"])
def get_remaining():
    remaining = timer_service.get_remaining_seconds()
    return jsonify({"remaining_seconds": remaining})