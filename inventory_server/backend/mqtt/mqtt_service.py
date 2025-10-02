# backend/mqtt/mqtt_service.py
import json
import time
import paho.mqtt.client as mqtt
from pathlib import Path
from services.timer_service import TimerService

class MQTTService:
    _instance = None

    @staticmethod
    def get_instance(inventory_service=None):
        if MQTTService._instance is None:
            # print('_________ INSTANCIATED MQTT __________')
            MQTTService._instance = MQTTService(inventory_service)
        return MQTTService._instance

    def __init__(self, inventory_service):
        if MQTTService._instance is not None:
            raise Exception("Use MQTTService.get_instance() instead")
        
        self.inventory_service = inventory_service

        # Load config
        config_path = Path(__file__).parent.parent / "config" / "config.json"
        with open(config_path, "r") as f:
            config = json.load(f)

        self.broker = config.get("broker_hostname", "localhost")
        self.port = config.get("port", 1883)

        self.client = mqtt.Client()

        self.client.on_disconnect = self.on_disconnect
        # self.client.on_connect = self.on_connect

        self.timer_service = TimerService.get_instance()

        print(f"[MQTTService] Connecting to {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, 60)

        self.client.loop_start()

        self.subscribe_to_topics()
        # Publish empty message on identify topic
        self.publish(topic="/ws_manager/identify")
        print(f"[MQTTService] WS identification request published.")


    # def on_connect(self, client, userdata, flags, rc):
        # self.subscribe_to_topics()
        # # Publish empty message on identify topic
        # self.publish(topic="/ws_manager/identify")
        # print(f"[MQTTService] WS identification request published.")

    def on_disconnect(self, client, userdata, rc):
        print("[MQTTService] Disconnected, trying to reconnect...")
        while True:
            try:
                self.client.reconnect()
                print("[MQTTService] Reconnected successfully.")
                break
            except Exception as e:
                print(f"[MQTTService] Reconnect failed: {e}, retry in 5s...")
                time.sleep(5)

    def subscribe_to_topics(self):
        topics_callbacks = {
            "/ws_manager/timer": self.on_timer_message,
            "/ws_manager/orders": self.on_order_message,
            "/ws_manager/update_order": self.on_update_order,
            "/ws_manager/help_request": self.on_help_message,
            "/ws_manager/order_from_previous_ws": self.on_order_from_previous_ws,
            "/ws_manager/order_for_next_ws": self.on_order_for_next_ws,
            "/ws_manager/manual_state": self.on_manual_state,
            "/ws_manager/set_ws_id": self.on_set_ws_id,
            "/ws_manager/set_ws_info": self.on_set_ws_info,
            "/ws_manager/set_assembly_type": self.on_set_assembly_type,
            "/ws_manager/order_delivered": self.on_order_delivered,
            "/ws_manager/delete_oder": self.on_delete_order
        }

        for topic, callback in topics_callbacks.items():
            # print(f'subscribed to {topic}, {callback}')
            self.client.message_callback_add(topic, callback)
            self.client.subscribe(topic)
        
        print(f"[MQTTService] SUSCRIBED TO TOPICS.")

    #     # Wildcard
    #     wildcard = "/ws_manager/#"
    #     self.client.message_callback_add(wildcard, self.on_wildcard_topic)
    #     self.client.subscribe(wildcard, qos=0)

    # # --------------------------------------------------------------------
    # # MQTT Callbacks
    # # --------------------------------------------------------------------
    # def on_wildcard_topic(self, client, userdata, msg):
    #     print(f"[MQTTService] wildcard {msg.topic}: {msg.payload}")

    def on_timer_message(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        command = payload.get("command")
        print(f"[MQTTService] /ws_manager/timer => {command}, {payload}")


        if command == "start":
            seconds = payload.get("seconds", 0)
            self.timer_service.start_timer(seconds)
        elif command == "stop":
            self.timer_service.stop_timer()
        elif command == "pause":
            self.timer_service.pause_timer()
        elif command == "resume":
            self.timer_service.resume_timer()
        else:
            print("[MQTTService] Unknown timer command.")

    def on_order_message(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/orders => {payload}")
        self.inventory_service.add_order(payload)

    def on_order_delivered(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/order_delivered => {payload}")
        self.inventory_service.remove_order(payload)

    def on_delete_order(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/delete_order => {payload}")
        self.inventory_service.remove_order(payload)

    def on_update_order(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/update_order => {payload}")
        self.inventory_service.update_order(payload)

    def on_help_message(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/help_request => {payload}")
        self.inventory_service.update_help(payload)

    def on_order_from_previous_ws(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/order_from_previous_ws => {payload}")
        self.inventory_service.update_order_from_prev_ws(payload)

    def on_order_for_next_ws(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/order_for_next_ws => {payload}")
        self.inventory_service.update_order_for_next_ws(payload)

    def on_manual_state(self, client, userdata, msg):
        """
        payload = {
          "ws_id":"WS-2", or "original_ws_id":"WS-2",
          "side":"L",
          "manual_command":"stop" (or 'start','reset')
        }
        """
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/manual_state => {payload}")
        # unify on ws_id
        ws_id = payload.get("ws_id") or payload.get("original_ws_id")
        side = payload["side"]
        command = payload["manual_command"]
        self.inventory_service.manual_start_stop(ws_id, side, command)

    def on_set_ws_id(self, client, userdata, msg):
        """
        payload = {
          "ws_id":"WS-2",
          // or "original_ws_id":"WS-2"
        }
        """
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/set_ws_id => {payload}")
        ws_id = payload.get("ws_id") or payload.get("original_ws_id")
        # In your new logic, you might not do anything if rename is no longer needed
        self.inventory_service.set_ws_id(ws_id)

    def on_set_ws_info(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/set_ws_info => {payload}")
        self.inventory_service.set_ws_info(payload)

    def on_set_assembly_type(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        print(f"[MQTTService] /ws_manager/set_assembly_type => {payload}")
        atype = payload.get("assembly_type", "standard")
        self.inventory_service.set_assembly_type(atype)

    # --------------------------------------------------------------------
    # Publishing
    # --------------------------------------------------------------------
    def publish(self, topic, payload=None, qos=0, retain=False):
        try:
            msg_str = json.dumps(payload) if isinstance(payload, dict) else payload
            self.client.publish(topic, msg_str, qos, retain)
        except Exception as exc:
            print(f"[MQTTService] publish error: {exc}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()