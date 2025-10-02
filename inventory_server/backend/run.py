# backend/run.py
from app import create_app
from services.timer_service import TimerService
from socketio_instance import socketio
from mqtt.mqtt_service import MQTTService
from models.db_models import OrderModel  # import so recognized
from db_engine import engine, Base
from services.inventory_service import InventoryService
from services.andon_service import AndonService
from routes.manager_routes import init_manager_routes
import logging

def initialize_db():
    import os
    # Comment the if statement if you dont want the orders to be deleted after inventory restart
    if os.path.exists("my_persistent_data.db"):
        os.remove("my_persistent_data.db")
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified.")


if __name__ == "__main__":
    initialize_db()
    app = create_app()

    inv_service = InventoryService.get_instance()
    mqtt_service = MQTTService.get_instance(inventory_service=inv_service)

    andon_svc = AndonService.get_instance()
    andon_svc.set_mqtt_service(mqtt_service)

    init_manager_routes(inv_service, mqtt_service)
    # init_timer_service(mqtt_service)

    socketio.init_app(app, cors_allowed_origins="*")

    port = 3010
    # socketio.run(app, port=port, debug=True)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)
    socketio.run(app, host="0.0.0.0", port=port) #, debug=False, use_reloader=False)