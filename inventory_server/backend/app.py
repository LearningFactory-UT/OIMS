# backend/app.py
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from routes.inventory_routes import inventory_bp
from routes.timer_routes import timer_bp
from routes.order_routes import order_bp
from routes.help_routes import help_bp
from routes.manager_routes import manager_bp
from flask_sqlalchemy import SQLAlchemy
from models.db_models import OrderModel
from routes.inventory_routes import inventory_bp

socketio = None

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///my_persistent_data.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "some-secret-key"

    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(timer_bp, url_prefix="/api/timer")
    app.register_blueprint(order_bp, url_prefix="/api/orders")
    app.register_blueprint(help_bp, url_prefix="/api/help")
    app.register_blueprint(manager_bp, url_prefix="/api/manager")

    return app