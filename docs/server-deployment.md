# OIMS Server Deployment Guide

This is the recommended production flow for OIMS 2.0 on the Ubuntu-based machine that will host the OIMS server. The machine hostname is configurable and should be supplied through deployment configuration, not hardcoded in the codebase.

## 1. Prerequisites

- Docker Engine with the Compose plugin
- The production Mosquitto broker already reachable at `<broker-hostname>:1883`
- DNS or mDNS resolution for your chosen OIMS server hostname on the factory LAN

## 2. Install the stack

```bash
sudo mkdir -p /opt/oims
sudo chown "$USER":"$USER" /opt/oims
git clone https://github.com/LearningFactory-UT/OIMS.git /opt/oims
cd /opt/oims
git switch oims-2.0
cp .env.example .env
```

Edit `.env` and set at least:

- `OIMS_SECRET_KEY`
- `OIMS_ADMIN_USERNAME`
- `OIMS_ADMIN_PASSWORD`
- `OIMS_BROKER_HOSTNAME=<broker-hostname>`
- `OIMS_CORS_ORIGINS=http://<oims-server-hostname>`

## 3. Start the services

```bash
docker compose up -d --build
```

The production stack serves:

- frontend and reverse proxy at `http://<oims-server-hostname>`
- backend internally on `backend:3010`

The backend database is persisted at `./data/backend/oims.db`.

## 4. First admin login

Open `http://<oims-server-hostname>/admin` and sign in with the admin credentials from `.env`.

From the admin surface:

1. Create each station with its stable numeric ID, for example `2`.
2. Keep `Display name` UI-only.
3. Create one `tablet` device token per station.
4. Create one `inventory` device token for the inventory display.

Copy each token immediately after creation or rotation. The UI only shows the full token once.

## 5. Tablet setup

On each tablet:

```bash
cd tablet_launcher
python3 provision.py
python3 launcher.py
```

Enter:

- role: `tablet`
- stable station ID: for example `2`
- device token: the admin-issued tablet token

The launcher opens:

- `http://<oims-server-hostname>/tablet?token=...`

The tablet surface remembers the locally stored station assignment and is restricted to that single workstation.

## 6. Inventory display setup

On the inventory screen:

```bash
cd tablet_launcher
python3 provision.py
python3 launcher.py
```

Enter:

- role: `inventory`
- device token: the admin-issued inventory token

The launcher opens:

- `http://<oims-server-hostname>/inventory?token=...`

This surface is read-only and only shows the orders board.

## 7. Verification

Backend health:

```bash
curl http://<oims-server-hostname>/api/system/health
```

Watch MQTT orders on the live broker:

```bash
mosquitto_sub -h <broker-hostname> -t /ws_manager/orders -v
```

Create an order from station `2` and verify the payload contains:

```json
"attributes": {
  "ws_id": "2"
}
```

## 8. Operational notes

- Admin surface: `http://<oims-server-hostname>/admin`
- Inventory surface: `http://<oims-server-hostname>/inventory`
- Tablet surface: `http://<oims-server-hostname>/tablet`
- Legacy workstation Python client remains in the repo for compatibility testing, but the production path is the web tablet plus launcher flow.
