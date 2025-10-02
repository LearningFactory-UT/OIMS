from datetime import datetime, timedelta
import time
import customtkinter as ctk

# TODO: implement to_serializable_dict()

class TimerApp(ctk.CTkFrame):
    def __init__(self, upper_class_instance, timer_text):
        super().__init__(upper_class_instance)
        self.upper_class_instance = upper_class_instance
        self.timer_text = timer_text
        self.timer_text.set("Remaining time: 00:00")
        self.timer_running = False
        self.paused_time = None
        self.after_id = None  # To keep track of the scheduled 'after' call
        self.remaining_seconds = timedelta(seconds=0)

    def to_serializable_dict(self):
        return None

    def start_timer(self, seconds):
        if not self.timer_running:
            self.reset_timer_state()  # Ensure timer state is reset before starting
            self.upper_class_instance.enable_workstation()
            self.end_time = datetime.now() + timedelta(seconds=seconds)
            self.timer_running = True
            self.paused_time = None
            self.schedule_update()
            print('TIMER STARTED')


    def schedule_update(self):
        if self.timer_running:
            self.after_id = self.after(1000, self.update_timer)


    def update_timer(self):
        self.remaining_seconds = self.end_time - datetime.now()
        if self.remaining_seconds.total_seconds() > 0:
            minutes, seconds = divmod(int(self.remaining_seconds.total_seconds()), 60)
            time_string = f"Remaining time: {minutes:02d}:{seconds:02d}"
            self.timer_text.set(time_string)
            self.schedule_update()
        else:
            self.timer_text.set("Remaining time: 00:00")
            self.timer_running = False
            self.after_cancel(self.after_id)
            self.after_id = None  # Reset after_id
            self.upper_class_instance.disable_workstation()
            self.send_timer_end()


    def pause_timer(self):
        if self.timer_running and self.after_id:
            self.upper_class_instance.disable_workstation()
            self.after_cancel(self.after_id)
            self.paused_time = (self.end_time - datetime.now()).total_seconds()
            self.timer_running = False
            self.after_id = None  # Reset after_id


    def stop_timer(self):
        self.upper_class_instance.disable_workstation()
        if self.after_id:
            self.after_cancel(self.after_id)
        self.reset_timer_state()
        self.send_timer_end()



    def resume_timer(self):
        if self.paused_time:
            self.start_timer(self.paused_time)

    def send_timer_end(self):
        # Notify upper_class_instance that the timer has ended
        self.upper_class_instance.timer_end()
     
    def reset_timer_state(self):
        """Resets the timer's state to allow for a fresh start."""
        self.timer_running = False
        self.timer_text.set("Remaining time: 00:00")
        self.paused_time = None
        self.remaining_seconds = timedelta(seconds=0)
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None  # Ensure no pending updates are left