# backend/services/andon_service.py
import json
import threading

class AndonService:
    _instance = None

    @staticmethod
    def get_instance():
        if AndonService._instance is None:
            AndonService._instance = AndonService()
        return AndonService._instance
    
    def set_mqtt_service(self, mqtt_svc):
        self.mqtt_service = mqtt_svc

    def __init__(self):
        if AndonService._instance is not None:
            raise Exception("Use AndonService.get_instance() instead.")
        self.mqtt_service = None
        # self.json_file_path = "workstation_colors.json"
        # self.start_periodic_update()

    def update_lights(self, ws_id, side, image_name):
        """
        For debugging + publish color code to /ws_manager/update_lights
        """
        print(f"[AndonService]: Updating lights for {ws_id}, side={side}, -> {image_name}")

        # # Update the JSON file with the new color
        # self.update_json_file(ws_id, side, image_name)

        # We keep "original_ws_id" because ortherwise we should update the ESP32 code
        payload = {
            "original_ws_id": ws_id,
            "side": side,
            "image_name": image_name
        }
        self.mqtt_service.publish(
            topic="/ws_manager/update_lights",
            payload=json.dumps(payload)
        )

    # def update_json_file(self, ws_id, side, image_name):
    #     # Read the current data from the JSON file
    #     with open(self.json_file_path, 'r') as json_file:
    #         data = json.load(json_file)

    #     # Update the data with the new color
    #     if ws_id not in data:
    #         data[ws_id] = {}
    #     data[ws_id][side] = image_name

    #     # Write the updated data back to the JSON file
    #     with open(self.json_file_path, 'w') as json_file:
    #         json.dump(data, json_file)

    # def start_periodic_update(self):
    #     # Schedule the first call
    #     self.send_json_file_content()
    #     # Schedule subsequent calls every 30 seconds
    #     threading.Timer(30.0, self.start_periodic_update).start()

    # def send_json_file_content(self):
    #     # Read the JSON file content
    #     with open(self.json_file_path, 'r') as json_file:
    #         data = json.load(json_file)

    #     # Send the data as a message
    #     for ws_id, sides in data.items():
    #         for side, image_name in sides.items():
    #             self.mqtt_service.publish(
    #                 topic="/ws_manager/update_lights",
    #                 payload=json.dumps({
    #                     "original_ws_id": ws_id,
    #                     "side": side,
    #                     "image_name": image_name
    #                 })
    #             )