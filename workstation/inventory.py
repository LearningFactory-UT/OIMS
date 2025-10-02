###### DEPRECATED ######
### This module inventory.py has been rewritten in javascript and 
### it is now running on the ThinkStation (http://rtlsserver.local)


import math
import customtkinter as ctk
import json
import mqtt
import callbacks
from timer import TimerApp
from datetime import datetime
from utils import ITEMS #, generate_csv, save_state_to_csv
from order import Order
from scrollable import ScrollableLabelButtonFrame
# from workstation_widget import WorkstationWidget
from bidict import bidict
import pygame
import time
import threading
from PIL import Image
# from gantt_chart import generate_charts

# TODO: ADD method to request for pending orders when session starts

class Inventory(ctk.CTk):

    def __init__(self, ws_id):
        super().__init__()

        self.lock_set_ws_id = threading.Lock()
        self.lock_set_ws_info = threading.Lock()

        self.stringvars = []

        self.ws_id = ws_id
        self.original_ws_id = ws_id

        # self.csv_file_path = None

        # self.orders_dict, self.past_orders_dict = {'order_id': Order}
        self.orders_dict = {}
        self.past_orders_dict = {}
        # self.ws_already_active_dict = {original_ws_id: {side: True|False}}
        self.ws_already_active_dict = {}

        # self.help_requests_dict = {help_id: {'original_ws_id':original_ws_id, 'side':side, 'help': True|False, 'idle': True|False}}
        self.help_requests_dict = {} 
        
        # self.order_from_prev_ws_dict = {prev_ws_order_id: {'original_ws_id':original_ws_id, 'side': side, 'pending': True|False, 'idle': True|False}}
        self.order_from_prev_ws_dict = {}

        # self.order_for_next_ws_dict = {ready_for_next_id: {'original_ws_id':original_ws_id, 'side': side, 'ready': True|False}}
        self.order_for_next_ws_dict = {}

        # self.ws_stop_dict[original_ws_id][side] = True
        self.ws_stop_dict = {}

        # self.ws_id_dict = {original_ws_id: ws_id}
        self.ws_id_dict = bidict({self.original_ws_id: ws_id})
        
        # self.ws_representations_dict = {original_ws_id: WorkstationWidget}
        # self.ws_representations_dict = {}
        self.assembly_type = "standard" # or 'simplified'

        # Create the timer
        self.timer_text = ctk.StringVar()
        self.timer_app = TimerApp(self, self.timer_text)

        # Set overall appearance
        ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # For Windows with specific resolution, manually set size and position
        # if screen_width == 1920 and screen_height == 1200:
        self.geometry(f'{screen_width}x{screen_height}+0+0')
        #self.config(cursor='none')

        self.mqtt_handler = mqtt.Local_MQTT_Handler_Inventory(self)


        # callbacks.instanciate_local_inventory_obj(self)

        self.create_widgets()


    def graceful_termination(self):
        self.mqtt_handler.publish(topic='/ws_manager/update_lights', payload=json.dumps({'original_ws_id':'ALL', 'side':'ALL', 'image_name':''}))
        self.mqtt_handler.stop()
        pygame.quit()

    ###########################################################
    ##################### WIDGETS METHODS #####################
    def create_widgets(self):

        ########## GENERAL CONFIGURATION ##########
        
        # Configure grid columns
        self.grid_columnconfigure(0, weight=1)
        # self.grid_columnconfigure(0, weight=0)
        # self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.top_row_font = ctk.CTkFont(weight='bold', size=30)
        self.standard_font = ctk.CTkFont(weight='bold', size=20)
        self.small_font = ctk.CTkFont(size=20)


        # Instanciate now the two frames so that they can be checked for None to remove buttons.
        # TODO: maybe find a better way, this doesnt seem elegant
        self.scrollable_label_button_frame_L = None
        self.scrollable_label_button_frame_R = None
        
        ########## TOP FRAME ##########

        # Create and place the top row with informations
        top_info_frame = ctk.CTkFrame(master=self)
        top_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.image = ctk.CTkImage(Image.open('images/logo.png'), size=(119,45))
        self.image_label = ctk.CTkLabel(master=top_info_frame, text='', image=self.image)
        self.image_label.pack(side='left', padx=(30,50), pady=0)

        station_number_label = ctk.CTkLabel(master=top_info_frame, text=f'Inventory', font=self.top_row_font)
        station_number_label.pack(side='left', padx=50, pady=20)
        
        # Start the clock
        self.time_text = ctk.StringVar()
        self.stringvars.append(self.time_text)
        self.update_stringvars()

        settings_button = ctk.CTkButton(master=top_info_frame, text="Settings", height=40, width=50, command=self.settings_callback, font=self.standard_font)
        settings_button.pack(side="right", padx=25, pady=15)

        self.time_label = ctk.CTkLabel(master=top_info_frame, textvariable=self.time_text, font=self.top_row_font)
        self.time_label.pack(side='left', padx = 50, pady=10)
        #self.time_label.grid(row=0, column=1, sticky='ew', padx = 50, pady=30)

        self.timer_label = ctk.CTkLabel(master=top_info_frame, textvariable=self.timer_text, font=self.top_row_font)
        self.timer_label.pack(side='right', padx = 50, pady=10)


        ########## LEFT FRAME ##########

        # Create frame
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=1, column=0, sticky="nsew")

        # Configure grid rows for left frame
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=1)
        

        ########## LEFT-TOP FRAME ##########

        
        # Split the left frame into top and bottom
        self.left_top_frame = ctk.CTkFrame(self.left_frame)
        # Layout for top and bottom frames
        self.left_top_frame.grid(row=0, column=0, sticky="nsew")

        self.urgent_orders_title = ctk.CTkLabel(master=self.left_top_frame, text='URGENT ORDERS', font=self.top_row_font)
        self.urgent_orders_title.pack(side='top', anchor='w', pady=10, padx=20)
        
        self.scrollable_label_button_frame_top = ScrollableLabelButtonFrame(master=self.left_top_frame, detail_command=self.show_order_details, corner_radius=0)
        self.scrollable_label_button_frame_top.pack(fill='both', expand=True, pady=10, padx=10)

        ########## LEFT-BOTTOM FRAME ##########

        # Split the left frame into top and bottom
        self.left_bottom_frame = ctk.CTkFrame(self.left_frame)
        # Layout for top and bottom frames
        self.left_bottom_frame.grid(row=1, column=0, sticky="nsew")
        
        self.standard_orders_title = ctk.CTkLabel(master=self.left_bottom_frame, text='STANDARD ORDERS', font=self.top_row_font)
        self.standard_orders_title.pack(side='top', anchor='w', pady=10, padx=20)
        
        self.scrollable_label_button_frame_bottom = ScrollableLabelButtonFrame(master=self.left_bottom_frame, detail_command=self.show_order_details, corner_radius=0)
        self.scrollable_label_button_frame_bottom.pack(fill='both', expand=True, pady=10, padx=10)
        

        # Once all widgets are created, publish the identify message
        self.mqtt_handler.publish(topic="/ws_manager/identify")


    def set_ws_info(self, info_dict):
        with self.lock_set_ws_id:
            # when new ws connects and timer is running, send command to start the timer
            if self.timer_app.remaining_seconds.total_seconds() > 0 and self.timer_app.timer_running:
                self.start_timer_callback(autostart=True, seconds=self.timer_app.remaining_seconds.total_seconds())

            '''info_dict = {
                'ws_id':self.ws_id, 
                'original_ws_id':self.original_ws_id, 
                'pending_orders':self.orders_dict,
                'pending_help':self.pending_help
                'pending_order_from_previous_ws': self.pending_order_from_previous_ws
            }'''
            # print(info_dict)
            print(f'receiving info_dict from ws {info_dict["ws_id"]}')

            original_ws_id = info_dict['original_ws_id']
            for order_id, order_info in info_dict['pending_orders'].items():
                # Convert 'creation_time' from string to datetime
                order_info['creation_time'] = datetime.fromisoformat(order_info['creation_time'])
                
                # Convert 'label_text' from string to ctk.StringVar (or similar)
                order_info['label_text'] = ctk.StringVar(value=order_info['label_text'])
                
                # Order instance 
                order = Order(**order_info)
                
                # Add the order to your orders dictionary
                self.orders_dict[order_id] = order
                if order.urgent:
                    self.scrollable_label_button_frame_top.add_item(order_id, order.label_text)
                else:
                    self.scrollable_label_button_frame_bottom.add_item(order_id, order.label_text)
                
            # Initialize the key for the ws_already_active dictionary
            self.ws_already_active_dict[original_ws_id] = {}
            for side in ['L', 'R']:
                self.ws_already_active_dict[original_ws_id][side] = False

            # self.help_requests_dict = {help_id: {'original_ws_id':original_ws_id, 'side':side, 'idle': True|False, 'creation_time':Datetime object}}

            #pending_help = {side: {'help_id':help_id, 'idle':idle, 'creation_time':datetime.now()}}
            for side, help_dict in info_dict['pending_help'].items():
                if help_dict is not None:
                    self.help_requests_dict[help_dict['help_id']] = {}
                    self.help_requests_dict[help_dict['help_id']]['original_ws_id'] = original_ws_id
                    self.help_requests_dict[help_dict['help_id']]['side'] = side
                    self.help_requests_dict[help_dict['help_id']]['creation_time'] = datetime.fromisoformat(help_dict['creation_time'])
                    self.help_requests_dict[help_dict['help_id']]['idle'] = help_dict['idle']

            #pending_help = {side: {'help_id':help_id, 'idle':idle, 'creation_time':datetime.now()}}
            for side, order_from_prev_ws_dict in info_dict['pending_order_from_previous_ws'].items():
                if order_from_prev_ws_dict is not None:
                    self.order_from_prev_ws_dict[order_from_prev_ws_dict['prev_ws_order_id']] = {}
                    self.order_from_prev_ws_dict[order_from_prev_ws_dict['prev_ws_order_id']]['original_ws_id'] = original_ws_id
                    self.order_from_prev_ws_dict[order_from_prev_ws_dict['prev_ws_order_id']]['side'] = side
                    self.order_from_prev_ws_dict[order_from_prev_ws_dict['prev_ws_order_id']]['creation_time'] = datetime.fromisoformat(order_from_prev_ws_dict['creation_time'])
                    self.order_from_prev_ws_dict[order_from_prev_ws_dict['prev_ws_order_id']]['idle'] = order_from_prev_ws_dict['idle']

            # Update the ws representation on the current ws state
            self.update_ws_representation(original_ws_id)


    def manual_start_stop(self, original_ws_id, side, command):
        if command == 'start':
            self.ws_already_active_dict[original_ws_id][side] = True
            self.ws_stop_dict[original_ws_id][side] = False
        elif command =='stop':
            self.ws_stop_dict[original_ws_id][side] = True
        elif command == 'reset':
            self.ws_stop_dict[original_ws_id][side] = False

        self.update_ws_representation(original_ws_id)


    def update_ws_representation(self, original_ws_id, time_s_up=False):
        update_dicts = []

        if not time_s_up:
            # Define idle as false and if any urgency (urgency <-> inability to perform work) is found  
            # then this flag is set to True
            idle = {'L':False, 'R':False}

            ############### ORDERS ###############
            pending_order = {'L':False, 'R':False}

            pending_orders = []
            # Unpack global orders, if there are any from the current ws then save them in pending_orders
            for order in self.orders_dict.values():
                if order.original_ws_id == original_ws_id:
                    pending_orders.append(order)

            # If there were any orders from current ws, then perform check on details
            for order in pending_orders:
                # If an order is present, then the flag dict pending_order[L|R] is set to True (later used to turn on blue light)
                pending_order[order.side] = True 
                if order.urgent:
                    # If the order is also urgent, update the relative flag dict (later used to turn on the red light if True or green if False)
                    idle[order.side] = True
                
                # Mark as active until timer runs out - if there is an order then the ws is active
                self.ws_already_active_dict[original_ws_id][order.side] = True
            


            ############### HELP ###############
            # As a reference: self.help_requests_dict = {help_id: help_dict}
            # help_dict = {'original_ws_id':original_ws_id, 'side':side, 'help': True|False, 'idle': True|False, 'creation_time': Datetime object}
            help = {'L':False, 'R':False}
            
            pending_help = []
            # Unpack global help requests, if there are any from the current ws then save them in pending_help
            for help_request in self.help_requests_dict.values():
                if help_request['original_ws_id'] == original_ws_id:
                    pending_help.append(help_request)
            
            # If there were any help request from current ws, then perform check on details
            for help_request in pending_help:
                # If help request is present, then the flag dict help[L|R] is set to True (later used to turn on yellow light)
                help[help_request['side']] = True
                # If help request is urgent, update the relative flag dict (later used to turn on the red light if True or green if False)
                idle[help_request['side']] = help_request['idle']

                # Mark as active until timer runs out - if there is an help request then the ws is active
                self.ws_already_active_dict[original_ws_id][help_request['side']] = True

            
            ############### FROM PREVIOUS ###############
            order_from_prev = {'L':False, 'R':False}
            
            pending_order_from_prev_ws = []
            # Unpack global order_from_prev dict, if there are any pending order_from_prev for the current ws then save them in pending_order_from_prev_ws
            for order_from_prev_ws in self.order_from_prev_ws_dict.values():
                if order_from_prev_ws['original_ws_id'] == original_ws_id:
                    pending_order_from_prev_ws.append(order_from_prev_ws)

            # If there were any pending_order_from_prev_ws from current ws, then perform check on details
            for order_from_prev_ws in pending_order_from_prev_ws:
                # If any order_from_prev is present, then the flag dict order_from_prev[L|R] is set to True (later used to turn on blinking blue light)
                order_from_prev[order_from_prev_ws['side']] = True
                # If order_from_prev is urgent, update the relative flag dict (later used to turn on the red light if True or green if False)
                idle[order_from_prev_ws['side']] = order_from_prev_ws['idle']

                # Mark as active until timer runs out - if there is any order_from_prev then the ws is active    
                self.ws_already_active_dict[original_ws_id][order_from_prev_ws['side']] = True


            ############### TO NEXT ###############
            order_for_next = {'L':False, 'R':False}

            order_ready_for_next_ws = []
            # Unpack global order_for_next_ws dict, if the current ws has any order_for_next_ws ready then save this in order_ready_for_next_ws
            for ready_for_next_dict in self.order_for_next_ws_dict.values():
                if ready_for_next_dict['original_ws_id'] == original_ws_id:
                    order_ready_for_next_ws.append(ready_for_next_dict)
            
            # If the current ws has any order_for_next_ws, then perform check on details
            for ready_for_next_dict in order_ready_for_next_ws:
                # If any order_for_next_ws is present, then the flag dict order_for_next[L|R] is set to True (later used to turn on blinking green light)
                order_for_next[ready_for_next_dict['side']] = True

                # Mark as active until timer runs out - if there is any order_for_next_ws then the ws is active 
                self.ws_already_active_dict[original_ws_id][ready_for_next_dict['side']] = True
            
            
            #############################################
                
            # If timer is not running, set lights to red.
            if not self.timer_app.timer_running:
                idle['L'] = True
                idle['R'] = True
                help['L'] = False
                help['R'] = False
                order_from_prev['L'] = False
                order_from_prev['R'] = False
                order_for_next['L'] = False
                order_for_next['R'] = False
                pending_order['L'] = False
                pending_order['R'] = False
            
            color_string = {'L':'', 'R':''}
            for side in ['L', 'R']:
                if self.ws_already_active_dict[original_ws_id].get(side):
                    if idle[side] or self.ws_stop_dict[original_ws_id][side]:
                        color_string[side] = 'R'
                    else:
                        color_string[side] = 'G'

                    if order_for_next[side]:
                        color_string[side] += 'g'
                    
                    if help[side]:
                        color_string[side] += 'Y'
                    
                    if order_from_prev[side]:
                        color_string[side] += 'b'

                    if pending_order[side]:
                        color_string[side] += 'B'
                    
                    update_dicts.append({'side': side, 'image_name': color_string[side]})
                else:
                    color_string[side] = 'R'
                    update_dicts.append({'side': side, 'image_name': color_string[side]})
        else:
            for side in ['L', 'R']:
                update_dicts.append({'side': side, 'image_name': 'R'})

        print(f'update_dicts = {update_dicts}')
        print(f'original_ws_id = {original_ws_id}')
        for update_dict in update_dicts:
            # Update the andon lights
            payload = json.dumps({'original_ws_id':original_ws_id, 'side': update_dict['side'], 'image_name': update_dict['image_name']})
            self.mqtt_handler.publish(topic='/ws_manager/update_lights', payload=payload)

    def show_order_details(self, order_id):
        # Function to handle the "Delivered" action
        def delivered_action(window):
            # Remove the order from the list and destroy its button
            order_id_json = json.dumps({'order_id':order_id})
            self.mqtt_handler.publish(topic='/ws_manager/order_delivered', payload=order_id_json)
            
            window.destroy()

        # Function to handle the "Yet to Deliver" action
        def yet_to_deliver_action(window):
            # Implement the logic for when an order is not yet delivered
            print(f"Order {order_id} is yet to be delivered.")
            window.destroy()

        # Create the top-level window
        window = ctk.CTkToplevel(self, fg_color='#353535')
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width / 2) - (400 / 2)
        y = (screen_height / 2) - (400 / 2)
        window.geometry(f'400x400+{int(x)}+{int(y)}')
        #window.resizable(False, False)
        window.grid_columnconfigure((0, 1), weight=1)
        window.grid_rowconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=0)
        window.overrideredirect(True)
        window.wait_visibility()
        window.grab_set()

        # Display order details
        message = f"Order ID: {order_id}\n\n"

        print(self.orders_dict)
        for key, quantity in self.orders_dict[order_id].items_dict.items():
            message += f'{key}: {quantity}\n'

        
        message_label = ctk.CTkLabel(master=window, text=message)
        message_label.grid(row=0, column=0, columnspan=2, pady=(30, 15), padx=30, sticky='nsew')

        # Buttons for "Delivered" and "Yet to Deliver"
        delivered_button = ctk.CTkButton(master=window, text='Delivered', command=lambda: delivered_action(window), height=40, corner_radius=20)
        yet_to_deliver_button = ctk.CTkButton(master=window, text='Yet to Deliver', command=lambda: yet_to_deliver_action(window), height=40, corner_radius=20)
        delivered_button.grid(row=1, column=0, pady=(15, 30), padx=30, sticky='w')
        yet_to_deliver_button.grid(row=1, column=1, pady=(15, 30), padx=30, sticky='e')

        window.wait_window()  # Wait until the dialog window is closed

    ##################### WIDGETS METHODS #####################
    ###########################################################
        
    ################################################################
    ##################### TIME & TIMER METHODS #####################
    

    def start_timer_callback(self, autostart=False, seconds=None):
        print('Start timer callback function')
        if not autostart:
            seconds = self.ask_timer_lenght()
            start_sound_thread = threading.Thread(target=lambda: self.play_sound('start'))
            start_sound_thread.start()
            print(seconds)
        
        if seconds:
            payload = json.dumps({'command':'start', 'seconds':seconds, 'initiator':'inventory'})
            self.mqtt_handler.publish(topic='/ws_manager/timer', payload=payload)
        

    def ask_timer_lenght(self):
        total_seconds = None
        def cancel_action(window):
            window.destroy()

        def save_action(window, minutes, seconds):
            nonlocal total_seconds
            total_seconds = int(minutes) * 60 + int(seconds)
            window.destroy()

        # Create the top-level window
        window = ctk.CTkToplevel(self, fg_color='#353535')
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_width = 400
        window_height = 300
        x = (screen_width / 2) - (window_width / 2)
        y = (screen_height / 2) - (window_height / 2)
        window.geometry(f'{window_width}x{window_height}+{int(x)}+{int(y)}')
        #window.resizable(False, False)
        window.grid_columnconfigure((0, 1), weight=1)
        window.grid_rowconfigure((0, 1, 2, 3), weight=1)
        window.overrideredirect(True)
        window.wait_visibility()
        window.grab_set()



        name_label = ctk.CTkLabel(master=window, text="Set timer")
        name_label.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='s')
        
        
        # Variable for the CTkEntry widget (text field)
        minutes = 15
        seconds = 0

        minutes_entry = ctk.CTkEntry(window, textvariable=ctk.StringVar(value=minutes))
        minutes_entry.grid(row=1, column=0, padx=10, pady=10, sticky='e')
        minute_label = ctk.CTkLabel(master=window, text="Minutes")
        minute_label.grid(row=1, column=1, pady=10, padx=10, sticky='w')

        seconds_entry = ctk.CTkEntry(window, textvariable=ctk.StringVar(value=seconds))
        seconds_entry.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        seconds_label = ctk.CTkLabel(master=window, text="Seconds")
        seconds_label.grid(row=2, column=1, pady=10, padx=10, sticky='w')

        cancel_button = ctk.CTkButton(master=window, text='Cancel', command=lambda: cancel_action(window), height=40, corner_radius=20)
        save_button = ctk.CTkButton(master=window, text=f'Start', command=lambda: save_action(window, minutes_entry.get(), seconds_entry.get()), height=40, corner_radius=20)
       
        cancel_button.grid(row=3, column=0, pady=(15, 30), padx=30, sticky='ew')
        save_button.grid(row=3, column=1, pady=(15, 30), padx=30, sticky='ew')

        window.wait_window()  # Wait until the dialog window is closed

        return total_seconds


    def stop_timer_callback(self):
        payload = json.dumps({'command':'stop'})
        self.mqtt_handler.publish(topic='/ws_manager/timer', payload=payload)

        # Save start time to csv as red light and turn on andon red light.
        for original_ws_id, ws_id in self.ws_id_dict.items():
            # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for side in ['L', 'R']:
                payload = json.dumps({'original_ws_id':original_ws_id, 'side': side, 'image_name': 'R'})
                self.mqtt_handler.publish(topic='/ws_manager/update_lights', payload=payload)
                        
    
    def pause_timer_callback(self):
        payload = json.dumps({'command':'pause'})
        self.mqtt_handler.publish(topic='/ws_manager/timer', payload=payload)
    

    def resume_timer_callback(self):
        payload = json.dumps({'command':'resume'})
        self.mqtt_handler.publish(topic='/ws_manager/timer', payload=payload)


    def timer_end(self):
        order_ids = list(self.orders_dict.keys())
        while self.orders_dict:
            self.remove_order(order_ids.pop(0), reason="timer")
        
        for original_ws_id in self.ws_id_dict.keys():
            self.update_ws_representation(original_ws_id, time_s_up=True)
            
            # self.ws_already_active_dict = {original_ws_id: {side: True|False}}
            self.ws_already_active_dict[original_ws_id] = {}
            for side in ['L', 'R']:
                self.ws_already_active_dict[original_ws_id][side] = False
        
        # Start new thread to avoid program halting when playing the sound
        end_sound_thread = threading.Thread(target=lambda: self.play_sound('end'))
        end_sound_thread.start()


    def play_sound(self, sound):
        pygame.mixer.init()
        sound = pygame.mixer.Sound(f"sounds/{sound}.mp3")
        sound.play()
        # Sleep to prevent the thread from ending too soon
        time.sleep(sound.get_length())


    ##################### TIME & TIMER METHODS #####################
    ################################################################
    

    ##############################################################
    ################# ORDER MODIFICATION METHODS #################
    def remove_order(self, order_id, reason):
        # Implement the logic to remove the order from the list and destroy its button
        # self.orders_dict[order_id].button.destroy()
        if self.orders_dict.get(order_id):
            original_ws_id = self.orders_dict[order_id].original_ws_id
        else:
            self.update_ws_representation(original_ws_id)
            return

        if self.orders_dict[order_id].urgent:
            self.scrollable_label_button_frame_top.remove_item(order_id)
        else:
            self.scrollable_label_button_frame_bottom.remove_item(order_id)

        side = self.orders_dict[order_id].side
        if side == 'L':
            # short-circuit evaluation to prevent winfo_ismapped() to be called on a None object.
            if self.scrollable_label_button_frame_L is not None and self.scrollable_label_button_frame_L.winfo_ismapped(): 
                self.scrollable_label_button_frame_L.remove_item(order_id)
        else:
            if self.scrollable_label_button_frame_R is not None and self.scrollable_label_button_frame_R.winfo_ismapped(): 
                self.scrollable_label_button_frame_R.remove_item(order_id)

        self.past_orders_dict[order_id] = self.orders_dict.pop(order_id)
        self.past_orders_dict[order_id].end_time = datetime.now()
        self.past_orders_dict[order_id].end_reason = reason

        self.update_ws_representation(original_ws_id)
        
    
    def add_order(self, order_dict):
        items_dict = order_dict['items']
            
        order_dict = order_dict['attributes']

        order_id = order_dict['order_id']
        ws_id = order_dict['ws_id']
        side = order_dict['operator_side']
        urgent = order_dict['urgent']

        label_text = ctk.StringVar()
        
        if urgent:
            self.scrollable_label_button_frame_top.add_item(order_id, label_text)
        else:
            self.scrollable_label_button_frame_bottom.add_item(order_id, label_text)

        # Search for the key (original_ws_id) given the value (ws_id)
        original_ws_id = self.ws_id_dict.inverse[ws_id]
        #order = Order(order_id, ws_id, side, button, datetime.now(), label_text, urgent, items_dict)
        order = Order(order_id, original_ws_id, ws_id, side, datetime.now(), label_text, urgent, items_dict)
        # self.orders.append(order)
        self.orders_dict[order_id] = order
        self.update_order_label(self.orders_dict[order_id])

        self.update_ws_representation(original_ws_id)


    def update_order(self, update_order_dict):
        # update_order_dict in the form of {'urgent': True, 'order_id': order_id}
        order_id = update_order_dict['order_id']
        urgent = update_order_dict['urgent']

        if self.orders_dict[order_id].urgent != urgent:
            
            if self.orders_dict[order_id].urgent:
                self.scrollable_label_button_frame_top.remove_item(order_id)
                self.scrollable_label_button_frame_bottom.add_item(order_id, self.orders_dict[order_id].label_text)
            else:
                self.scrollable_label_button_frame_bottom.remove_item(order_id)
                self.scrollable_label_button_frame_top.add_item(order_id, self.orders_dict[order_id].label_text)
            
            self.orders_dict[order_id].urgent = urgent

            # Redraw the frame
            self.left_top_frame.update()
            self.left_bottom_frame.update()
        
        original_ws_id = self.orders_dict[order_id].original_ws_id
        self.update_ws_representation(original_ws_id)


        print('ORDER UPDATED')

    ################# ORDER MODIFICATION METHODS #################
    ##############################################################
        

    ##################################################
    ################# UPDATE METHODS #################
    def update_order_label(self, order):
        #print(order)
        elapsed_time = datetime.now() - order.creation_time
        elapsed_seconds = int(elapsed_time.total_seconds())

        hours = elapsed_seconds // 3600
        minutes = (elapsed_seconds % 3600) // 60
        seconds = elapsed_seconds % 60

        # Format the time string based on the elapsed time
        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        label = f"{order.ws_id} {order.side} - {time_str}  "
        
        for item, quantity in order.items_dict.items():
            label += f"|  {item} {quantity}  "
        
        label += "|"

        order.label_text.set(label)


    def update_stringvars(self):
        self.update_time()

        for key, order in self.orders_dict.items():
            self.update_order_label(order)


        self.after(500, self.update_stringvars)

    
    def update_help(self, help_dict):
        # help_dict = {'help_id':help_id, 'ws_id':self.ws_id, 'side':side, 'help': True|False, 'idle': True|False}
        # self.help_requests_dict = {help_id: {'help_id':help_id, 'original_ws_id':original_ws_id, 'side':side, 'help': True|False, 'idle': True|False}}

        help_id = help_dict.pop('help_id')

        # substitute ws_id with the original_ws_id
        ws_id = help_dict.pop('ws_id')
        original_ws_id = self.ws_id_dict.inverse[ws_id]
        help_dict['original_ws_id'] = original_ws_id

        if help_dict['help']:
            # Save the updated help_dict to the dictionary
            self.help_requests_dict[help_id] = help_dict
        else:
            help_id_to_remove = []
            for saved_help_id, help_request in self.help_requests_dict.items():
                if help_request['original_ws_id'] == original_ws_id and help_request['side'] == help_dict['side']:
                    help_id_to_remove.append(saved_help_id)
        
            for help_id in help_id_to_remove:
                self.help_requests_dict.pop(help_id)


        self.update_ws_representation(original_ws_id)


    def update_order_from_prev_ws(self, prev_ws_order_dict):
        # prev_ws_order_dict = {'prev_ws_order_id': prev_ws_order_id, 'ws_id': self.ws_id, 'side': side, 'pending': True, 'idle': True}
        # self.order_from_prev_ws_dict = {original_ws_id: prev_ws_order_dict}

        prev_ws_order_id = prev_ws_order_dict.pop('prev_ws_order_id')

        # substitute ws_id with the original_ws_id
        ws_id = prev_ws_order_dict.pop('ws_id')
        original_ws_id = self.ws_id_dict.inverse[ws_id]
        prev_ws_order_dict['original_ws_id'] = original_ws_id

        if prev_ws_order_dict['pending']:
            # Save the updated prev_ws_order_dict to the dictionary
            self.order_from_prev_ws_dict[prev_ws_order_id] = prev_ws_order_dict
        else:
            prev_ws_order_id_to_remove = []
            for saved_prev_ws_order_id, saved_order_from_prev_ws in self.order_from_prev_ws_dict.items():
                if saved_order_from_prev_ws['original_ws_id'] == original_ws_id and saved_order_from_prev_ws['side'] == prev_ws_order_dict['side']:
                    prev_ws_order_id_to_remove.append(saved_prev_ws_order_id)
        
            for prev_ws_order_id in prev_ws_order_id_to_remove:
                self.order_from_prev_ws_dict.pop(prev_ws_order_id)


        self.update_ws_representation(original_ws_id)

    
    def update_order_for_next_ws(self, ready_for_next_dict):
        # ready_for_next_dict = {'ready_for_next_id': ready_for_next_id, 'ws_id': self.ws_id, 'side': side, 'ready': True}

        ready_for_next_id = ready_for_next_dict.pop('ready_for_next_id')

        # substitute ws_id with the original_ws_id
        ws_id = ready_for_next_dict.pop('ws_id')
        original_ws_id = self.ws_id_dict.inverse[ws_id]
        ready_for_next_dict['original_ws_id'] = original_ws_id

        if ready_for_next_dict['ready']:
            # Save the updated prev_ws_order_dict to the dictionary
            self.order_for_next_ws_dict[ready_for_next_id] = ready_for_next_dict
        else:
            ready_for_next_id_to_remove = []
            for saved_ready_for_next_id, saved_ready_for_next_dict in self.order_for_next_ws_dict.items():
                if saved_ready_for_next_dict['original_ws_id'] == original_ws_id and saved_ready_for_next_dict['side'] == ready_for_next_dict['side']:
                    ready_for_next_id_to_remove.append(saved_ready_for_next_id)
        
            for ready_for_next_id in ready_for_next_id_to_remove:
                self.order_for_next_ws_dict.pop(ready_for_next_id)


        self.update_ws_representation(original_ws_id)


    def update_time(self):
        current_time = datetime.now()
        time_string = current_time.strftime('%H:%M:%S')
        self.time_text.set(time_string)
   
    ################# UPDATE METHODS #################
    ##################################################
        

    def set_ws_id(self, original_ws_id, ws_id):
        with self.lock_set_ws_id:
            if ws_id in self.ws_id_dict.values() or ws_id == '':
                # Refuse renaming of ws_id
                payload = json.dumps({"original_ws_id":original_ws_id, "ws_id":False})
                self.mqtt_handler.publish(topic="/ws_manager/set_ws_id_response", payload=payload)
                return
            
            self.ws_id_dict[original_ws_id] = ws_id
            self.ws_stop_dict[original_ws_id] = {'L':False, 'R':False}


            # Accept renaming of ws_id
            payload = json.dumps({"original_ws_id":original_ws_id, "ws_id":ws_id})
            self.mqtt_handler.publish(topic="/ws_manager/set_ws_id_response", payload=payload)

            print(f'################################')
            print(f'##         ADDED WS {original_ws_id}         ##')
            print(f'################################')


    def settings_callback(self):

        def cancel_action(window):
            window.destroy()

        def save_action(window, selected_assembly):
            window.destroy()

            self.assembly_type = selected_assembly.get()

            json_payload = json.dumps({"assembly_type": self.assembly_type})
            
            self.mqtt_handler.publish(topic='/ws_manager/set_assembly_type', payload=json_payload)

        # Create the top-level window
        window = ctk.CTkToplevel(self, fg_color='#353535')
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_width = 400
        window_height = 300
        x = (screen_width / 2) - (window_width / 2)
        y = (screen_height / 2) - (window_height / 2)
        window.geometry(f'{window_width}x{window_height}+{int(x)}+{int(y)}')
        #window.resizable(False, False)
        window.grid_columnconfigure((0, 1), weight=0)
        window.grid_rowconfigure((0, 1, 2), weight=0)
        window.overrideredirect(True)
        window.wait_visibility()
        window.grab_set()

        # Variable to hold the value of the selected radio button
        selected_assembly = ctk.StringVar(value=self.assembly_type)

        # Create the "Standard assembly" radio button
        standard_assembly_rb = ctk.CTkRadioButton(window, text="Standard assembly", variable=selected_assembly, value="standard")
        standard_assembly_rb.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Create the "Simplified assembly" radio button
        simplified_assembly_rb = ctk.CTkRadioButton(window, text="Simplified assembly", variable=selected_assembly, value="simplified")
        simplified_assembly_rb.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        cancel_button = ctk.CTkButton(master=window, text='Cancel', command=lambda: cancel_action(window), height=40, corner_radius=20)
        save_button = ctk.CTkButton(master=window, text=f'Save', command=lambda: save_action(window, selected_assembly), height=40, corner_radius=20)
       
        cancel_button.grid(row=2, column=0, pady=(15, 30), padx=30, sticky='ew')
        save_button.grid(row=2, column=1, pady=(15, 30), padx=30, sticky='ew')

        window.wait_window()  # Wait until the dialog window is closed


    def clean_window(self):
        for widget in self.winfo_children():
            widget.grid_forget()  
        
     
    def enable_workstation(self, original_ws_ids=None):
        # Turn on andon red lights
        for original_ws_id, ws_id in self.ws_id_dict.items():
            for side in ['L', 'R']:
                payload = json.dumps({'original_ws_id':original_ws_id, 'side': side, 'image_name': 'R'})
                self.mqtt_handler.publish(topic='/ws_manager/update_lights', payload=payload)

    def disable_workstation(self, original_ws_ids=None):
        # placeholder
        pass


def main():
    # Load the config.json file
    ws_id = 'Inventory'
    app = Inventory(ws_id)
    app.mainloop()
    app.graceful_termination()

if __name__ == "__main__":
    main()


