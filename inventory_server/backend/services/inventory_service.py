from datetime import datetime
from typing import Dict
from models.order import Order
from services.andon_service import AndonService
from socketio_instance import socketio
from db_engine import SessionLocal
from models.db_models import OrderModel
from services.timer_service import TimerService

class InventoryService:
    _instance = None

    @staticmethod
    def get_instance():
        if InventoryService._instance is None:
            InventoryService._instance = InventoryService()
        return InventoryService._instance

    def __init__(self):
        if InventoryService._instance is not None:
            raise Exception("Use InventoryService.get_instance() instead.")

        print('_______ INSTANCIATING INV SERVICE ______')
        # Main state
        self.orders_dict: Dict[str, Order] = {}
        self.past_orders_dict: Dict[str, Order] = {}

        # help requests
        self.help_requests_dict = {}  

        # Orders from a previous station
        self.order_from_prev_ws_dict = {}

        # Orders for the next station
        self.order_for_next_ws_dict = {}

        # Whether we have a manual "stop" or "start" on a given ws/side
        self.ws_stop_dict = {}  # {ws_id: {"L": bool, "R": bool}}

        # Track if a side is "already active" on that ws
        self.ws_already_active_dict = {}  # {ws_id: {"L": bool, "R": bool}}

        # We no longer store ws_id_dict for rename logic
        # self.ws_id_dict = {}

        self.assembly_type = "standard"  # or "simplified"

        self.andon_service = AndonService.get_instance()
        self.timer_service = TimerService.get_instance()

        # Register socket event handlers
        socketio.on_event('timer_state_changed', self._handle_timer_state_change)

    # -------------------------
    # ORDER MANAGEMENT
    # -------------------------
    def add_order(self, order_data: dict):
        attributes = order_data["attributes"]
        order_id = attributes["order_id"]
        
        # unify on a single ws_id
        ws_id = attributes.get("ws_id") or attributes.get("original_ws_id")
        if not ws_id:
            print(f"[InventoryService] Missing ws_id. Cannot add order {order_id}.")
            return

        side = attributes["operator_side"]
        urgent_flag = attributes.get("urgent", False)
        items_dict = order_data["items"]

        # Check if order already in memory
        if order_id in self.orders_dict:
            print(f"[InventoryService] Order {order_id} already exists in-memory. Ignoring.")
            return

        # Insert into DB
        session = SessionLocal()
        try:
            existing = session.query(OrderModel).filter_by(order_id=order_id).first()
            if existing:
                print(f"Order {order_id} already exists in DB. Ignoring.")
                return

            new_order_record = OrderModel(
                order_id=order_id,
                ws_id=ws_id,
                side=side,
                creation_time=datetime.now(),
                urgent=urgent_flag,
                items_json=items_dict
            )
            session.add(new_order_record)
            session.commit()
        except Exception as exc:
            session.rollback()
            print(f"[InventoryService] DB error while adding order {order_id}: {exc}")
            return
        finally:
            session.close()

        # Also create in-memory
        new_order = Order(
            order_id=order_id,
            ws_id=ws_id,
            side=side,
            creation_time=datetime.now(),
            urgent=urgent_flag,
            items_dict=items_dict,
            label_text=f"{ws_id} {side}"
        )
        self.orders_dict[order_id] = new_order

        # Emit updated order list
        current_orders = [o.to_serializable_dict() for o in self.orders_dict.values()]
        socketio.emit("orders_updated", {"orders": current_orders})

        print(f"[InventoryService] Added order {order_id} (ws_id={ws_id}).")
        self.update_ws_representation(ws_id)

    def remove_order(self, order_data: dict, reason="manual"):
        order_id = order_data["order_id"]
        session = SessionLocal()
        try:
            record = session.query(OrderModel).filter_by(order_id=order_id).first()
            if not record:
                print(f"[InventoryService] Order {order_id} not found in DB.")
            else:
                session.delete(record)
                session.commit()
                print(f"Order {order_id} deleted from database with reason: {reason}")
        except Exception as exc:
            session.rollback()
            print(f"[InventoryService] DB error while deleting order {order_id}: {exc}")
        finally:
            session.close()

        order = self.orders_dict.pop(order_id, None)
        if not order:
            print(f"[InventoryService] Order {order_id} not found in-memory.")
            return

        order.end_time = datetime.now()
        order.end_reason = reason
        self.past_orders_dict[order_id] = order

        socketio.emit("order_removed", {
            "order_id": order_id,
            "reason": reason
        })
        # We only know the ws_id from the order object
        self.update_ws_representation(order.ws_id)

        print(f"[InventoryService] Removed order {order_id} with reason {reason}")

    def update_order(self, update_order_dict: dict):
        order_id = update_order_dict.get("order_id")
        if order_id not in self.orders_dict:
            print(f"[InventoryService] Order {order_id} not found for update.")
            return

        order = self.orders_dict[order_id]
        new_urgent_val = update_order_dict.get("urgent")
        if new_urgent_val is not None:
            order.urgent = bool(new_urgent_val)
            print(f"[InventoryService] Updated order {order_id}, urgent={order.urgent}")
            
            # Emit an event to notify the frontend about the order update
            socketio.emit("order_updated", {
                "order_id": order_id,
                "urgent": order.urgent
            })

        self.update_ws_representation(order.ws_id)

    def clear_all_orders(self, reason="timer"):
        orders_to_remove = [{"order_id": oid} for oid in list(self.orders_dict.keys())]
        for order_dict in orders_to_remove:
            self.remove_order(order_dict, reason=reason)
        print(f"[InventoryService] Cleared all orders due to {reason}.")
        # set all lights to red
        for ws_id in self.ws_stop_dict.keys():
            self.update_ws_representation(ws_id, time_s_up=True)

    # -------------------------
    # HELP REQUESTS
    # -------------------------
    def update_help(self, help_dict: dict):
        help_id = help_dict["help_id"]
        ws_id = help_dict.get("ws_id") or help_dict.get("original_ws_id")
        side = help_dict["side"]

        if help_dict["help"] is True:
            self.help_requests_dict[help_id] = {
                "ws_id": ws_id,
                "side": side,
                "idle": help_dict["idle"],
                "creation_time": datetime.now()
            }
            print(f"[InventoryService] Help request started for {ws_id} side {side}.")
        else:
            to_remove = []
            for key, val in self.help_requests_dict.items():
                if val["ws_id"] == ws_id and val["side"] == side:
                    to_remove.append(key)
            for rm in to_remove:
                self.help_requests_dict.pop(rm, None)
            print(f"[InventoryService] Help request ended for {ws_id} side {side}.")

        self.update_ws_representation(ws_id)

    # -------------------------
    # ORDER FROM PREVIOUS / FOR NEXT
    # -------------------------
    def update_order_from_prev_ws(self, prev_ws_order_dict: dict):
        prev_ws_order_id = prev_ws_order_dict["prev_ws_order_id"]
        ws_id = prev_ws_order_dict.get("ws_id") or prev_ws_order_dict.get("original_ws_id")
        side = prev_ws_order_dict["side"]

        if prev_ws_order_dict["pending"] is True:
            self.order_from_prev_ws_dict[prev_ws_order_id] = {
                "ws_id": ws_id,
                "side": side,
                "creation_time": datetime.now(),
                "idle": prev_ws_order_dict["idle"]
            }
            print(f"[InventoryService] Received an incoming order from prev WS: {prev_ws_order_id}.")
        else:
            to_remove = []
            for pid, val in self.order_from_prev_ws_dict.items():
                if val["ws_id"] == ws_id and val["side"] == side:
                    to_remove.append(pid)
            for rm in to_remove:
                self.order_from_prev_ws_dict.pop(rm, None)
            print(f"[InventoryService] Cleared an incoming order from prev WS: {prev_ws_order_id}.")

        self.update_ws_representation(ws_id)

    def update_order_for_next_ws(self, ready_for_next_dict: dict):
        ready_for_next_id = ready_for_next_dict["ready_for_next_id"]
        ws_id = ready_for_next_dict.get("ws_id") or ready_for_next_dict.get("original_ws_id")
        side = ready_for_next_dict["side"]

        if ready_for_next_dict["ready"] is True:
            self.order_for_next_ws_dict[ready_for_next_id] = {
                "ws_id": ws_id,
                "side": side,
                "ready": True
            }
            print(f"[InventoryService] {ws_id} side {side} has order ready for next ws.")
        else:
            to_remove = []
            for rid, val in self.order_for_next_ws_dict.items():
                if val["ws_id"] == ws_id and val["side"] == side:
                    to_remove.append(rid)
            for rm in to_remove:
                self.order_for_next_ws_dict.pop(rm, None)
            print(f"[InventoryService] Cleared order_for_next_ws from {ws_id}, side {side}.")

        self.update_ws_representation(ws_id)

    # -------------------------
    # WORKSTATION STATE MGMT
    # -------------------------
    def manual_start_stop(self, ws_id: str, side: str, command: str):
        if ws_id not in self.ws_stop_dict:
            self.ws_stop_dict[ws_id] = {"L": False, "R": False}
            self.ws_already_active_dict[ws_id] = {"L": False, "R": False}

        if command == "start":
            self.ws_already_active_dict[ws_id][side] = True
            self.ws_stop_dict[ws_id][side] = False
            print(f"[InventoryService] Manual START {ws_id} side {side}.")
        elif command == "stop":
            self.ws_stop_dict[ws_id][side] = True
            print(f"[InventoryService] Manual STOP {ws_id} side {side}.")
        elif command == "reset":
            self.ws_stop_dict[ws_id][side] = False
            self.ws_already_active_dict[ws_id][side] = False
            print(f"[InventoryService] Manual RESET {ws_id} side {side}.")

        self.update_ws_representation(ws_id)

    def set_ws_id(self, ws_id: str):
        """
        If rename logic is no longer needed, you can basically no-op this,
        or do something minimal.
        """
        print(f"[InventoryService] set_ws_id called with {ws_id}, but rename logic is removed.")
        # Optionally do nothing, or store in some single dict if you want.

    def set_ws_info(self, info_dict: dict):
        """
        If there's any info about existing orders, etc., handle it.
        But if you no longer need a big sync, you can simplify or remove this.
        """
        print(f"[InventoryService] set_ws_info from {info_dict.get('ws_id')}")
        # Example: unify ws_id
        ws_id = info_dict.get("ws_id") or info_dict.get("original_ws_id")
        # Then do your custom logic if needed

    # def disable_workstation(self, ws_ids: list):
    #     for w in ws_ids:
    #         if w not in self.ws_stop_dict:
    #             self.ws_stop_dict[w] = {"L": False, "R": False}
    #             self.ws_already_active_dict[w] = {"L": False, "R": False}
    #         self.ws_stop_dict[w]["L"] = True
    #         self.ws_stop_dict[w]["R"] = True
    #         print(f"[InventoryService] disable_workstation: {w}")
    #         self.update_ws_representation(w)

    # def enable_workstation(self, ws_ids: list):
    #     for w in ws_ids:
    #         if w not in self.ws_stop_dict:
    #             self.ws_stop_dict[w] = {"L": False, "R": False}
    #             self.ws_already_active_dict[w] = {"L": False, "R": False}
    #         self.ws_stop_dict[w]["L"] = False
    #         self.ws_stop_dict[w]["R"] = False
    #         print(f"[InventoryService] enable_workstation: {w}")
    #         self.update_ws_representation(w)

    # -------------------------
    # ASSEMBLY TYPE MGMT
    # -------------------------
    def set_assembly_type(self, atype: str):
        if atype in ["standard", "simplified"]:
            self.assembly_type = atype
            print(f"[InventoryService] Assembly type set to {atype}")

    def get_assembly_type(self):
        return self.assembly_type

    # -------------------------
    # UPDATE LIGHTS ("Andon") LOGIC
    # -------------------------
    def update_ws_representation(self, ws_id, time_s_up=False):
        # This function is called for each workstation, for each action in the workstation 
        
        # If we haven't seen this station, init
        if ws_id not in self.ws_stop_dict:
            self.ws_stop_dict[ws_id] = {"L": False, "R": False}
            self.ws_already_active_dict[ws_id] = {"L": False, "R": False}

        update_dicts = []
        
        if time_s_up:
            # time_s_up => everything red
            for side in ["L", "R"]:
                update_dicts.append({"side": side, "image_name": "R"})
        else: 
            # Timer is running 

            # Initialize all the flags
            idle            = {"L": False, "R": False}
            pending_order   = {"L": False, "R": False}
            help_req        = {"L": False, "R": False}
            order_from_prev = {"L": False, "R": False}
            order_for_next  = {"L": False, "R": False}

            # Gather all orders for this ws
            pending_orders = [o for o in self.orders_dict.values() if o.ws_id == ws_id]
            for order in pending_orders:
                pending_order[order.side] = True
                if order.urgent:
                    idle[order.side] = True
                self.ws_already_active_dict[ws_id][order.side] = True

            # Gather help requests
            station_help = [val for val in self.help_requests_dict.values() if val["ws_id"] == ws_id]
            for h in station_help:
                help_req[h["side"]] = True
                if h["idle"]:
                    idle[h["side"]] = True
                self.ws_already_active_dict[ws_id][h["side"]] = True

            # Gather from-prev
            station_prev = [val for val in self.order_from_prev_ws_dict.values() if val["ws_id"] == ws_id]
            for p in station_prev:
                order_from_prev[p["side"]] = True
                if p["idle"]:
                    idle[p["side"]] = True
                self.ws_already_active_dict[ws_id][p["side"]] = True

            # Gather for-next
            station_next = [val for val in self.order_for_next_ws_dict.values() if val["ws_id"] == ws_id]
            for n in station_next:
                order_for_next[n["side"]] = True
                self.ws_already_active_dict[ws_id][n["side"]] = True

            # If the global timer is not running => everything is effectively idle
            if not self.timer_service.is_timer_running():
                idle["L"] = True
                idle["R"] = True
                help_req["L"] = False
                help_req["R"] = False
                order_from_prev["L"] = False
                order_from_prev["R"] = False
                order_for_next["L"] = False
                order_for_next["R"] = False
                pending_order["L"] = False
                pending_order["R"] = False

            color_string = {'L':'', 'R':''}
            # print(f'ws_already_active_dict[{ws_id}] = {self.ws_already_active_dict[ws_id]}')
            for side in ['L', 'R']:
                if self.ws_already_active_dict[ws_id].get(side):

                    if idle[side] or self.ws_stop_dict[ws_id][side]:
                        color_string[side] = 'R'
                    else:
                        color_string[side] = 'G'

                    if order_for_next[side]:
                        color_string[side] += 'g'
                    
                    if help_req[side]:
                        color_string[side] += 'Y'
                    
                    if order_from_prev[side]:
                        color_string[side] += 'b'

                    if pending_order[side]:
                        color_string[side] += 'B'
                    
                    update_dicts.append({'side': side, 'image_name': color_string[side]})
                else:
                    color_string[side] = 'R'
                    update_dicts.append({'side': side, 'image_name': color_string[side]})
            

        for upd in update_dicts:
            self.andon_service.update_lights(ws_id, upd["side"], upd["image_name"])

        print(f"update_dicts = {update_dicts}")

    def _handle_timer_state_change(self, data):
        """Handle timer state changes and update workstation representations accordingly."""
        if data.get('state') == 'started':
            # Update all workstations when timer starts
            for ws_id in self.ws_stop_dict.keys():
                self.update_ws_representation(ws_id)