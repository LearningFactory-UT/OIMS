# backend/socketio_instance.py
from flask_socketio import SocketIO
from settings import settings

socketio = SocketIO(
    async_mode="threading",
    logger=False,
    engineio_logger=False,
    cors_allowed_origins=settings.cors_origins,
    allow_upgrades=False,
)
