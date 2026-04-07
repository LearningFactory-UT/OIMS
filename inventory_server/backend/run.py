import logging

from sqlalchemy import inspect, text

from app import create_app
from db_engine import Base, engine
from mqtt.mqtt_service import MQTTService
from services.andon_service import AndonService
from services.inventory_service import InventoryService
from settings import settings
from socketio_instance import socketio


class _IgnoreStaleSocketSessionFilter(logging.Filter):
    def filter(self, record):
        return "Invalid session" not in record.getMessage()


def _apply_sqlite_migrations():
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "orders" in table_names:
            order_columns = {column["name"] for column in inspector.get_columns("orders")}
            if "original_ws_id" not in order_columns:
                connection.execute(text("ALTER TABLE orders ADD COLUMN original_ws_id VARCHAR"))
            if "source" not in order_columns:
                connection.execute(
                    text("ALTER TABLE orders ADD COLUMN source VARCHAR DEFAULT 'mqtt_v1'")
                )
            if "display_name" not in order_columns:
                connection.execute(text("ALTER TABLE orders ADD COLUMN display_name VARCHAR"))
            connection.execute(
                text("UPDATE orders SET original_ws_id = ws_id WHERE original_ws_id IS NULL")
            )
            connection.execute(text("UPDATE orders SET display_name = ws_id WHERE display_name IS NULL"))
            connection.execute(text("UPDATE orders SET ws_id = original_ws_id WHERE original_ws_id IS NOT NULL"))

        if "timers" in table_names:
            timer_columns = {column["name"] for column in inspector.get_columns("timers")}
            if "state" not in timer_columns:
                connection.execute(
                    text("ALTER TABLE timers ADD COLUMN state VARCHAR DEFAULT 'stopped'")
                )
            if "paused_seconds" not in timer_columns:
                connection.execute(
                    text("ALTER TABLE timers ADD COLUMN paused_seconds INTEGER DEFAULT 0")
                )
            if "updated_at" not in timer_columns:
                connection.execute(text("ALTER TABLE timers ADD COLUMN updated_at DATETIME"))


def initialize_db():
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT OR IGNORE INTO timers "
                "(id, state, timer_running, total_seconds, paused_seconds) "
                "VALUES (1, 'stopped', 0, 0, 0)"
            )
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO system_state "
                "(id, assembly_type, updated_at) "
                "VALUES (1, 'standard', CURRENT_TIMESTAMP)"
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    initialize_db()
    app = create_app()

    inventory_service = InventoryService.get_instance()
    mqtt_service = MQTTService.get_instance(inventory_service=inventory_service)

    andon_service = AndonService.get_instance()
    andon_service.set_mqtt_service(mqtt_service)

    socketio.init_app(app, cors_allowed_origins=settings.cors_origins)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)
    logging.getLogger("engineio.server").addFilter(_IgnoreStaleSocketSessionFilter())

    socketio.run(app, host=settings.host, port=settings.port)
