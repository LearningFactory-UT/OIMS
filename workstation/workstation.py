import json
from math import ceil
import threading
from spinbox import Spinbox
import customtkinter as ctk
import mqtt as mqtt
from datetime import datetime, timedelta
import time
from timer import TimerApp
from scrollable import ScrollableLabelButtonFrame
from utils import generate_id, generate_help_id, ITEMS
from order import Order, HelpRequest
import pygame
from PIL import Image
# from PIL import Image
# from dataclasses import dataclass
# from tkinter import Tk, PhotoImage
# import callbacks


order_ids = {'L':[], 'R':[]}

# TODO: allow for stations with single operator


# Now drone_items is a list of DroneItem objects with the names from the items dictionary.

class Client(ctk.CTk):
    def __init__(self, ws_id):

        # Create the main window
        super().__init__()

        # Set overall appearance
        ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # For Windows with specific resolution, manually set size and position
        # if screen_width == 1920 and screen_height == 1200:
        self.geometry(f'{screen_width}x{screen_height}+0+0')  # Set window size and position
        # else:
        #     self.attributes('-fullscreen', True)  # Otherwise, use fullscreen for other dimensions or OS 
        #self.config(cursor='none')

        # Create the timer
        self.timer_text = ctk.StringVar()
        self.timer_app = TimerApp(self, self.timer_text)

        self.ws_id = ws_id
        self.original_ws_id = ws_id


        self.orders_dict = {}
        self.past_orders_dict = {}

        self.pending_help = {'L':None, 'R':None}
        self.past_help_requests_dict = {}

        

        self.pending_order_from_previous_ws = {'L':None, 'R':None}
        self.order_ready_for_next_ws = {'L':None, 'R':None}

        self.assembly_type =  'standard' # or "simplified"

        # send ws_id at the start of the session
        self.mqtt_handler = mqtt.Local_MQTT_Handler_Workstations(self)
        
        self.create_widgets()

        self.mqtt_handler.subscribe_to_topics()
        self.send_ws_id(self.ws_id)
        self.send_ws_info()


        # divide the work in two to avoid early function calls
        


    def create_widgets(self, disable=True):
        
        # Eliminate any previous widget
        self.clean_window()

        # Grid configuration
        # self.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)
        self.grid_columnconfigure((0,1), weight=1)
        self.grid_rowconfigure((0,4,5), weight=0)
        self.grid_rowconfigure((1,2,3), weight=1)


        ######################## TOP ROW #########################
        ##########################################################

        # Create and place the top row with informations
        self.bold_and_big_font = ctk.CTkFont(weight='bold', size=30)
        self.bold_and_normal_font = ctk.CTkFont(weight='bold', size=20)

        top_info_frame = ctk.CTkFrame(master=self)
        top_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.image = ctk.CTkImage(Image.open('images/logo.png'), size=(119,45))
        self.image_label = ctk.CTkLabel(master=top_info_frame, text='', image=self.image)
        self.image_label.pack(side='left', padx=(30,50), pady=0)

        self.ws_id_stringvar = ctk.StringVar(value=f'WS {self.ws_id}')
        self.station_number_label = ctk.CTkLabel(master=top_info_frame, textvariable=self.ws_id_stringvar, font=self.bold_and_big_font)
        self.station_number_label.pack(side='left', padx=50, pady=15)

        # Start the clock
        self.time_text = ctk.StringVar()
        self.update_time()

        self.time_label = ctk.CTkLabel(master=top_info_frame, textvariable=self.time_text, font=self.bold_and_big_font)
        self.time_label.pack(side='left', padx = 50, pady=15)




        settings_button = ctk.CTkButton(master=top_info_frame, text="Settings", height=40, width=50, command=self.settings_callback)
        settings_button.pack(side="right", padx=25, pady=15)
        # TODO: RIGHT NOW AVOID RENAMING THE STATIONS.
        settings_button.configure(state="disabled")

        # callbacks.instanciate_local_timer_obj(self.timer_app)
        self.timer_label = ctk.CTkLabel(master=top_info_frame, textvariable=self.timer_text, font=self.bold_and_big_font)
        self.timer_label.pack(side='right', padx = 25, pady=15)

        
        ######################## SPINBOXES ROWS #########################
        #################################################################

        self.create_spinboxes()
        

        ######################## ORDER ROW #########################
        ############################################################

        self.previous_orders_row_frame = ctk.CTkFrame(master=self)
        self.previous_orders_row_frame.grid_columnconfigure((0,1), weight=1)
        self.previous_orders_row_frame.grid_rowconfigure((1), weight=1)
        self.previous_orders_row_frame.grid(row=3, column=0, columnspan=2, sticky="ew")

        self.left_order_title = ctk.CTkLabel(master=self.previous_orders_row_frame, text='L OPERATOR PENDING ORDERS', font=self.bold_and_normal_font)
        self.left_order_title.grid(row=0, column=0, padx=10, pady=15, sticky="nw")

        self.right_order_title = ctk.CTkLabel(master=self.previous_orders_row_frame, text='R OPERATOR PENDING ORDERS', font=self.bold_and_normal_font)
        self.right_order_title.grid(row=0, column=1, padx=10, pady=15, sticky="ne")

        self.scrollable_label_button_frame_L = ScrollableLabelButtonFrame(master=self.previous_orders_row_frame, detail_command=self.on_past_order_details, delivered_command=self.delivered_command, corner_radius=0, height=100)
        # self.scrollable_label_button_frame_L.pack(side='left', padx = 0, pady=0)
        self.scrollable_label_button_frame_L.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.scrollable_label_button_frame_R = ScrollableLabelButtonFrame(master=self.previous_orders_row_frame, detail_command=self.on_past_order_details, delivered_command=self.delivered_command, corner_radius=0, height=100)
        # self.scrollable_label_button_frame_R.pack(side='right', padx = 0, pady=0)
        self.scrollable_label_button_frame_R.grid(row=1, column=1, padx=0, pady=0, sticky="nsew")
        # for i in range(10):  # add items with images
        #     self.scrollable_label_button_frame_L.add_item(f"image and item {i}")
        # for i in range(15):
        #     self.scrollable_label_button_frame_R.add_item(f"image and item {i}")

        ####################### TOP BUTTON ROW #########################
        ################################################################

        # Create and place the bottom row with buttons
        # Left operator
        top_button_frame_L = ctk.CTkFrame(master=self)
        top_button_frame_L.grid(row=4, column=0, columnspan=1, sticky="nsew")

        self.send_order_button_op_L = ctk.CTkButton(master=top_button_frame_L, height=40, width=130, text="Send Order", command=lambda: self.send_callback('L'))
        self.send_order_button_op_L.pack(side="left", padx=10, pady=(20,10))

        self.help_stringvar_op_L = ctk.StringVar(value='REQUEST HELP')
        self.help_button_op_L = ctk.CTkButton(master=top_button_frame_L, height=40, width=130, textvariable=self.help_stringvar_op_L, border_width=2, border_color='#FFD600', fg_color='transparent', hover_color='#b29500', command=lambda: self.help_callback('L')) #text_color='gray', 
        self.help_button_op_L.pack(side="left", padx=10, pady=(20,10))
        self.help_button_blinking_op_L = False

        self.start_button_op_L = ctk.CTkButton(master=top_button_frame_L, height=40, width=130, text="START", border_width=2, border_color='#006838', fg_color='transparent', hover_color='#004827', command=lambda: self.start_callback('L'))
        self.start_button_op_L.pack(side="left", padx=10, pady=(20,10))

        self.stop_button_op_L = ctk.CTkButton(master=top_button_frame_L, height=40, width=130, text="STOP", border_width=2, border_color='#CC2027', fg_color='transparent', hover_color='#8e161b', command=lambda: self.stop_callback('L'))
        self.stop_button_op_L.pack(side="left", padx=10, pady=(20,10))
        self.stop_button_blinking_op_L = False

        # For the top frames division
        vertical_line_top = ctk.CTkFrame(top_button_frame_L, width=3, fg_color='#6A6969', height=75)
        vertical_line_top.pack(side='right')
        
        top_button_frame_R = ctk.CTkFrame(master=self)
        top_button_frame_R.grid(row=4, column=1, columnspan=1, sticky="nsew")

        # Right operator
        self.stop_button_op_R = ctk.CTkButton(master=top_button_frame_R, height=40, width=130, text="STOP", border_width=2, border_color='#CC2027', fg_color='transparent', hover_color='#8e161b', command=lambda: self.stop_callback('R'))
        self.stop_button_op_R.pack(side="right", padx=10, pady=(20,10))
        self.stop_button_blinking_op_R = False

        self.start_button_op_R = ctk.CTkButton(master=top_button_frame_R, height=40, width=130, text="START", border_width=2, border_color='#006838', fg_color='transparent', hover_color='#004827', command=lambda: self.start_callback('R'))
        self.start_button_op_R.pack(side="right", padx=10, pady=(20,10))

        self.help_stringvar_op_R = ctk.StringVar(value='REQUEST HELP')
        self.help_button_op_R = ctk.CTkButton(master=top_button_frame_R, height=40, width=130, textvariable=self.help_stringvar_op_R, border_width=2, border_color='#FFD600', fg_color='transparent', hover_color='#b29500', command=lambda: self.help_callback('R')) #text_color='gray', 
        self.help_button_op_R.pack(side="right", padx=10, pady=(20,10))
        self.help_button_blinking_op_R = False

        self.send_order_button_op_R = ctk.CTkButton(master=top_button_frame_R, height=40, width=130, text="Send Order", command=lambda: self.send_callback('R'))
        self.send_order_button_op_R.pack(side="right", padx=10, pady=(20,10))


        ####################### BOTTOM BUTTON ROW #########################
        ###################################################################
        bottom_button_frame_L = ctk.CTkFrame(master=self)
        bottom_button_frame_L.grid(row=5, column=0, sticky="nsew")

        self.waiting_previous_stringvar_op_L = ctk.StringVar(value='Waiting from previous workstation')
        self.waiting_previous_button_op_L = ctk.CTkButton(master=bottom_button_frame_L, height=40, width=280, border_width=2, border_color='#2D5289', fg_color='transparent', textvariable=self.waiting_previous_stringvar_op_L, command=lambda: self.waiting_previous_callback('L'))
        self.waiting_previous_button_op_L.pack(side="left", padx=10, pady=(10,20))
        self.waiting_previous_button_blinking_op_L = False
        
        self.ready_for_next_stringvar_op_L = ctk.StringVar(value='Ready for next workstation')
        self.ready_for_next_button_op_L = ctk.CTkButton(master=bottom_button_frame_L, height=40, width=280, border_width=2, border_color='#006838', fg_color='transparent', textvariable=self.ready_for_next_stringvar_op_L, command=lambda: self.ready_for_next_callback('L'))
        self.ready_for_next_button_op_L.pack(side="left", padx=10, pady=(10,20))
        self.ready_for_next_button_blinking_op_L = False

        # For the bottom frames division
        vertical_line_top = ctk.CTkFrame(bottom_button_frame_L, width=3, fg_color='#6A6969', height=75)
        vertical_line_top.pack(side='right')
        
        bottom_button_frame_R = ctk.CTkFrame(master=self)
        bottom_button_frame_R.grid(row=5, column=1, sticky="nsew")
        
        self.ready_for_next_stringvar_op_R = ctk.StringVar(value='Ready for next workstation')
        self.ready_for_next_button_op_R = ctk.CTkButton(master=bottom_button_frame_R, height=40, width=280, border_width=2, border_color='#006838', fg_color='transparent', textvariable=self.ready_for_next_stringvar_op_R, command=lambda: self.ready_for_next_callback('R'))
        self.ready_for_next_button_op_R.pack(side="right", padx=10, pady=(10,20))
        self.ready_for_next_button_blinking_op_R = False

        self.waiting_previous_stringvar_op_R = ctk.StringVar(value='Waiting from previous workstation')
        self.waiting_previous_button_op_R = ctk.CTkButton(master=bottom_button_frame_R, height=40, width=280, border_width=2, border_color='#2D5289', fg_color='transparent', textvariable=self.waiting_previous_stringvar_op_R, command=lambda: self.waiting_previous_callback('R'))
        self.waiting_previous_button_op_R.pack(side="right", padx=10, pady=(10,20))
        self.waiting_previous_button_blinking_op_R = False


        if disable:
            self.disable_workstation()

        self.start_blinking()

    def ready_for_next_callback(self, side):
        # Set the color of the manual buttons to transparent and reset manual
        getattr(self, f'stop_button_op_{side}').configure(fg_color='transparent')
        getattr(self, f'start_button_op_{side}').configure(fg_color='transparent')
        self.send_manual_reset(side)

        # Toggle the order_from_previous_ws request state based on the current text of the button
        if self.order_ready_for_next_ws.get(side) is None:
            # If no pending order_from_previous_ws, it means we are requesting order_from_previous_ws now
            ready_for_next_id = f'WS{self.ws_id}_ready_for_next_{generate_help_id()}'
            # idle = self.check_urgent(message="Do you need this immediately?")
            ready_for_next_json = json.dumps({'ready_for_next_id': ready_for_next_id, 'ws_id': self.ws_id, 'side': side, 'ready': True})
            self.mqtt_handler.publish(topic='/ws_manager/order_for_next_ws', payload=ready_for_next_json)
            self.order_ready_for_next_ws[side] = {'ready_for_next_id': ready_for_next_id, 'creation_time': datetime.now()}
            # Update button text to "DONE WAITING"
            getattr(self, f'ready_for_next_stringvar_op_{side}').set('PREASSEMBLY DELIVERED')
            setattr(self, f'ready_for_next_button_blinking_op_{side}', True)
        else:
            ready_for_next_id = self.order_ready_for_next_ws[side]['ready_for_next_id']
            ready_for_next_json = json.dumps({'ready_for_next_id':ready_for_next_id, 'ws_id':self.ws_id, 'side':side, 'ready': False})
            self.mqtt_handler.publish(topic='/ws_manager/order_for_next_ws', payload=ready_for_next_json)

            # If there is a pending order_from_previous_ws, it means we are deleting the order_from_previous_ws request now
            self.order_ready_for_next_ws[side] = None
            # Update button text back to "WAITING PREAVIOUS"
            getattr(self, f'ready_for_next_stringvar_op_{side}').set('Ready for next workstation')
            setattr(self, f'ready_for_next_button_blinking_op_{side}', False)

    def start_blinking(self, blink=True):
        # Define a mapping of button properties based on conditions
        button_configurations = [
            (self.help_button_blinking_op_L, self.help_button_op_L, '#FFD600'),
            (self.help_button_blinking_op_R, self.help_button_op_R, '#FFD600'),
            (self.waiting_previous_button_blinking_op_L, self.waiting_previous_button_op_L, '#3B6CB4'),
            (self.waiting_previous_button_blinking_op_R, self.waiting_previous_button_op_R, '#3B6CB4'),
            (self.stop_button_blinking_op_L, self.stop_button_op_L, '#CC2027'),
            (self.stop_button_blinking_op_R, self.stop_button_op_R, '#CC2027'),
            (self.ready_for_next_button_blinking_op_L, self.ready_for_next_button_op_L, '#006838'),
            (self.ready_for_next_button_blinking_op_R, self.ready_for_next_button_op_R, '#006838'),
        ]
        
        # Iterate through each configuration and apply settings based on `blink` flag
        for is_blinking, button, color in button_configurations:
            fg_color = color if is_blinking and blink else 'transparent'
            button.configure(fg_color=fg_color)
        
        # Schedule the next blinking toggle
        self.after(500, lambda: self.start_blinking(blink=not blink))


    def waiting_previous_callback(self, side):
        # Set the color of the manual buttons to transparent and reset manual
        getattr(self, f'stop_button_op_{side}').configure(fg_color='transparent')
        getattr(self, f'start_button_op_{side}').configure(fg_color='transparent')
        self.send_manual_reset(side)

        # Toggle the order_from_previous_ws request state based on the current text of the button
        if self.pending_order_from_previous_ws.get(side) is None:
            # If no pending order_from_previous_ws, it means we are requesting order_from_previous_ws now
            prev_ws_order_id = f'WS{self.ws_id}_prev_ws_order_{generate_help_id()}'
            idle = self.check_urgent(message="Do you need this immediately?")
            prev_ws_order_json = json.dumps({'prev_ws_order_id': prev_ws_order_id, 'ws_id': self.ws_id, 'side': side, 'pending': True, 'idle': idle})
            self.mqtt_handler.publish(topic='/ws_manager/order_from_previous_ws', payload=prev_ws_order_json)
            self.pending_order_from_previous_ws[side] = {'prev_ws_order_id': prev_ws_order_id, 'idle': idle, 'creation_time': datetime.now()}
            # Update button text to "DONE WAITING"
            getattr(self, f'waiting_previous_stringvar_op_{side}').set('DONE WAITING')
            setattr(self, f'waiting_previous_button_blinking_op_{side}', True)
        else:
            prev_ws_order_id = self.pending_order_from_previous_ws[side]['prev_ws_order_id']
            prev_ws_order_json = json.dumps({'prev_ws_order_id':prev_ws_order_id, 'ws_id':self.ws_id, 'side':side, 'pending': False, 'idle': False})
            self.mqtt_handler.publish(topic='/ws_manager/order_from_previous_ws', payload=prev_ws_order_json)

            # If there is a pending order_from_previous_ws, it means we are deleting the order_from_previous_ws request now
            self.pending_order_from_previous_ws[side] = None
            # Update button text back to "WAITING PREAVIOUS"
            getattr(self, f'waiting_previous_stringvar_op_{side}').set('Waiting from previous workstation')
            setattr(self, f'waiting_previous_button_blinking_op_{side}', False)

    def send_manual_reset(self, side):
        setattr(self, f'stop_button_blinking_op_{side}', False)
        getattr(self, f'start_button_op_{side}').configure(fg_color='transparent')
        reset_json = json.dumps({'original_ws_id':self.original_ws_id, 'side':side, 'manual_command':'reset'})
        self.mqtt_handler.publish(topic='/ws_manager/manual_state', payload=reset_json)


    def start_callback(self, side):
        setattr(self, f'stop_button_blinking_op_{side}', False)
        getattr(self, f'start_button_op_{side}').configure(fg_color='#006838')
        getattr(self, f'stop_button_op_{side}').configure(fg_color='transparent')
        
        
        # start_id = 0 #TODO THIS IS A MOCKUP, SEE IF ID IS ACTUALLY NEEDED!!!!

        start_json = json.dumps({'original_ws_id':self.original_ws_id, 'side':side, 'manual_command':'start'})
        self.mqtt_handler.publish(topic='/ws_manager/manual_state', payload=start_json)

    def stop_callback(self, side):
        getattr(self, f'start_button_op_{side}').configure(fg_color='transparent')
        getattr(self, f'stop_button_op_{side}').configure(fg_color='#CC2027')
        setattr(self, f'stop_button_blinking_op_{side}', True)
        
        
        # stop_id = 0 #TODO THIS IS A MOCKUP, SEE IF ID IS ACTUALLY NEEDED!!!!

        stop_json = json.dumps({'original_ws_id':self.original_ws_id, 'side':side, 'manual_command':'stop'})
        self.mqtt_handler.publish(topic='/ws_manager/manual_state', payload=stop_json)

    def remove_order(self, order_id, reason):
        # Implement the logic to remove the order from the list and destroy its button
        #self.orders_dict[order_id].button.destroy()
        
        if order_id in self.orders_dict:
            if self.orders_dict[order_id].side == 'L':
                self.scrollable_label_button_frame_L.remove_item(order_id)
            else:
                self.scrollable_label_button_frame_R.remove_item(order_id)

            self.past_orders_dict[order_id] = self.orders_dict.pop(order_id)
            self.past_orders_dict[order_id].end_time = datetime.now()
            self.past_orders_dict[order_id].end_reason = reason

    def delivered_command(self, order_id):
        order_id_json = json.dumps({'order_id':order_id})
        self.mqtt_handler.publish(topic='/ws_manager/order_delivered', payload=order_id_json)

    def on_past_order_details(self, order_id):
        # Function to handle the "Delivered" action
        def delivered_action(window):
            # Implement the logic for when an order is marked as delivered
            print(f"Order {order_id} marked as delivered.")

            self.delivered_command(order_id)
            window.destroy()

        def delete_order_action(window):
            # Implement the logic for when an order is deleted
            print(f"Order {order_id} deleted by operator.")

            order_id_json = json.dumps({'order_id':order_id})
            self.mqtt_handler.publish(topic='/ws_manager/delete_oder', payload=order_id_json)

            window.destroy()

        # Function to handle the "Yet to Deliver" action
        def go_back_action(window):
            window.destroy()

        def mark_as_action(window, marker):
            urgent = True if marker == "urgent" else False
            self.mark_order_as(order_id, urgent)
            window.destroy()

        # Create the top-level window
        window = ctk.CTkToplevel(self, fg_color='#353535')
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_width = 800
        window_height = 400
        x = (screen_width / 2) - (window_width / 2)
        y = (screen_height / 2) - (window_height / 2)
        window.geometry(f'{window_width}x{window_height}+{int(x)}+{int(y)}')
        #window.resizable(False, False)
        window.grid_columnconfigure((0, 1, 2, 3), weight=1)
        window.grid_rowconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=0)
        window.overrideredirect(True)
        window.wait_visibility()
        window.grab_set()

        # Display order details
        message = f"Order ID: {order_id}\n\n"
        
        if self.orders_dict[order_id].urgent:
            marker = 'not urgent'
        else:
            marker = 'urgent'


        print(self.orders_dict)
        for key, quantity in self.orders_dict[order_id].items_dict.items():
            message += f'{key}: {quantity}\n'

        
        message_label = ctk.CTkLabel(master=window, text=message)
        message_label.grid(row=0, column=0, columnspan=4, pady=(30, 15), padx=30, sticky='nsew')

        # Buttons for "Delivered" and "Yet to Deliver"
        go_back_button = ctk.CTkButton(master=window, text='Go back', command=lambda: go_back_action(window), height=40, corner_radius=20)
        delivered_button = ctk.CTkButton(master=window, text='Delivered', command=lambda: delivered_action(window), height=40, corner_radius=20)
        delete_button = ctk.CTkButton(master=window, text='Delete Order', command=lambda: delete_order_action(window), height=40, corner_radius=20)
        mark_as_button = ctk.CTkButton(master=window, text=f'Mark as {marker}', command=lambda: mark_as_action(window, marker), height=40, corner_radius=20)
       
        go_back_button.grid(row=1, column=0, pady=(15, 30), padx=30, sticky='ew')
        delivered_button.grid(row=1, column=1, pady=(15, 30), padx=30, sticky='ew')
        delete_button.grid(row=1, column=2, pady=(15, 30), padx=30, sticky='ew')
        mark_as_button.grid(row=1, column=3, pady=(15, 30), padx=30, sticky='ew')

        window.wait_window()  # Wait until the dialog window is closed


    def disable_workstation(self, original_ws_ids=None):
        # Check if the current workstation ID is in the provided list
        if original_ws_ids is None or self.original_ws_id in original_ws_ids:
            for side, help in self.pending_help.items():
                if help is not None:
                    self.help_callback(side)

            for side, pending_order_from_previous_ws in self.pending_order_from_previous_ws.items():
                if pending_order_from_previous_ws is not None:
                    self.waiting_previous_callback(side)

            for side, order_ready_for_next_ws in self.order_ready_for_next_ws.items():
                if order_ready_for_next_ws is not None:
                    self.ready_for_next_callback(side)

            for side in ['L', 'R']:
                # setattr(self, f'help_button_blinking_op_{side}', False)
                # setattr(self, f'waiting_previous_button_blinking_op_{side}', False)
                setattr(self, f'stop_button_blinking_op_{side}', False)
                # setattr(self, f'ready_for_next_button_blinking_op_{side}', False)
            # Iterate through all widgets in the application
            for widget in self.winfo_children():  # Assuming 'self' is a tk.Tk or tk.Frame instance
                if isinstance(widget, ctk.CTkFrame):
                    for child_widget in widget.winfo_children():  # Assuming 'self' is a tk.Tk or tk.Frame instance
                        # Check if the widget is a button
                        if isinstance(child_widget, ctk.CTkButton) and child_widget.cget('text') != "Settings":
                            child_widget.configure(state="disabled") # Disable the button
                        # Check if the widget is an instance of the SpinBox class
                        elif isinstance(child_widget, Spinbox):  # Assuming SpinBox is a custom class you have defined
                            child_widget.disable_spinbox()  # Call the custom disable method for SpinBox
    

    def enable_workstation(self, original_ws_ids=None):
        start_sound_thread = threading.Thread(target=lambda: self.play_sound('start'))
        start_sound_thread.start()
        # Check if the current workstation ID is in the provided list
        if original_ws_ids is None or self.original_ws_id in original_ws_ids:
            # Iterate through all widgets in the application
            for widget in self.winfo_children(): 
                if isinstance(widget, ctk.CTkFrame):
                    for child_widget in widget.winfo_children():  
                        # Check if the widget is a button
                        if isinstance(child_widget, ctk.CTkButton) and child_widget.cget('text') != "Settings":
                            child_widget.configure(state="normal") # Enable the button
                        # Check if the widget is an instance of the SpinBox class
                        elif isinstance(child_widget, Spinbox):  # Assuming SpinBox is a custom class you have defined
                            child_widget.enable_spinbox()  # Call the custom disable method for SpinBox




    def set_assembly_type(self, assembly_type):
        self.assembly_type = assembly_type


        # for widget in self.second_row_frame.winfo_children():
        #     widget.destroy()
        # for widget in self.third_row_frame.winfo_children():
        #     widget.destroy()

        # It doesnt seem to be necessary to first destroy the frames...
        # self.second_row_frame.destroy()
        # self.third_row_frame.destroy()

        self.create_spinboxes()
        if not self.timer_app.timer_running:
            self.disable_workstation()


    def send_ws_id(self, ws_id=None):
        if ws_id is None:
            ws_id = self.ws_id
        json_payload = json.dumps({'ws_id':ws_id, 'original_ws_id':self.original_ws_id})
        self.mqtt_handler.publish(topic='/ws_manager/set_ws_id', payload=json_payload)


    def send_ws_info(self):
        # First start the timer
        if self.timer_app.remaining_seconds.total_seconds() > 0:
            if self.timer_app.timer_running:
                print(f"Sending timer command to everybody")
                # Send timer command with current remaining seconds
                payload = json.dumps({'command':'start', 'seconds':self.timer_app.remaining_seconds.total_seconds(), 'initiator':'workstation'})
                self.mqtt_handler.publish(topic='/ws_manager/timer', payload=payload)
            # else:
                # if self.timer_app.paused_time.total_seconds():
                #     payload = json.dumps({'remaining_seconds': self.timer_app.paused_time.total_seconds()})
                #     self.mqtt_handler.publish(topic='/ws_manager/remaining_seconds', payload=payload)
                # else:
                #     # If timer is not running and there's no paused_time, something is wrong, stop the timer.
                #     # TODO: very weird if the program ends up here, think thoroughly about this scenario
                #     print("SUPER WEIRD THAT WE'RE HERE, FIGURE OUT WHY.")
                #     payload = json.dumps({'command':'stop'})
                #     self.mqtt_handler.publish(topic='/ws_manager/timer', payload=payload)

        # Then send whatever information is needed
        pending_orders_dict = {}
        for order_id, order in self.orders_dict.items():
            pending_orders_dict[order_id] = order.to_serializable_dict()
        
        
        pending_help_dict = {'L':None, 'R':None}
        for side, help_dict in self.pending_help.items():
            if help_dict is  not None:
                pending_help_dict[side] = {}
                pending_help_dict[side]['help_id'] = help_dict['help_id']
                pending_help_dict[side]['creation_time'] = help_dict['creation_time'].isoformat()
                pending_help_dict[side]['idle'] = help_dict['idle']
        
        pending_order_from_previous_ws_dict = {'L':None, 'R':None}
        for side, order_from_prev_ws_dict in self.pending_order_from_previous_ws.items():
            if order_from_prev_ws_dict is  not None:
                pending_order_from_previous_ws_dict[side] = {}
                pending_order_from_previous_ws_dict[side]['prev_ws_order_id'] = order_from_prev_ws_dict['prev_ws_order_id']
                pending_order_from_previous_ws_dict[side]['creation_time'] = order_from_prev_ws_dict['creation_time'].isoformat()
                pending_order_from_previous_ws_dict[side]['idle'] = order_from_prev_ws_dict['idle']
        
        info_dict = {
            'ws_id':self.ws_id, 
            'original_ws_id':self.original_ws_id, 
            'pending_orders':pending_orders_dict,
            'pending_help':pending_help_dict,
            'pending_order_from_previous_ws':pending_order_from_previous_ws_dict
        }

        print(info_dict)

        info_json = json.dumps(info_dict)
        self.mqtt_handler.publish(topic='/ws_manager/set_ws_info', payload=info_json)



    def update_ws_id(self, original_ws_id, ws_id):
        # Only execute if the message is for this workstation
        if original_ws_id == self.original_ws_id:
            if ws_id:
                self.ws_id = ws_id
                self.ws_id_stringvar.set(f"WS {ws_id}")
            else:
                # show error message
                print("This name is already in use. Please choose another name.")
                pass
            

    def settings_callback(self):
        def cancel_action(window):
            window.destroy()

        def save_action(window, ws_id):
            window.destroy()
            self.send_ws_id(ws_id)

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
        window.grid_rowconfigure((0, 1, 2), weight=1)
        window.overrideredirect(True)
        window.wait_visibility()
        window.grab_set()



        name_label = ctk.CTkLabel(master=window, text="Workstation name:")
        name_label.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='s')
        
        # Variable for the CTkEntry widget (text field)
        ws_id = self.ws_id  # This should be replaced with your actual default value

        ws_id_entry = ctk.CTkEntry(window, textvariable=ctk.StringVar(value=ws_id))
        ws_id_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky='n')

        cancel_button = ctk.CTkButton(master=window, text='Cancel', command=lambda: cancel_action(window), height=40, corner_radius=20)
        save_button = ctk.CTkButton(master=window, text=f'Save', command=lambda: save_action(window, ws_id_entry.get()), height=40, corner_radius=20)
       
        cancel_button.grid(row=2, column=0, pady=(15, 30), padx=30, sticky='ew')
        save_button.grid(row=2, column=1, pady=(15, 30), padx=30, sticky='ew')

        window.wait_window()  # Wait until the dialog window is closed
        
    

    def mark_order_as(self, order_id, urgent):
        self.orders_dict[order_id].urgent = urgent


        final_dict = {'urgent':urgent, 'order_id':order_id}
        final_dict_json =json.dumps(final_dict)

        self.mqtt_handler.publish(topic='/ws_manager/update_order', payload=final_dict_json)


    def send_callback(self, side):
        # Set the color of the manual buttons to transparent and reset manual
        getattr(self, f'stop_button_op_{side}').configure(fg_color='transparent')
        getattr(self, f'start_button_op_{side}').configure(fg_color='transparent')
        self.send_manual_reset(side)


        final_dict = {'items':{},'attributes':{}}
        for spin_box in self.spin_boxes:
            final_dict['items'][spin_box.name] = spin_box.get_value()


        final_dict['attributes']['ws_id'] = self.ws_id
        # final_dict['attributes']['original_ws_id'] = self.original_ws_id
        final_dict['attributes']['operator_side'] = side

        final_dict['attributes']['urgent'] = self.check_urgent(message="Is your local storage empty?") # True if urgent, False if not urgent
        
        order_id = f'WS{self.ws_id}_{generate_id()}'
        # Save last order in the dictionary
        order_ids[side].append(order_id)
        # Add last order to the payload
        final_dict['attributes']['order_id'] = order_id
        


        # Create a list of keys to be removed
        keys_to_remove = [key for key, value in final_dict['items'].items() if value == 0]
        # If no item is being ordered, dont even send the order
        if len(keys_to_remove) == len(final_dict['items']):
            return 
        # Iterate over the list of keys and remove them from the dictionary
        for key in keys_to_remove:
            del final_dict['items'][key]

        
        final_dict_json =json.dumps(final_dict)
        print(final_dict_json)

        self.save_order(final_dict)

        # Publish to the broker
        self.mqtt_handler.publish(topic='/ws_manager/orders', payload=final_dict_json)
        
        self.second_row_frame.destroy()
        self.third_row_frame.destroy()
        self.create_spinboxes()



    def save_order(self, order_dict):
        items_dict = order_dict['items']
            
        order_dict = order_dict['attributes']

        order_id = order_dict['order_id']
        ws_id = order_dict['ws_id']
        side = order_dict['operator_side']
        urgent = order_dict['urgent']

        label_text = ctk.StringVar()
        
        if side == 'L':
            self.scrollable_label_button_frame_L.add_item(order_id, label_text)
            # self.scrollable_label_button_frame_L.update()
        else:
            self.scrollable_label_button_frame_R.add_item(order_id, label_text)
            # self.scrollable_label_button_frame_R.update()


        order = Order(order_id, self.original_ws_id, ws_id, side, datetime.now(), label_text, urgent, items_dict)
        # self.orders.append(order)
        self.orders_dict[order_id] = order
        self.create_order_label(self.orders_dict[order_id])


    def create_order_label(self, order):
        label = f"{order.order_id}     "
        
        for item, quantity in order.items_dict.items():
            label += f"|   {item} {quantity}   "
        
        label += "|"

        order.label_text.set(label)



    def cancel_callback(self):
        self.clean_window()
        self.create_widgets(disable=False)

        
    def help_callback(self, side):
        # Set the color of the manual buttons to transparent and reset manual
        getattr(self, f'stop_button_op_{side}').configure(fg_color='transparent')
        getattr(self, f'start_button_op_{side}').configure(fg_color='transparent')
        self.send_manual_reset(side)

        # Toggle the help request state based on the current text of the button
        if self.pending_help.get(side) is None:
            # If no pending help, it means we are requesting help now
            help_id = f'WS{self.ws_id}_HELP_{generate_help_id()}'
            idle = self.check_urgent(message="Are you stuck?")
            help_json = json.dumps({'help_id': help_id, 'ws_id': self.ws_id, 'side': side, 'help': True, 'idle': idle})
            self.mqtt_handler.publish(topic='/ws_manager/help_request', payload=help_json)
            self.pending_help[side] = {'help_id': help_id, 'idle': idle, 'creation_time': datetime.now()}
            # Update button text to "DELETE HELP"
            # self.help_stringvar_op_L.set('DELETE HELP')
            help_sound_thread = threading.Thread(target=lambda: self.play_sound('help'))
            help_sound_thread.start()
            getattr(self, f'help_stringvar_op_{side}').set('DELETE HELP')
            setattr(self, f'help_button_blinking_op_{side}', True)
        else:
            help_id = self.pending_help[side]['help_id']
            help_json = json.dumps({'help_id':help_id, 'ws_id':self.ws_id, 'side':side, 'help': False, 'idle': False})
            self.mqtt_handler.publish(topic='/ws_manager/help_request', payload=help_json)

            # If there is a pending help, it means we are deleting the help request now
            self.pending_help[side] = None
            # Update button text back to "REQUEST HELP"
            getattr(self, f'help_stringvar_op_{side}').set('REQUEST HELP')
            setattr(self, f'help_button_blinking_op_{side}', False)



    def create_spinboxes(self):
        self.second_row_frame = ctk.CTkFrame(master=self)
        self.second_row_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.third_row_frame = ctk.CTkFrame(master=self)
        self.third_row_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.spin_boxes = []
        n_items = len(ITEMS[self.assembly_type].keys())
        items_top_row = ceil(n_items/2)
        items_bottom_row = n_items - items_top_row

        # Generate tuples dynamically based on items_top_row and items_bottom_row
        top_row_tuple = tuple(range(items_top_row))
        bottom_row_tuple = tuple(range(items_bottom_row))

        # Use the generated tuples for configuring grid columnconfigure
        self.second_row_frame.grid_columnconfigure(top_row_tuple, weight=1)
        self.second_row_frame.grid_rowconfigure(0, weight=1)
        self.third_row_frame.grid_columnconfigure(bottom_row_tuple, weight=1)
        self.third_row_frame.grid_rowconfigure(0, weight=1)


        for i, item in enumerate(ITEMS[self.assembly_type].keys()):
            if i < items_top_row:
                self.spin_boxes.append(Spinbox(self.second_row_frame, image_path=ITEMS[self.assembly_type][item], name=item))
            else:
                self.spin_boxes.append(Spinbox(self.third_row_frame, image_path=ITEMS[self.assembly_type][item], name=item))

        
        # Create and place the spinboxes in two rows
        for i in range(items_top_row):
            self.spin_boxes[i].grid(row=0, column=i, sticky="ew", padx=5, pady=5)

        for i in range(items_bottom_row):
            list_index = i+items_top_row
            self.spin_boxes[list_index].grid(row=0, column=i, sticky="ew", padx=5, pady=5)


    def clean_window(self):
        for widget in self.winfo_children():
            widget.grid_forget()  
        

    def update_time(self):
        current_time = datetime.now()
        time_string = current_time.strftime('%H:%M:%S')
        self.time_text.set(time_string)
        self.after(500, self.update_time)
    

    def check_urgent(self, message):

        self.urgent_response = None  # This will store the user's choice

        def yes_action_aggregate(window):
            self.urgent_response = True
            window.destroy()

        def no_action_aggregate(window):
            self.urgent_response = False
            window.destroy()

        

        self.window = ctk.CTkToplevel(self, fg_color='#353535')
    
        # Get screen width and height
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Calculate position x and y coordinates
        x = (screen_width/2) - (400/2)
        y = (screen_height/2) - (200/2)

        self.window.geometry(f'400x200+{int(x)}+{int(y)}')
        self.window.resizable(False, False)
        self.window.grid_columnconfigure((1,2), weight=1)
        self.window.grid_rowconfigure((1,2),weight=1)
        self.window.overrideredirect(True)
        self.window.wait_visibility()
        self.window.grab_set()

          #Have you already terminated\nthe components in the order?"
        
        self.messagelabel = ctk.CTkLabel(master=self.window, text=message)
        self.messagelabel.grid(row=0,column=0, columnspan=2, pady=(30,15), padx=30, sticky='nsew')


        # Your button setup code...
        self.yes_button = ctk.CTkButton(master=self.window, command=lambda: yes_action_aggregate(self.window), text='YES', height=40, corner_radius=20)
        self.no_button = ctk.CTkButton(master=self.window, command=lambda: no_action_aggregate(self.window), text='NO', height=40, corner_radius=20)
        self.yes_button.grid(row=1,column=0, pady=(15,30), padx=30, sticky='w')
        self.no_button.grid(row=1,column=1, pady=(15,30), padx=30, sticky='e')

        self.window.wait_window()  # This waits until the dialog window is closed
        return self.urgent_response
    

    def timer_end(self):
        order_ids = list(self.orders_dict.keys())
        print(order_ids)
        while self.orders_dict:
            # TODO: NOT WORKING, UNDERSTAND WHY (working in inventory)
            self.remove_order(order_ids.pop(0), reason="timer")
        
        # Start new thread to avoid program halting when playing the sound
        end_sound_thread = threading.Thread(target=lambda: self.play_sound('end'))
        end_sound_thread.start()

    def play_sound(self, sound):
        pygame.mixer.init()
        sound = pygame.mixer.Sound(f"sounds/{sound}.mp3")
        sound.play()
        # Sleep to prevent the thread from ending too soon
        time.sleep(sound.get_length())







def main():
    # Load the config.json file
    with open('config.json', 'r') as file:
        config = json.load(file)

    # Retrieve the ws_id from the config
    ws_id = config['station_ID']

    # Start the main loop
    client = Client(ws_id)
    client.mainloop()



if __name__ == "__main__":
    main()


