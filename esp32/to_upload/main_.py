from wifi import WIFI_handler
from mqtt import MQTT_handler
from utils import print_log
import machine

try:
    # Instanciate the wifi_hanlder object that takes care of the wifi connection
    wifi_handler = WIFI_handler()
    wifi_handler.try_connect() # Can raise errors if something unexpected goes wrong

    # Instanciate the mqtt_hanlder object that takes care of the MQTT connection
    mqtt_handler = MQTT_handler()

    print_log('ESP32 ON, CONNECTED TO CLIENT AND READY FOR OPERATION')

    while True:
        mqtt_handler.wait_msg()

except Exception as exc:
    machine.reset()