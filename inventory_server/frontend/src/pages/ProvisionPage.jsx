import React, { useEffect, useMemo, useState } from "react";

import DecisionModal from "../components/DecisionModal";
import { apiFetch } from "../lib/api";

function formatDeviceUsage(device) {
  if (!device.last_used_at) {
    return "never used";
  }
  return new Date(device.last_used_at).toLocaleString();
}

export default function ProvisionPage({ systemState, onOpenWorkstation, onRefreshState }) {
  const devices = systemState.devices || [];
  const [stationId, setStationId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);

  const [deviceRole, setDeviceRole] = useState("tablet");
  const [deviceLabel, setDeviceLabel] = useState("");
  const [deviceStationId, setDeviceStationId] = useState("");
  const [deviceBusy, setDeviceBusy] = useState(false);
  const [issuedDevice, setIssuedDevice] = useState(null);
  const [stationToDelete, setStationToDelete] = useState(null);

  const stationsById = useMemo(
    () =>
      Object.fromEntries(
        systemState.stations.map((station) => [station.station_id, station])
      ),
    [systemState.stations]
  );

  useEffect(() => {
    onRefreshState?.();
  }, [onRefreshState]);

  async function createStation(event) {
    event.preventDefault();
    if (!stationId.trim()) {
      return;
    }

    setBusy(true);
    try {
      const station = await apiFetch("/api/stations/register", {
        method: "POST",
        body: JSON.stringify({
          station_id: stationId.trim(),
          display_name: displayName.trim() || stationId.trim(),
          client_type: "tablet-launcher",
          provisioned_by: "browser",
        }),
      });
      await onRefreshState?.();
      onOpenWorkstation(station.station_id);
    } finally {
      setBusy(false);
    }
  }

  async function createDevice(event) {
    event.preventDefault();
    if (!deviceLabel.trim()) {
      return;
    }
    if (deviceRole === "tablet" && !deviceStationId.trim()) {
      return;
    }

    setDeviceBusy(true);
    try {
      const device = await apiFetch("/api/auth/devices", {
        method: "POST",
        body: JSON.stringify({
          role: deviceRole,
          label: deviceLabel.trim(),
          station_id: deviceRole === "tablet" ? deviceStationId.trim() : null,
        }),
      });
      setIssuedDevice(device);
      setDeviceLabel("");
      await onRefreshState?.();
    } finally {
      setDeviceBusy(false);
    }
  }

  async function toggleDevice(device, enabled) {
    setDeviceBusy(true);
    try {
      const updatedDevice = await apiFetch(`/api/auth/devices/${device.device_id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      });
      setIssuedDevice((current) =>
        current?.device_id === updatedDevice.device_id ? updatedDevice : current
      );
      await onRefreshState?.();
    } finally {
      setDeviceBusy(false);
    }
  }

  async function rotateDevice(deviceId) {
    setDeviceBusy(true);
    try {
      const rotated = await apiFetch(`/api/auth/devices/${deviceId}/rotate`, {
        method: "POST",
      });
      setIssuedDevice(rotated);
      await onRefreshState?.();
    } finally {
      setDeviceBusy(false);
    }
  }

  async function confirmDeleteStation() {
    if (!stationToDelete) {
      return;
    }

    setBusy(true);
    try {
      await apiFetch(`/api/stations/${stationToDelete.station_id}`, {
        method: "DELETE",
      });
      await onRefreshState?.();
      if (deviceStationId === stationToDelete.station_id) {
        setDeviceStationId("");
      }
      setStationToDelete(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="panel split-panel">
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Provisioning</p>
              <h2>Existing stations</h2>
            </div>
          </div>
          <div className="station-grid">
            {systemState.stations.map((station) => {
              const boundDevices = devices.filter(
                (device) =>
                  device.role === "tablet" && device.station_id === station.station_id
              );

              return (
                <article key={station.station_id} className="station-card">
                  <h3>{station.display_name}</h3>
                  <p className="station-meta">Stable ID: {station.station_id}</p>
                  <p className="station-meta">
                    Tablet devices: {boundDevices.length || 0}
                  </p>
                  <div className="button-row wrap">
                    <button
                      className="primary-button"
                      onClick={() => onOpenWorkstation(station.station_id)}
                    >
                      Open workstation
                    </button>
                    <button
                      className="danger-button"
                      disabled={busy}
                      onClick={() => setStationToDelete(station)}
                    >
                      Delete workstation
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Provisioning</p>
              <h2>Create a station</h2>
            </div>
          </div>
          <form className="form-stack" onSubmit={createStation}>
            <label className="field">
              <span>Stable station ID</span>
              <input
                value={stationId}
                onChange={(event) => setStationId(event.target.value)}
                placeholder="2"
              />
            </label>
            <label className="field">
              <span>Display name (UI only)</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="WS-02"
              />
            </label>
            <button className="primary-button" disabled={busy} type="submit">
              Create and open workstation
            </button>
          </form>
        </div>
      </section>

      <section className="panel split-panel">
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Device Access</p>
              <h2>Create a device token</h2>
            </div>
          </div>
          <form className="form-stack" onSubmit={createDevice}>
            <label className="field">
              <span>Surface role</span>
              <select
                value={deviceRole}
                onChange={(event) => setDeviceRole(event.target.value)}
              >
                <option value="tablet">Tablet</option>
                <option value="inventory">Inventory</option>
              </select>
            </label>
            <label className="field">
              <span>Label</span>
              <input
                value={deviceLabel}
                onChange={(event) => setDeviceLabel(event.target.value)}
                placeholder="Tablet at station 2"
              />
            </label>
            {deviceRole === "tablet" ? (
              <label className="field">
                <span>Bound station ID</span>
                <select
                  value={deviceStationId}
                  onChange={(event) => setDeviceStationId(event.target.value)}
                >
                  <option value="">Select a station</option>
                  {systemState.stations.map((station) => (
                    <option key={station.station_id} value={station.station_id}>
                      {station.station_id}
                      {station.display_name !== station.station_id
                        ? ` · ${station.display_name}`
                        : ""}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <button className="primary-button" disabled={deviceBusy} type="submit">
              Create device token
            </button>
          </form>

          {issuedDevice?.token ? (
            <div className="token-panel">
              <p className="eyebrow">Copy Once</p>
              <h3>{issuedDevice.label}</h3>
              <p className="muted-copy">
                Store this token in the tablet launcher or inventory kiosk configuration.
              </p>
              <div className="token-value">{issuedDevice.token}</div>
            </div>
          ) : null}
        </div>

        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Device Access</p>
              <h2>Issued devices</h2>
            </div>
          </div>
          <div className="device-list">
            {devices.map((device) => (
              <article key={device.device_id} className="device-card">
                <div className="station-card-header">
                  <div>
                    <h3>{device.label}</h3>
                    <p className="station-meta">
                      {device.role}
                      {device.station_id ? ` · station ${device.station_id}` : ""}
                    </p>
                  </div>
                  <span className={device.enabled ? "badge badge-online" : "badge badge-offline"}>
                    {device.enabled ? "enabled" : "disabled"}
                  </span>
                </div>
                <p className="station-meta">
                  Token hint: {device.token_hint} · Last used: {formatDeviceUsage(device)}
                </p>
                <div className="button-row wrap">
                  <button
                    className={device.enabled ? "danger-button" : "primary-button"}
                    disabled={deviceBusy}
                    onClick={() => toggleDevice(device, !device.enabled)}
                  >
                    {device.enabled ? "Disable" : "Enable"}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={deviceBusy}
                    onClick={() => rotateDevice(device.device_id)}
                  >
                    Rotate token
                  </button>
                </div>
                {device.station_id ? (
                  <p className="station-meta">
                    Display name: {stationsById[device.station_id]?.display_name || device.station_id}
                  </p>
                ) : null}
              </article>
            ))}
            {devices.length === 0 ? (
              <p className="muted-copy">No devices have been provisioned yet.</p>
            ) : null}
          </div>
        </div>
      </section>

      {stationToDelete ? (
        <DecisionModal
          title="Delete workstation"
          message={`Delete workstation ${stationToDelete.display_name} (${stationToDelete.station_id})? This will remove its active orders and bound tablet devices.`}
          confirmLabel="Delete workstation"
          cancelLabel="Cancel"
          onConfirm={confirmDeleteStation}
          onCancel={() => setStationToDelete(null)}
        />
      ) : null}
    </div>
  );
}
