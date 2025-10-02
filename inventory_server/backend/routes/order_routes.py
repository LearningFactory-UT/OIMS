# backend/routes/order_routes.py
from flask import Blueprint, request, jsonify
from models.db_models import OrderModel
from services.inventory_service import InventoryService
from db_engine import SessionLocal

order_bp = Blueprint("order_bp", __name__)
inventory_service = InventoryService.get_instance()

@order_bp.route("/", methods=["GET"])
def get_all_orders():
    session = SessionLocal()
    try:
        all_records = session.query(OrderModel).filter(OrderModel.end_time == None).all()
        response = [record.to_dict() for record in all_records]
    except Exception as exc:
        print(f"[OrderService] Error fetching orders: {exc}")
        response = []
    finally:
        session.close()

    return jsonify(response)

@order_bp.route("/", methods=["POST"])
def create_order():
    order_data = request.get_json()
    inventory_service.add_order(order_data)
    return jsonify({"message": "Order created"}), 201

@order_bp.route("/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    inventory_service.remove_order({"order_id": order_id}, reason="deleted")
    return jsonify({"message": f"Order {order_id} removed."})