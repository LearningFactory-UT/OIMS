class AndonService:
    _instance = None

    @staticmethod
    def get_instance():
        if AndonService._instance is None:
            AndonService._instance = AndonService()
        return AndonService._instance

    def __init__(self):
        if AndonService._instance is not None:
            raise Exception("Use AndonService.get_instance() instead.")
        self.mqtt_service = None

    def set_mqtt_service(self, mqtt_svc):
        self.mqtt_service = mqtt_svc

    def update_lights(self, ws_id: str, side: str, image_name: str):
        if self.mqtt_service is None:
            return

        self.mqtt_service.publish(
            topic="/ws_manager/update_lights",
            payload={
                "original_ws_id": ws_id,
                "side": side,
                "image_name": image_name,
            },
        )
