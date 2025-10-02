import time
import paho.mqtt.client as mqtt
# from app.utils import debug_print, get_rpi_serial_number
# import app.callbacks as callbacks
# import app.states as states
# import app.commands as commands
# import app.status as status
import callbacks
import json



class Local_MQTT_Handler:
    def __init__(self) -> None:
        # Create an MQTT client and connect to the local broker.
        self.client = mqtt.Client()#mqtt.CallbackAPIVersion.VERSION1)

        # Load the config.json file
        with open('config.json', 'r') as file:
            config = json.load(file)
        
        # Set up the connection parameters.
        broker = config['broker_hostname']
        port = 1883

        # Connect the client to the broker.
        self.client.connect(broker, port, 60)
        print('Connected to the broker')
        
        self.client.on_disconnect = self.on_disconnect

        
        # Start the client before publishing.
        self.client.loop_start()

    def subscribe_to_topics(self):
        delete_order_topic = "/ws_manager/delete_oder"
        self.message_callback_add(delete_order_topic, callbacks.on_delete_order)
        self.subscribe(delete_order_topic)
        
        order_delivered_topic = "/ws_manager/order_delivered"
        self.message_callback_add(order_delivered_topic, callbacks.on_order_delivered)
        self.subscribe(order_delivered_topic)

        broadcast_topic = "/ws_manager/broadcasted_command"
        self.message_callback_add(broadcast_topic, callbacks.on_broadcast)
        self.subscribe(broadcast_topic)

        timer_topic = "/ws_manager/timer"
        self.message_callback_add(timer_topic, callbacks.on_timer)
        self.subscribe(timer_topic)


    def publish(self, topic, payload=None, qos=1, retain=False, properties=None):
        try:
            self.client.publish(topic, payload, qos, retain, properties)
        except Exception as exc:
            raise

    def subscribe(self, topic, qos=1, options=None, properties=None):
        try:
            self.client.subscribe(topic, qos, options, properties)
        except Exception as exc:
            raise

    def message_callback_add(self, sub, callback):
        # Wrap the callback to include 'self' as context
        wrapped_callback = lambda client, userdata, message: callback(client, userdata, message, self)
        try:
            self.client.message_callback_add(sub, wrapped_callback)
        except Exception as exc:
            raise

    # Callback when the client disconnects from the broker
    def on_disconnect(self, client, userdata, rc):
        '''
        Callback for when the client disconnects from the broker
        '''
        if rc != 0:
            print("Unexpected disconnection.")
        # Attempt to reconnect
        print("Trying to reconnect...")
        while True:
            try:
                self.client.reconnect()
                print("Reconnected successfully.")
                break
            except Exception as e:
                print(f"Reconnect failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)
    
    def reconnect(self):
        # Attempt to reconnect to the MQTT broker
        try:
            self.client.reconnect()
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5) 

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

        


class Local_MQTT_Handler_Workstations(Local_MQTT_Handler):
    def __init__(self, workstation_instance) -> None:
        super().__init__()
        self.upper_class_instance = workstation_instance
    
    def subscribe_to_topics(self):
        super().subscribe_to_topics()
        set_assembly_type_topic = "/ws_manager/set_assembly_type"
        self.message_callback_add(set_assembly_type_topic, callbacks.on_set_assembly_type)
        self.subscribe(set_assembly_type_topic)

        identify_topic = "/ws_manager/identify"
        self.message_callback_add(identify_topic, callbacks.on_identify)
        self.subscribe(identify_topic)

        set_ws_id_response_topic = "/ws_manager/set_ws_id_response"
        self.message_callback_add(set_ws_id_response_topic, callbacks.on_set_ws_id_response_topic)
        self.subscribe(set_ws_id_response_topic)

        disable_workstation_topic = '/ws_manager/disable_workstation'
        self.message_callback_add(disable_workstation_topic, callbacks.on_disable_workstation)
        self.subscribe(disable_workstation_topic)


        



class Local_MQTT_Handler_Inventory(Local_MQTT_Handler):
    def __init__(self, inventory_instance) -> None:
        super().__init__()
        super().subscribe_to_topics()
        self.upper_class_instance = inventory_instance

        topic = '/ws_manager/#'
        self.message_callback_add(topic, callbacks.on_wildcard_topic)
        self.subscribe(topic)
        

        order_topic = "/ws_manager/orders"
        self.message_callback_add(order_topic, callbacks.on_order)
        self.subscribe(order_topic)

        order_topic = "/ws_manager/update_order"
        self.message_callback_add(order_topic, callbacks.update_order)
        self.subscribe(order_topic)
        
        help_topic = "/ws_manager/help_request"
        self.message_callback_add(help_topic, callbacks.on_help)
        self.subscribe(help_topic)

        set_ws_id_topic = "/ws_manager/set_ws_id"
        self.message_callback_add(set_ws_id_topic, callbacks.on_set_ws_id)
        self.subscribe(set_ws_id_topic)

        set_ws_info_topic = "/ws_manager/set_ws_info"
        self.message_callback_add(set_ws_info_topic, callbacks.on_set_ws_info)
        self.subscribe(set_ws_info_topic)

        remaining_seconds_topic = "/ws_manager/remaining_seconds"
        self.message_callback_add(remaining_seconds_topic, callbacks.on_remaining_seconds)
        self.subscribe(remaining_seconds_topic)

        order_from_previous_ws_topic = "/ws_manager/order_from_previous_ws"
        self.message_callback_add(order_from_previous_ws_topic, callbacks.on_order_from_previous_ws)
        self.subscribe(order_from_previous_ws_topic)

        order_for_next_ws_topic = "/ws_manager/order_for_next_ws"
        self.message_callback_add(order_for_next_ws_topic, callbacks.on_order_for_next_ws)
        self.subscribe(order_for_next_ws_topic)
        
        manual_state_topic = "/ws_manager/manual_state"
        self.message_callback_add(manual_state_topic, callbacks.on_manual_state)
        self.subscribe(manual_state_topic)
        
        

    