from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from db_engine import SessionLocal
from models.db_models import TimerModel
from socketio_instance import socketio


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

        self.lock = threading.Lock()
        self.state = "stopped"
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.paused_seconds = 0
        self._thread: threading.Thread | None = None

        self._load_from_db()

    # ------------------------------------------------------------------
    # Persistence and recovery
    # ------------------------------------------------------------------
    def _load_from_db(self):
        session = SessionLocal()
        try:
            record = session.get(TimerModel, 1)
            if record is None:
                record = TimerModel(id=1)
                session.add(record)
                session.commit()

            self.state = record.state or "stopped"
            self.start_time = record.start_time
            self.total_seconds = record.total_seconds or 0
            self.paused_seconds = record.paused_seconds or 0
            self.remaining_seconds = self.paused_seconds

            if self.state == "running" and self.start_time:
                self.end_time = self.start_time + timedelta(seconds=self.total_seconds)
                self.remaining_seconds = max(
                    0, int((self.end_time - datetime.utcnow()).total_seconds())
                )
                if self.remaining_seconds <= 0:
                    self._set_stopped_state(persist=True, emit=False)
                    from services.inventory_service import InventoryService

                    InventoryService.get_instance().clear_all_orders(reason="timer")
                else:
                    self._ensure_thread()
            elif self.state == "paused":
                self.end_time = None
                self.remaining_seconds = self.paused_seconds
            else:
                self._set_stopped_state(persist=False, emit=False)
        finally:
            session.close()

    def _persist_state(self):
        session = SessionLocal()
        try:
            record = session.get(TimerModel, 1)
            if record is None:
                record = TimerModel(id=1)
                session.add(record)

            record.state = self.state
            record.timer_running = self.state == "running"
            record.start_time = self.start_time
            record.total_seconds = self.total_seconds
            record.paused_seconds = self.paused_seconds
            record.updated_at = datetime.utcnow()
            session.commit()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Internal state management
    # ------------------------------------------------------------------
    def _set_stopped_state(self, persist: bool = True, emit: bool = True):
        self.state = "stopped"
        self.start_time = None
        self.end_time = None
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.paused_seconds = 0
        if persist:
            self._persist_state()
        if emit:
            self._emit_timer_events("stop")

    def _ensure_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_timer, daemon=True)
        self._thread.start()

    def _run_timer(self):
        while True:
            time.sleep(1)
            with self.lock:
                if self.state != "running" or self.end_time is None:
                    return
                self.remaining_seconds = max(
                    0, int((self.end_time - datetime.utcnow()).total_seconds())
                )
                if self.remaining_seconds > 0:
                    continue
                self._set_stopped_state(persist=True, emit=False)
            self._on_timer_end()
            return

    def _notify_snapshot_refresh(self):
        from services.inventory_service import InventoryService

        inventory_service = InventoryService.get_instance()
        inventory_service.sync_all_andon_states(emit=False)
        inventory_service.emit_state_snapshot()

    def _emit_timer_events(self, action: str):
        snapshot = self.snapshot().to_dict()
        socketio.emit("timer_state", snapshot)

        if action == "start":
            socketio.emit("timer_start", {"duration": snapshot["remaining_seconds"]})
            socketio.emit("timer_state_changed", {"state": "started"})
        elif action == "pause":
            socketio.emit("timer_pause", {"paused_time": snapshot["paused_seconds"]})
            socketio.emit("timer_state_changed", {"state": "paused"})
        elif action == "resume":
            socketio.emit("timer_resume", {"remaining": snapshot["remaining_seconds"]})
            socketio.emit("timer_state_changed", {"state": "resumed"})
        elif action == "stop":
            socketio.emit("timer_stop", {})
            socketio.emit("timer_state_changed", {"state": "stopped"})
        elif action == "ended":
            socketio.emit("timer_ended", {"message": "Timer ended"})
            socketio.emit("timer_state_changed", {"state": "ended"})

        self._notify_snapshot_refresh()

    def _on_timer_end(self):
        from services.inventory_service import InventoryService

        InventoryService.get_instance().clear_all_orders(reason="timer")
        self._emit_timer_events("ended")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def apply_command(self, command: str, seconds: int = 0, source: str = "api") -> bool:
        if command == "start":
            return self.start_timer(seconds, source=source)
        if command == "stop":
            return self.stop_timer(source=source)
        if command == "pause":
            return self.pause_timer(source=source)
        if command == "resume":
            return self.resume_timer(source=source)
        raise ValueError(f"Unsupported timer command '{command}'.")

    def start_timer(self, seconds: int, source: str = "api") -> bool:
        seconds = int(seconds)
        if seconds <= 0:
            raise ValueError("Timer duration must be greater than zero.")

        with self.lock:
            self.state = "running"
            self.start_time = datetime.utcnow()
            self.end_time = self.start_time + timedelta(seconds=seconds)
            self.total_seconds = seconds
            self.remaining_seconds = seconds
            self.paused_seconds = 0
            self._persist_state()
            self._ensure_thread()

        self._emit_timer_events("start")
        return True

    def pause_timer(self, source: str = "api") -> bool:
        with self.lock:
            if self.state != "running":
                return False
            self.remaining_seconds = max(
                0, int((self.end_time - datetime.utcnow()).total_seconds())
            )
            self.paused_seconds = self.remaining_seconds
            self.state = "paused"
            self.end_time = None
            self.start_time = None
            self._persist_state()

        self._emit_timer_events("pause")
        return True

    def resume_timer(self, source: str = "api") -> bool:
        with self.lock:
            if self.state != "paused" or self.paused_seconds <= 0:
                return False
            remaining = self.paused_seconds
            self.state = "running"
            self.start_time = datetime.utcnow()
            self.end_time = self.start_time + timedelta(seconds=remaining)
            self.total_seconds = remaining
            self.remaining_seconds = remaining
            self.paused_seconds = 0
            self._persist_state()
            self._ensure_thread()

        self._emit_timer_events("resume")
        return True

    def stop_timer(self, source: str = "api") -> bool:
        with self.lock:
            was_active = self.state in {"running", "paused"}
            self._set_stopped_state(persist=True, emit=False)

        if was_active:
            from services.inventory_service import InventoryService

            InventoryService.get_instance().clear_all_orders(reason="timer")
        self._emit_timer_events("stop")
        return was_active

    def get_remaining_seconds(self) -> int:
        with self.lock:
            if self.state == "running" and self.end_time is not None:
                self.remaining_seconds = max(
                    0, int((self.end_time - datetime.utcnow()).total_seconds())
                )
                return self.remaining_seconds
            if self.state == "paused":
                return self.paused_seconds
            return 0

    def is_timer_running(self) -> bool:
        return self.state == "running"

    def snapshot(self):
        from domain.entities import TimerState

        return TimerState(
            state=self.state,
            total_seconds=self.total_seconds,
            remaining_seconds=self.get_remaining_seconds(),
            paused_seconds=self.paused_seconds,
            start_time=self.start_time,
        )
