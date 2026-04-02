from flask import Flask
from flask_cors import CORS

from routes.help_routes import help_bp
from routes.inventory_routes import inventory_bp
from routes.manager_routes import manager_bp
from routes.order_routes import order_bp
from routes.station_routes import station_bp
from routes.system_routes import system_bp
from routes.timer_routes import timer_bp
from settings import settings


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins}})
    app.config["SECRET_KEY"] = settings.secret_key

    app.register_blueprint(system_bp, url_prefix="/api/system")
    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(timer_bp, url_prefix="/api/timer")
    app.register_blueprint(order_bp, url_prefix="/api/orders")
    app.register_blueprint(help_bp, url_prefix="/api/help")
    app.register_blueprint(manager_bp, url_prefix="/api/manager")
    app.register_blueprint(station_bp, url_prefix="/api/stations")

    return app
