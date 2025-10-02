import json
from timer import TimerApp
from datetime import timedelta

local_timer:TimerApp = None
# local_inventory_obj:Inventory = None

# def instanciate_local_timer_obj(timer_obj: TimerApp):
#     global local_timer
#     local_timer = timer_obj

# def instanciate_local_inventory_obj(inventory_obj: Inventory):
#     global local_inventory_obj
#     local_inventory_obj = inventory_obj

def update_order(client, userdata, message, context):
    update_order_dict = json.loads(message.payload)
    print(update_order_dict)
    # local_inventory_obj.update_order(update_order_dict)
    context.upper_class_instance.update_order(update_order_dict)


## Main Callback for messages on topic: '/rpi/broadcast_command'
    
def on_wildcard_topic(client, userdata, message, context):
    print(message.topic)

def on_broadcast(client, userdata, message, context):

    # expecting messages ot type {'command': value, 'content': value}
    command_dict = json.loads(message.payload)
    print(command_dict)
    command = command_dict['command']
    content = command_dict.get('content')

    if command == '':
        pass
    else:
        print('Command not supported')


def on_order(client, userdata, message, context):
    # order is gonna be a dict {'ws_id': int, 'operator_side': 'L'or'R', 'Battery': int, 'Board Screw': int, 'Bumper': int, 'C-CW Prop': int, 'Camera Board': int, 'Camera Housing': int, 'Camera Screw': int, 'Control Board': int, 'CW Prop': int, 'Drone Frame': int, 'Motor Jig': int, 'Motor Screw': int, 'Motor': int}
    order_dict = json.loads(message.payload)
    context.upper_class_instance.add_order(order_dict)
    # local_inventory_obj.add_order(order_dict)
    print(order_dict)
    
def on_update_ws_id(client, userdata, message, context):
    # TODO: called when publishing a message on topic: '/ws_manager/update_ws_id'
    pass

def on_help(client, userdata, message, context):
    # help_dict = {'ws_id':self.ws_id, 'side':side, 'help': True|False, 'idle': True|False}
    help_dict = json.loads(message.payload)
    context.upper_class_instance.update_help(help_dict)


def on_order_from_previous_ws(client, userdata, message, context):
    prev_ws_order_dict = json.loads(message.payload)
    context.upper_class_instance.update_order_from_prev_ws(prev_ws_order_dict)

def on_order_for_next_ws(client, userdata, message, context):
    ready_for_next_dict = json.loads(message.payload)
    context.upper_class_instance.update_order_for_next_ws(ready_for_next_dict)

def on_timer(client, userdata, message, context):
    global local_timer

    print(message.payload)

    # expecting messages of type {"command": "stop"|"pause"|"resume"} or {"command":"start", "seconds":int}
    
    command_dict = json.loads(message.payload)
    print(command_dict)
    command = command_dict['command']

    
    if command == 'start':
        seconds = command_dict['seconds']
        context.upper_class_instance.timer_app.start_timer(seconds)
        # local_timer.start_timer(seconds)
        # print('timer started')
    elif command == 'stop':
        context.upper_class_instance.timer_app.stop_timer()
        # local_timer.stop_timer()
        print('timer stopped')
    elif command == 'pause':
        context.upper_class_instance.timer_app.pause_timer()
        # local_timer.pause_timer()
        print('timer paused')
    elif command == 'resume':
        context.upper_class_instance.timer_app.resume_timer()        
        # local_timer.resume_timer()        
        print('timer resumed')
    else:
        print('Expected message of type {"command": "stop"|"pause"|"resume"} or {"command":"start", "seconds":int}')


# Modified callback to accept a context parameter
def on_order_delivered(client, userdata, message, context):
    message_dict = json.loads(message.payload)
    order_id = message_dict['order_id']
    context.upper_class_instance.remove_order(order_id, reason='delivered')

def on_delete_order(client, userdata, message, context):
    message_dict = json.loads(message.payload)
    order_id = message_dict['order_id']
    context.upper_class_instance.remove_order(order_id, reason='deleted')


def on_set_assembly_type(client, userdata, message, context):
    message_dict = json.loads(message.payload)
    assembly_type = message_dict['assembly_type']
    context.upper_class_instance.set_assembly_type(assembly_type)


def on_set_ws_id(client, userdata, message, context):
    # {'ws_id':self.ws_id, 'original_ws_id':self.original_ws_id}
    message_dict = json.loads(message.payload)
    ws_id = message_dict['ws_id']
    original_ws_id = message_dict['original_ws_id']

    context.upper_class_instance.set_ws_id(original_ws_id, ws_id)


def on_identify(client, userdata, message, context):
    context.upper_class_instance.send_ws_id()
    context.upper_class_instance.send_ws_info()

def on_remaining_seconds(client, userdata, message, context):
    payload = json.loads(message.payload)
    remaining_seconds = payload['remaining_seconds']
    context.upper_class_instance.timer_app.remaining_seconds = timedelta(seconds=remaining_seconds)



def on_set_ws_id_response_topic(client, userdata, message, context):
    ws_id = json.loads(message.payload)['ws_id']
    original_ws_id = json.loads(message.payload)['original_ws_id']

    context.upper_class_instance.update_ws_id(original_ws_id, ws_id)


def on_set_ws_info(client, userdata, message, context):
    info_dict = json.loads(message.payload)
    context.upper_class_instance.set_ws_info(info_dict)

def on_disable_workstation(client, userdata, message, context):
    message_dict = json.loads(message.payload)
    original_ws_ids = message_dict['original_ws_ids']
    context.upper_class_instance.disable_workstation(original_ws_ids)

def on_manual_state(client, userdata, message, context):
    message_dict = json.loads(message.payload)

    # message_dict = {'original_ws_id':self.original_ws_id, 'side':side, 'manual_command':'stop'}
    original_ws_id = message_dict['original_ws_id']
    side = message_dict['side']
    command = message_dict['manual_command']
    context.upper_class_instance.manual_start_stop(original_ws_id, side, command)