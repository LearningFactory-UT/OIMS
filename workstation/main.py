import json

# Load the config.json file
with open('config.json', 'r') as file:
    config = json.load(file)

# Retrieve the ws_id from the config
ws_type = config['station_type']

if ws_type == "workstation":
    import workstation
    workstation.main()
elif ws_type == "inventory":
    import inventory
    inventory.main()

    
