def build_legacy_order_payload(order: dict) -> dict:
    return {
        "items": order.get("items_dict", {}),
        "attributes": {
            "ws_id": order["station_id"],
            "operator_side": order["side"],
            "urgent": bool(order.get("urgent", False)),
            "order_id": order["order_id"],
        },
    }
