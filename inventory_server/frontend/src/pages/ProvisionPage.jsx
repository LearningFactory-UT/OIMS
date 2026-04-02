import React, { useState } from "react";

import { apiFetch } from "../lib/api";

export default function ProvisionPage({ systemState, onOpenWorkstation }) {
  const [stationId, setStationId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);

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
      onOpenWorkstation(station.station_id);
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
            {systemState.stations.map((station) => (
              <article key={station.station_id} className="station-card">
                <h3>{station.display_name}</h3>
                <p className="station-meta">{station.station_id}</p>
                <button
                  className="primary-button"
                  onClick={() => onOpenWorkstation(station.station_id)}
                >
                  Open workstation
                </button>
              </article>
            ))}
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
                placeholder="station-05"
              />
            </label>
            <label className="field">
              <span>Display name</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="WS-05"
              />
            </label>
            <button className="primary-button" disabled={busy} type="submit">
              Create and open workstation
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

