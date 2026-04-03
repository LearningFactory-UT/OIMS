# Tablet Launcher

The tablet launcher is the thin local footprint for the hybrid workstation runtime.

## Provision a device

```bash
python3 provision.py
```

This saves the device role, token, and optional station ID into `config.json`.

## Run the launcher

```bash
python3 launcher.py
```

The launcher opens the centrally hosted `tablet` or `inventory` surface in kiosk mode and periodically checks the backend health endpoint.
