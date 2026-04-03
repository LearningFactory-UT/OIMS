from __future__ import annotations

from datetime import datetime

from auth.access import AccessContext
from auth.security import generate_device_id, generate_device_token, hash_token, token_hint
from db_engine import SessionLocal
from models.db_models import DeviceModel, StationModel
from settings import settings


class AuthService:
    _instance = None

    @staticmethod
    def get_instance():
        if AuthService._instance is None:
            AuthService._instance = AuthService()
        return AuthService._instance

    def __init__(self):
        if AuthService._instance is not None:
            raise Exception("Use AuthService.get_instance() instead.")

    def authenticate_admin(self, username: str, password: str) -> bool:
        return username == settings.admin_username and password == settings.admin_password

    def _device_payload(self, record: DeviceModel) -> dict:
        return {
            "device_id": record.device_id,
            "role": record.role,
            "label": record.label,
            "station_id": record.station_id,
            "enabled": record.enabled,
            "token_hint": record.token_hint,
            "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    def list_devices(self) -> list[dict]:
        session = SessionLocal()
        try:
            records = session.query(DeviceModel).order_by(DeviceModel.created_at.desc()).all()
            return [self._device_payload(record) for record in records]
        finally:
            session.close()

    def create_device(self, role: str, label: str, station_id: str | None = None) -> dict:
        if role not in {"tablet", "inventory"}:
            raise ValueError("Unsupported device role.")
        if role == "tablet" and not station_id:
            raise ValueError("Tablet devices must be bound to a station_id.")
        if role == "inventory":
            station_id = None

        session = SessionLocal()
        try:
            if role == "tablet":
                station_record = (
                    session.query(StationModel)
                    .filter_by(original_ws_id=str(station_id))
                    .first()
                )
                if station_record is None:
                    raise ValueError("A tablet device must target an existing station.")

            raw_token = generate_device_token(role)
            record = DeviceModel(
                device_id=generate_device_id(),
                role=role,
                label=label.strip() or role,
                station_id=str(station_id) if station_id is not None else None,
                token_hash=hash_token(raw_token),
                token_hint=token_hint(raw_token),
                enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            payload = self._device_payload(record)
            payload["token"] = raw_token
            return payload
        finally:
            session.close()

    def update_device(
        self,
        device_id: str,
        *,
        enabled: bool | None = None,
        label: str | None = None,
        station_id: str | None = None,
    ) -> dict:
        session = SessionLocal()
        try:
            record = session.query(DeviceModel).filter_by(device_id=device_id).first()
            if record is None:
                raise ValueError("Unknown device.")

            if enabled is not None:
                record.enabled = bool(enabled)
            if label is not None:
                record.label = label.strip() or record.label
            if record.role == "tablet" and station_id is not None:
                station_record = (
                    session.query(StationModel)
                    .filter_by(original_ws_id=str(station_id))
                    .first()
                )
                if station_record is None:
                    raise ValueError("A tablet device must target an existing station.")
                record.station_id = str(station_id).strip() or record.station_id

            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            return self._device_payload(record)
        finally:
            session.close()

    def rotate_device_token(self, device_id: str) -> dict:
        session = SessionLocal()
        try:
            record = session.query(DeviceModel).filter_by(device_id=device_id).first()
            if record is None:
                raise ValueError("Unknown device.")
            raw_token = generate_device_token(record.role)
            record.token_hash = hash_token(raw_token)
            record.token_hint = token_hint(raw_token)
            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            payload = self._device_payload(record)
            payload["token"] = raw_token
            return payload
        finally:
            session.close()

    def authenticate_device_token(self, raw_token: str) -> dict | None:
        token_hash_value = hash_token(raw_token)
        session = SessionLocal()
        try:
            record = (
                session.query(DeviceModel)
                .filter_by(token_hash=token_hash_value)
                .first()
            )
            if record is None or not record.enabled:
                return None
            record.last_used_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            return self._device_payload(record)
        finally:
            session.close()

    def get_device_access_context(self, device_id: str | None) -> AccessContext | None:
        if not device_id:
            return None

        session = SessionLocal()
        try:
            record = session.query(DeviceModel).filter_by(device_id=device_id).first()
            if record is None or not record.enabled:
                return None
            return AccessContext(
                authenticated=True,
                role=record.role,
                auth_kind="device",
                device_id=record.device_id,
                device_label=record.label,
                station_id=record.station_id,
            )
        finally:
            session.close()
