# Tablet Launcher

The tablet launcher is the thin local footprint for the hybrid workstation runtime.

## Provision a tablet

```bash
python3 provision.py
```

This saves the selected station ID into `config.json`.

## Run the launcher

```bash
python3 launcher.py
```

The launcher opens the centrally hosted workstation URL in kiosk mode and periodically checks the backend health endpoint.

