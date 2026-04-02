# backend/socketio_instance.py
from flask_socketio import SocketIO

socketio = SocketIO(
    async_mode="threading",
    logger=False,
    engineio_logger=False,
    cors_allowed_origins="*",
    allow_upgrades=False,
)
