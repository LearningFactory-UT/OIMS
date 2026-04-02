from __future__ import annotations

from dataclasses import dataclass

from domain.entities import AndonState, ManualState, OperatorSide


@dataclass
class AndonInputs:
    station_id: str
    side: OperatorSide
    timer_running: bool
    enabled: bool
    manual_state: ManualState
    pending_orders: int
    urgent_orders: int
    help_requested: bool
    help_idle: bool
    waiting_from_previous: bool
    waiting_from_previous_idle: bool
    ready_for_next: bool


def derive_andon_state(inputs: AndonInputs) -> AndonState:
    active = any(
        [
            inputs.pending_orders > 0,
            inputs.help_requested,
            inputs.waiting_from_previous,
            inputs.ready_for_next,
            inputs.manual_state in {"start", "stop"},
        ]
    )
    idle = (
        inputs.urgent_orders > 0
        or inputs.help_idle
        or inputs.waiting_from_previous_idle
        or not inputs.enabled
    )
    stopped = inputs.manual_state == "stop"

    if not inputs.timer_running or not inputs.enabled or not active:
        code = "R"
    else:
        code = "R" if idle or stopped else "G"
        if inputs.ready_for_next:
            code += "g"
        if inputs.help_requested:
            code += "Y"
        if inputs.waiting_from_previous:
            code += "b"
        if inputs.pending_orders > 0:
            code += "B"

    return AndonState(
        station_id=inputs.station_id,
        side=inputs.side,
        code=code,
        active=active,
        idle=idle,
        stopped=stopped,
    )

