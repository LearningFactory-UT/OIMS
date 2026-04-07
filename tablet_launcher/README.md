# Tablet Launcher

The tablet launcher is the thin local footprint for the hybrid workstation runtime.

## Provision a device

```bash
python3 provision.py
```

This saves the device role, token, optional station ID, and the configured server URLs into `config.json`.

## Run the launcher

```bash
python3 launcher.py
```

The launcher opens the centrally hosted `tablet` or `inventory` surface in kiosk mode and periodically checks the backend health endpoint.

For local testing on one machine, use:

- `api_base_url`: `http://localhost:3010`
- `ui_base_url`: `http://localhost:3000`

For deployment on a LAN, replace those with the actual hostname of the OIMS server, for example `http://your-oims-server.local`.
