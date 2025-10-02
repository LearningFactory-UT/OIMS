import json
import time
import umqtt.simple as simple
from utils import print_log, resolve_mdns_hostname
from config import read_json
from light_control import light_control

MAX_CONNECTION_ATTEMPTS = 5
CONNECTION_ATTEMPT_DELAY = 5

class MQTT_handler:

    def __init__(self):
        self.config_dict = read_json()
        self.esp32_id = f"ESP32_{self.config_dict['original_ws_id']}"

        try:
            # Attempt to resolve the mDNS hostname of the MQTT broker
            mqtt_server = resolve_mdns_hostname(self.config_dict['broker_hostname'])
            # Log Resolved MQTT broker IP
            print_log(f'Resolved MQTT broker IP: {mqtt_server}')
        except Exception as exc:
            # Log MQTT broker resolution failure
            print_log('Unable to resolve MQTT broker.', error=True, exc=exc)
            # The exception is gonna get caught on the main try-except, causes machine.reset()
            raise
    
        try:
            self.connect_to_mqtt(mqtt_server)

            # Log successful MQTT broker connection
            print_log(f'Connected to the MQTT broker!')
        except TimeoutError as exc:
            print_log('Unable to connect to MQTT broker.', error=True, exc=exc)
            # The exception is gonna get caught on the main try-except, causes machine.reset()
            raise

    def connect_to_mqtt(self, mqtt_server):
            """
            Connects to an MQTT broker.

            :param mqtt_server: str - The MQTT server to connect to
            :param esp32_id: str - The unique ID of the ESP32 device
            """

            attempts = 0
            while attempts < MAX_CONNECTION_ATTEMPTS:
                try:
                    self.client = simple.MQTTClient(self.esp32_id, mqtt_server, port=1883, keepalive=60)
                    self.client.set_callback(self.on_message_callback)
                    self.connect()

                    self.initialize_subscriptions()
                    break
                except Exception as exc:
                    attempts += 1
                    time.sleep(CONNECTION_ATTEMPT_DELAY)
            else:
                # The exception is gonna get caught on the main try-except, causes machine.reset()
                raise TimeoutError('Unable to enstablish connection with mqtt broker.')
            
    def initialize_subscriptions(self):
        update_lights_topic = '/ws_manager/update_lights'

        self.subscribe(update_lights_topic.encode())
        print_log(f'ESP32 subscribed to the topic {update_lights_topic}')

    def on_message_callback(self, topic, msg):
        """
        Callback function to handle subscribed MQTT messages.

        :param topic: bytes - The topic of the message
        :param msg: bytes - The received message
        """
        print_log(f'Message {msg} received on topic {topic}')

        # Decode message & topic
        decoded_msg = msg.decode('utf-8')
        decoded_topic = topic.decode('utf-8')

        payload = json.loads(decoded_msg)
        original_ws_id = payload['original_ws_id']

        #{'original_ws_id':'ALL', 'side':'ALL', 'image_name':''}
        if original_ws_id == self.config_dict['original_ws_id'] or original_ws_id == 'ALL':
            sides = payload['side']
            if sides == 'ALL':
                sides = ['L', 'R']
            else:
                sides = [sides]
            light_code = payload['image_name']
            
            for side in sides:
                light_control(side, light_code)
        

    def connect(self, reconnection_attempts=0):
        '''
        Try to connect to the MQTT broker
        if not possible try to enstablish wifi connection.
        '''
        try:
            self.client.connect()
        except Exception as e:
            self.try_reconnect()
            if reconnection_attempts < MAX_CONNECTION_ATTEMPTS:
                reconnection_attempts += 1
                self.connect(reconnection_attempts)
            else:
                # Some other error other than connection, propagate it
                raise

    def subscribe(self, topic, reconnection_attempts=0):
        try:
            self.client.subscribe(topic)
            reconnection_attempts = 0
        except Exception as e:
            self.try_reconnect()
            if reconnection_attempts < MAX_CONNECTION_ATTEMPTS:
                reconnection_attempts += 1
                self.subscribe(topic, reconnection_attempts)
            else:
                # Some other error other than connection, propagate it
                raise


    def wait_msg(self, reconnection_attempts=0):
        # self.client.wait_msg()
        try:
            #if reconnection_attempts:
            self.client.wait_msg()
        except Exception as exc:
            if isinstance(exc, OSError) and exc.args[0] == -1:
                # Just the ping response
                print_log('Just the ping response', error=True)
            else:
                print_log('Not the ping!', error=True)
            
            reconnection_attempts += 1
            if reconnection_attempts < MAX_CONNECTION_ATTEMPTS:
                self.try_reconnect()
                self.initialize_subscriptions()
                # Doesn't call itself again because it's inside a while True loop.
            else:
                raise
    
    def try_reconnect(self):
        '''
        This function tries to connect to the MQTT broker up to MAX_CONNECTION_ATTEMPTS attempts.
        '''
        attempts = 0
        while attempts < MAX_CONNECTION_ATTEMPTS:
            attempts += 1

            try:
                self.client.connect()
                break
            except Exception as exc:
                time.sleep(CONNECTION_ATTEMPT_DELAY)
        if attempts >= MAX_CONNECTION_ATTEMPTS:
            print_log(f"Exception while connecting MQTT broker", error=True, exc=exc)
            raise TimeoutError('Unable to reconnect to the MQTT broker.')
    


    # def publish(self, topic, payload, reconnection_attempts=0):
    #     try:
    #         self.client.publish(topic, payload)
    #     except OSError:
    #         self.try_reconnect()
    #         if reconnection_attempts < MAX_CONNECTION_ATTEMPTS:
    #             reconnection_attempts += 1
    #             self.publish(topic, payload, reconnection_attempts)
    #         else:
    #             # Some other error other than connection, propagate it
    #             raise


    # def check_msg(self, reconnection_attempts=0):
    #     try:
    #         self.client.check_msg()
    #         reconnection_attempts = 0
    #     except Exception as exc:
    #         if isinstance(exc, OSError) and exc.args[0] == -1:
    #             print_log('Just the ping response', error=True)
    #         else:
    #             print_log('Not the ping!', error=True)
            
    #         reconnection_attempts += 1
    #         if reconnection_attempts < MAX_CONNECTION_ATTEMPTS:
    #             self.try_reconnect()
    #             self.initialize_subscriptions()
    #             # Doesn't call itself again because it's inside a while True loop.
    #         else:
    #             raise


    