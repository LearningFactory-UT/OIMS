import json
import paho.mqtt.client as mqtt
from pathlib import Path

class MqttHandler():
    def __init__(self, broker):
        self.client = mqtt.Client()#mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(broker, 1883, 60)
        self.client.loop_start()

    def start_timer(self, seconds):
        payload = json.dumps({
            'command': 'start',
            'seconds': seconds,
            'initiator': 'data_manager'
        })
        self.client.publish(topic='/ws_manager/timer', payload=payload)

    def stop_timer(self):
        payload = json.dumps({'command': 'stop', 'initiator':'data_manager'})
        self.client.publish(topic='/ws_manager/timer', payload=payload)



config_path = Path(__file__).parent.parent / "backend" / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

broker = config.get("broker_hostname")
mqtt_handler = MqttHandler(broker)
mqtt_handler.start_timer(30)

# CONVENIENT TERMINAL COMMAND:
# mosquitto_pub -h localhost -t /ws_manager/timer -m '{"command": "start", "seconds": 30, "initiator": "nevermind"}'






