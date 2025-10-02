import datetime
import os
import csv

#/Users/giovannichiementin/Desktop/Uni-Work/Learning_Factory/Parts_order_UI/

ITEMS = {
    
    "standard":{
        "Battery":          "images/battery.png",
        "Board Screw":      "images/board_screw.png", 
        "Damper":           "images/bumper.png", 
        "C-CW Prop":        "images/c_cw_prop.png", 
        "Camera Board":     "images/camera_board.png", 
        "Camera Housing":   "images/camera_housing.png",
        "Camera Screw":     "images/camera_screw.png", 
        "Control Board":    "images/control_board.png", 
        "CW Prop":          "images/cw_prop.png", 
        "Drone Frame":      "images/frame.png", 
        "Motor Jig":        "images/motor_jig.png",
        "Motor Screw":      "images/motor_screw.png",
        "Motor":            "images/motor.png"
    },
    "simplified":{
        "Battery":          "images/battery.png",
        "Board Screw":      "images/board_screw.png", 
        "Damper":           "images/bumper.png", 
        "C-CW Prop":        "images/c_cw_prop.png", 
        "Camera Board":     "images/camera_board.png", 
        "Camera Housing":   "images/camera_housing.png",
        "Camera Screw":     "images/camera_screw.png", 
        "Control Board":    "images/control_board.png", 
        "CW Prop":          "images/cw_prop.png", 
        "Preassembled Frame": "images/frame.png", 
    }
}

def generate_id():
    if not hasattr(generate_id, "counter"):
        generate_id.counter = 0  # Initialize the counter the first time

    if generate_id.counter < 999:
        generate_id.counter += 1
        return f"{generate_id.counter:03d}"
    else:
        generate_id.counter = 0
        return f"{generate_id.counter:03d}"
    

def generate_help_id():
    if not hasattr(generate_help_id, "counter"):
        generate_help_id.counter = 0  # Initialize the counter the first time

    if generate_help_id.counter < 999:
        generate_help_id.counter += 1
        return f"{generate_help_id.counter:03d}"
    else:
        generate_help_id.counter = 0
        return f"{generate_help_id.counter:03d}"
    

def generate_csv(base_directory='data'):
    # Get today's date in DD/MM/YYYY format
    today = datetime.datetime.now().strftime("%d/%m/%Y_%H-%M")
    
    # Convert today's date format to DD-MM-YYYY for directory naming
    subdir_name = today.replace('/', '-')
    
    # Create the path for the new subdirectory within the base directory
    subdirectory_path = os.path.join(base_directory, subdir_name)
    
    # Check if the subdirectory exists, create it if it doesn't
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)
    
    # Initialize the file number
    # file_number = 1
    
    # Generate the initial file name
    #file_name = f"{subdir_name}" #-{file_number}.csv"
    file_name = f"data.csv" #-{file_number}.csv"
    full_path = os.path.join(subdirectory_path, file_name)
    
    # Check if the file already exists, and increment the number until it doesn't
    # while os.path.exists(full_path):
    #     # file_number += 1
    #     file_name = f"{subdir_name}" #-{file_number}.csv"
    #     full_path = os.path.join(subdirectory_path, file_name)

    with open(full_path, 'w', newline='') as csv_file:  # Ensure newline='' for proper line handling in CSV
            # Write the header to the CSV file
            header = ['timestamp', 'Status', 'WS_ID', 'side']
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(header)
    
    # Return the full path to the new file
    return full_path

def save_state_to_csv(csv_file_path, timestamp, status, ws_id, side): #, csv_backup_text):
    # csv_backup_text += f'{timestamp},{status},{ws_id},{side}\n'
    if csv_file_path is not None:
        with open(csv_file_path, 'a', newline='') as csv_file:  # Open the file in append mode
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([timestamp, status, ws_id, side])

