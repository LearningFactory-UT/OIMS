# OIMS MQTT v1 Contract

These topics are preserved for the first centralization wave.

## Timer

- Topic: `/ws_manager/timer`
- Payload:

```json
{"command":"start","seconds":1800,"initiator":"data_manager"}
```

Supported commands: `start`, `stop`, `pause`, `resume`.

## Orders

- Topic: `/ws_manager/orders`
- Payload:

```json
{
  "items": {"Motor": 2, "Drone Frame": 1},
  "attributes": {
    "ws_id": "5",
    "operator_side": "L",
    "urgent": false,
    "order_id": "WS5_001"
  }
}
```

## Order Updates

- Topic: `/ws_manager/update_order`
- Payload:

```json
{"order_id":"WS5_001","urgent":true}
```

## Order Removal

- Legacy typo topic: `/ws_manager/delete_oder`
- Canonical topic: `/ws_manager/delete_order`
- Payload:

```json
{"order_id":"WS5_001"}
```

## Delivered Orders

- Topic: `/ws_manager/order_delivered`
- Payload:

```json
{"order_id":"WS5_001"}
```

## Help Requests

- Topic: `/ws_manager/help_request`
- Payload:

```json
{"help_id":"WS5_HELP_001","ws_id":"5","side":"L","help":true,"idle":false}
```

## Waiting From Previous Workstation

- Topic: `/ws_manager/order_from_previous_ws`
- Payload:

```json
{"prev_ws_order_id":"WS5_prev_ws_order_001","ws_id":"5","side":"L","pending":true,"idle":false}
```

## Ready For Next Workstation

- Topic: `/ws_manager/order_for_next_ws`
- Payload:

```json
{"ready_for_next_id":"WS5_ready_for_next_001","ws_id":"5","side":"L","ready":true}
```

## Manual Operator State

- Topic: `/ws_manager/manual_state`
- Payload:

```json
{"original_ws_id":"5","side":"L","manual_command":"start"}
```

Supported commands: `start`, `stop`, `reset`.

## Station Registration And Snapshot

- Topic: `/ws_manager/set_ws_id`

```json
{"ws_id":"WS-5","original_ws_id":"5"}
```

- Topic: `/ws_manager/set_ws_id_response`

```json
{"original_ws_id":"5","ws_id":"WS-5"}
```

- Topic: `/ws_manager/set_ws_info`

Carries a full workstation snapshot during reconnect or identify flows.

## Identify

- Topic: `/ws_manager/identify`
- Empty payload or any JSON payload. Legacy clients respond with `set_ws_id` and `set_ws_info`.

## Assembly Type

- Topic: `/ws_manager/set_assembly_type`

```json
{"assembly_type":"standard"}
```

## Workstation Enable/Disable

- Topic: `/ws_manager/disable_workstation`
- Topic: `/ws_manager/enable_workstation`

```json
{"original_ws_ids":["5"]}
```

## ESP32 Light Updates

- Topic: `/ws_manager/update_lights`

```json
{"original_ws_id":"5","side":"L","image_name":"GbB"}
```

