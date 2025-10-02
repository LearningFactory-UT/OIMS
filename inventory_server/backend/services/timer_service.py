from datetime import datetime, timedelta, UTC
import threading
import time
from socketio_instance import socketio
from db_engine import SessionLocal
from models.db_models import TimerModel
from services.andon_service import AndonService
import json

# mqtt_service = None

# def init_timer_service(mqtt_svc):
#     """
#     Called once from run.py to inject actual references.
#     """
#     global mqtt_service
#     mqtt_service = mqtt_svc


class TimerService:
    _instance = None

    @staticmethod
    def get_instance():
        if TimerService._instance is None:
            TimerService._instance = TimerService()
        return TimerService._instance

    def __init__(self):
        if TimerService._instance is not None:
            raise Exception("Use TimerService.get_instance() instead.")
        
        self.andon_service = AndonService.get_instance()

        self.timer_running = False
        self.start_time = None
        self.end_time = None
        self.paused_time = 0
        self._thread = None
        self.lock = threading.Lock()
        self.remaining_seconds = 0

    def start_timer(self, seconds: int):
        with self.lock:
            if self.timer_running:
                return
            self.start_time = datetime.now()
            self.end_time = self.start_time + timedelta(seconds=seconds)
            self.remaining_seconds = seconds
            self.timer_running = True
            self.paused_time = 0

        # # Create an empty JSON file
        # self.create_empty_json_file()

        session = SessionLocal()
        try:
            timer_rec = session.query(TimerModel).get(1)
            if not timer_rec:
                timer_rec = TimerModel(id=1)
                session.add(timer_rec)
            timer_rec.timer_running = True
            timer_rec.start_time = datetime.now(UTC)
            timer_rec.total_seconds = seconds
            session.commit()
        except Exception as exc:
            session.rollback()
            print("DB error while starting timer:", exc)
        finally:
            session.close()

        self._thread = threading.Thread(target=self._run_timer, daemon=True)
        self._thread.start()
        print(f"[TimerService]: Timer started for {seconds} seconds.")
        socketio.emit("timer_start", {"duration": seconds})
        socketio.emit("timer_state_changed", {"state": "started"})

    def _run_timer(self):
        while True:
            time.sleep(1)
            with self.lock:
                if not self.timer_running:
                    break
                now = datetime.now()
                self.remaining_seconds = int((self.end_time - now).total_seconds())
                if self.remaining_seconds <= 0:
                    self.remaining_seconds = 0
                    self.timer_running = False
                    break
        if self.remaining_seconds == 0:
            self._on_timer_end()

    def _on_timer_end(self):
        print("TimerService: Timer ended.")
        from services.inventory_service import InventoryService
        InventoryService.get_instance().clear_all_orders(reason="timer")
        socketio.emit("timer_ended", {"message": "Timer ended"})
        
        # LET'S NOT DO THIS ANYMORE to avoid lights turning off in an unscheduled way
        # Schedule light update after 30 seconds
        #threading.Timer(30.0, lambda: self.andon_service.update_lights(ws_id='ALL', side='ALL', image_name='')).start()

    def pause_timer(self):
        with self.lock:
            if self.timer_running:
                self.paused_time = self.remaining_seconds
                self.timer_running = False
                socketio.emit("timer_pause", {"paused_time": self.paused_time})
                print("TimerService: Timer paused.")

    def resume_timer(self):
        with self.lock:
            secs = 0
            if not self.timer_running and self.paused_time > 0:
                secs = self.paused_time
                self.paused_time = 0
                socketio.emit("timer_resume", {"remaining": secs})
                print("TimerService: Timer resumed.")
        if secs:
            self.start_timer(secs)

    def stop_timer(self):
        with self.lock:
            self.timer_running = False
            self.remaining_seconds = 0
            self.paused_time = 0
        from services.inventory_service import InventoryService
        InventoryService.get_instance().clear_all_orders(reason="timer")
        socketio.emit("timer_stop", {})
        print("TimerService: Timer stopped.")

    def get_remaining_seconds(self):
        with self.lock:
            now = datetime.now()
            self.remaining_seconds = int((self.end_time - now).total_seconds())
            return self.remaining_seconds
    
    def is_timer_running(self):
        return self.timer_running

    # def create_empty_json_file(self):
    #     # Define the path for the JSON file
    #     self.json_file_path = "workstation_colors.json"
    #     # Create an empty dictionary with the desired structure
    #     data = {}
    #     # Write the empty structure to the JSON file
    #     with open(self.json_file_path, 'w') as json_file:
    #         json.dump(data, json_file)