# OIMS

OIMS is an ordering and inventory management system for a learning-factory drone assembly line. This repository now contains the three runtime pieces together:

- `inventory_server/`: central backend plus web control-plane and web workstation UI
- `workstation/`: legacy local Python tablet client kept for compatibility during migration
- `esp32/`: andon light firmware
- `tablet_launcher/`: thin launcher/provisioning scaffold for the hybrid tablet runtime

## Architecture

- The central backend is the system of record for timer state, stations, orders, operator-side state, and andon light state.
- MQTT topic compatibility is preserved for the current `v1` contract so the external timer sender and ESP32 devices keep working.
- The new workstation runtime is browser-based and centrally hosted; the local tablet footprint is reduced to a thin launcher/provisioning script.
- The admin, inventory, and tablet surfaces are now compartmentalized:
  - `/admin` requires admin login
  - `/inventory` requires an inventory device token
  - `/tablet` requires a tablet device token bound to one station
- The legacy Python workstation remains available while the web workstation reaches parity.

## Local Development

### Backend

```bash
cd inventory_server/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

The backend listens on `http://localhost:3010` by default.

### Frontend

```bash
cd inventory_server/frontend
npm install
npm start
```

The frontend dev server runs on `http://localhost:3000` and targets the backend configured in `public/runtime-config.js` or the host fallback logic.

### Legacy Workstation

```bash
cd workstation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### Tablet Launcher

```bash
cd tablet_launcher
python3 provision.py
python3 launcher.py
```

## Deployment

- Production on a configurable OIMS server host: [docs/server-deployment.md](/Users/giovannichiementin/Desktop/Work%20in%20progress/OIMS/docs/server-deployment.md)
- Docker Compose: `docker compose up --build`
- Native service examples: `deploy/systemd/`

For production, do not hardcode a factory-specific server name. Set the actual LAN hostname through `.env`, launcher config, and device config.

## MQTT Contract

The preserved `v1` MQTT topics and payloads are documented in [docs/mqtt-v1.md](/Users/giovannichiementin/Desktop/Work%20in%20progress/OIMS/docs/mqtt-v1.md).
