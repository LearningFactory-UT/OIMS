from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import wraps
from threading import Lock
from typing import Optional

from flask import g, jsonify, request, session


@dataclass
class AccessContext:
    authenticated: bool = False
    role: Optional[str] = None
    auth_kind: Optional[str] = None
    device_id: Optional[str] = None
    device_label: Optional[str] = None
    station_id: Optional[str] = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["is_admin"] = self.role == "admin"
        return payload

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def allows_station(self, station_id: str) -> bool:
        if self.is_admin:
            return True
        return self.role == "tablet" and self.station_id == str(station_id)


_socket_contexts: dict[str, AccessContext] = {}
_socket_lock = Lock()


def _cache_context(context: AccessContext) -> AccessContext:
    g.access_context = context
    return context


def clear_auth_session():
    session.pop("auth", None)
    g.pop("access_context", None)


def set_admin_session():
    session["auth"] = {"kind": "admin", "role": "admin"}
    session.modified = True
    _cache_context(AccessContext(authenticated=True, role="admin", auth_kind="admin"))


def set_device_session(device_payload: dict):
    session["auth"] = {
        "kind": "device",
        "role": device_payload["role"],
        "device_id": device_payload["device_id"],
    }
    session.modified = True
    _cache_context(
        AccessContext(
            authenticated=True,
            role=device_payload["role"],
            auth_kind="device",
            device_id=device_payload["device_id"],
            device_label=device_payload["label"],
            station_id=device_payload.get("station_id"),
        )
    )


def get_current_access_context() -> AccessContext:
    cached = getattr(g, "access_context", None)
    if cached is not None:
        return cached

    auth_payload = session.get("auth")
    if not auth_payload:
        return _cache_context(AccessContext())

    if auth_payload.get("kind") == "admin":
        return _cache_context(AccessContext(authenticated=True, role="admin", auth_kind="admin"))

    if auth_payload.get("kind") == "device":
        from services.auth_service import AuthService

        device_context = AuthService.get_instance().get_device_access_context(
            auth_payload.get("device_id")
        )
        if device_context is None:
            clear_auth_session()
        else:
            return _cache_context(device_context)

    raw_device_token = request.headers.get("X-OIMS-Device-Token", "").strip()
    if raw_device_token:
        from services.auth_service import AuthService

        token_context = AuthService.get_instance().get_access_context_for_raw_token(
            raw_device_token
        )
        if token_context is not None:
            return _cache_context(token_context)

    clear_auth_session()
    return _cache_context(AccessContext())


def register_socket_context(sid: str, context: AccessContext):
    with _socket_lock:
        _socket_contexts[sid] = context


def unregister_socket_context(sid: str):
    with _socket_lock:
        _socket_contexts.pop(sid, None)


def get_socket_context(sid: str) -> Optional[AccessContext]:
    with _socket_lock:
        return _socket_contexts.get(sid)


def iter_socket_contexts() -> list[tuple[str, AccessContext]]:
    with _socket_lock:
        return list(_socket_contexts.items())


def require_roles(*roles: str):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            context = get_current_access_context()
            if not context.authenticated:
                return jsonify({"error": "Authentication required"}), 401
            if roles and context.role not in roles:
                return jsonify({"error": "Forbidden"}), 403
            return func(*args, **kwargs)

        return wrapped

    return decorator


def require_station_access(station_id: str) -> AccessContext:
    context = get_current_access_context()
    if not context.authenticated:
        raise PermissionError("Authentication required")
    if not context.allows_station(station_id):
        raise PermissionError(f"Access to station '{station_id}' is forbidden.")
    return context


def forbid_unless_order_owner(order_station_id: str) -> AccessContext:
    context = get_current_access_context()
    if not context.authenticated:
        raise PermissionError("Authentication required")
    if context.is_admin:
        return context
    if context.role != "tablet" or context.station_id != str(order_station_id):
        raise PermissionError(
            f"Access to order station '{order_station_id}' is forbidden for this device."
        )
    return context
