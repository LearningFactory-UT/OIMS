import json

def read_json():
    # Open and load the configuration file for the specific ESP32 type
    with open('config.json') as f:
        config = json.load(f)
    
    # config = {'broker_hostname':____ , 'original_ws_id':____}

    return config