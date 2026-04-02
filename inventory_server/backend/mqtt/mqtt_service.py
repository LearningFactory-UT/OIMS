from __future__ import annotations

import json
import logging
import time
from threading import Lock

import paho.mqtt.client as mqtt

from services.inventory_service import InventoryService
from services.timer_service import TimerService
from settings import settings


logger = logging.getLogger(__name__)


class MQTTService:
    _instance = None

    @staticmethod
    def get_instance(inventory_service=None):
        if MQTTService._instance is None:
            MQTTService._instance = MQTTService(
                inventory_service or InventoryService.get_instance()
            )
        return MQTTService._instance

    def __init__(self, inventory_service: InventoryService):
        if MQTTService._instance is not None:
            raise Exception("Use MQTTService.get_instance() instead.")

        self.inventory_service = inventory_service
        self.timer_service = TimerService.get_instance()
        self.client = mqtt.Client()
        self.client.on_disconnect = self.on_disconnect
        self._suppressed_order_ids = set()
        self._suppressed_order_lock = Lock()

        self.broker = settings.broker_hostname
        self.port = settings.broker_port

        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

        self.subscribe_to_topics()
        self.request_station_identity()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def on_disconnect(self, client, userdata, rc):
        while True:
            try:
                self.client.reconnect()
                self.subscribe_to_topics()
                self.request_station_identity()
                break
            except Exception:
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
            "/ws_manager/delete_oder": self.on_delete_order,
            "/ws_manager/delete_order": self.on_delete_order,
            "/ws_manager/disable_workstation": self.on_disable_workstation,
            "/ws_manager/enable_workstation": self.on_enable_workstation,
        }

        for topic, callback in topics_callbacks.items():
            self.client.message_callback_add(topic, callback)
            self.client.subscribe(topic)

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    # ------------------------------------------------------------------
    # Publishing helpers
    # ------------------------------------------------------------------
    def publish(self, topic, payload=None, qos=0, retain=False, wait_for_delivery=False):
        payload_string = json.dumps(payload) if isinstance(payload, dict) else payload
        message_info = self.client.publish(topic, payload_string, qos, retain)

        if message_info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                "MQTT publish failed for topic %s with rc=%s and payload=%s",
                topic,
                message_info.rc,
                payload_string,
            )
            return False

        if wait_for_delivery:
            message_info.wait_for_publish(timeout=2.0)
            logger.info("MQTT published topic %s payload=%s", topic, payload_string)

        return True

    def publish_legacy_order(self, payload: dict):
        order_id = ((payload or {}).get("attributes") or {}).get("order_id")
        if order_id:
            with self._suppressed_order_lock:
                self._suppressed_order_ids.add(order_id)
        published = self.publish(
            "/ws_manager/orders",
            payload=payload,
            wait_for_delivery=True,
        )
        if published:
            logger.info("Legacy order published for order_id=%s", order_id)

    def _consume_suppressed_order(self, order_id: str | None) -> bool:
        if not order_id:
            return False
        with self._suppressed_order_lock:
            if order_id not in self._suppressed_order_ids:
                return False
            self._suppressed_order_ids.remove(order_id)
            return True

    def request_station_identity(self):
        self.publish("/ws_manager/identify", payload={})

    def publish_timer_command(
        self,
        command: str,
        seconds: int = 0,
        initiator: str = "inventory_server",
        handled_by_server: bool = True,
    ):
        payload = {"command": command, "initiator": initiator}
        if command == "start":
            payload["seconds"] = seconds
        if handled_by_server:
            payload["handled_by_server"] = True
        self.publish("/ws_manager/timer", payload=payload)

    def publish_set_ws_id_response(self, response: dict):
        self.publish("/ws_manager/set_ws_id_response", response)

    def publish_assembly_type(self, assembly_type: str, handled_by_server: bool = True):
        payload = {"assembly_type": assembly_type}
        if handled_by_server:
            payload["handled_by_server"] = True
        self.publish("/ws_manager/set_assembly_type", payload)

    def publish_workstation_toggle(
        self,
        command: str,
        original_ws_ids: list[str],
        handled_by_server: bool = True,
    ):
        payload = {"original_ws_ids": original_ws_ids}
        if handled_by_server:
            payload["handled_by_server"] = True
        self.publish(f"/ws_manager/{command}_workstation", payload)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _decode_payload(self, msg):
        if not msg.payload:
            return {}
        return json.loads(msg.payload)

    def _handled_by_server(self, payload: dict) -> bool:
        return bool(payload.get("handled_by_server"))

    def on_timer_message(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        if self._handled_by_server(payload):
            return
        command = payload.get("command")
        seconds = int(payload.get("seconds", 0))
        self.timer_service.apply_command(command, seconds=seconds, source="mqtt_v1")

    def on_order_message(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        attributes = payload.get("attributes") or {}
        if self._consume_suppressed_order(attributes.get("order_id")):
            return
        self.inventory_service.add_order(payload, source="mqtt_v1")

    def on_order_delivered(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.remove_order(payload, reason="delivered")

    def on_delete_order(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.remove_order(payload, reason="deleted")

    def on_update_order(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.update_order(payload)

    def on_help_message(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.update_help(payload, source="mqtt_v1")

    def on_order_from_previous_ws(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.update_order_from_prev_ws(payload, source="mqtt_v1")

    def on_order_for_next_ws(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.update_order_for_next_ws(payload, source="mqtt_v1")

    def on_manual_state(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        station_id = payload.get("original_ws_id") or payload.get("ws_id")
        self.inventory_service.manual_start_stop(
            station_id,
            payload["side"],
            payload["manual_command"],
        )

    def on_set_ws_id(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        response = self.inventory_service.set_ws_id(
            payload["original_ws_id"],
            payload["ws_id"],
        )
        self.publish_set_ws_id_response(response)

    def on_set_ws_info(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        self.inventory_service.set_ws_info(payload)

        timer_snapshot = self.timer_service.snapshot()
        if timer_snapshot.state == "running":
            self.publish_timer_command(
                "start",
                seconds=timer_snapshot.remaining_seconds,
                initiator="inventory_server_sync",
                handled_by_server=True,
            )
        elif timer_snapshot.state == "paused":
            self.publish_timer_command(
                "pause",
                initiator="inventory_server_sync",
                handled_by_server=True,
            )

        self.publish_assembly_type(
            self.inventory_service.get_assembly_type(),
            handled_by_server=True,
        )

    def on_set_assembly_type(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        if self._handled_by_server(payload):
            return
        self.inventory_service.set_assembly_type(payload.get("assembly_type", "standard"))

    def on_disable_workstation(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        if self._handled_by_server(payload):
            return
        ws_ids = payload.get("original_ws_ids") or payload.get("ws_ids") or []
        self.inventory_service.disable_workstation(ws_ids)

    def on_enable_workstation(self, client, userdata, msg):
        payload = self._decode_payload(msg)
        if self._handled_by_server(payload):
            return
        ws_ids = payload.get("original_ws_ids") or payload.get("ws_ids") or []
        self.inventory_service.enable_workstation(ws_ids)
