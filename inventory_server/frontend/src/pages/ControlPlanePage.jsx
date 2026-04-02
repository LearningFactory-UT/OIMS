import React, { useEffect, useMemo, useState } from "react";

import { apiFetch } from "../lib/api";
import { formatTimer, parseServerDate } from "../timerUtils";

function formatRelative(timestamp) {
  if (!timestamp) {
    return "never";
  }

  const parsedDate = parseServerDate(timestamp);
  if (!parsedDate || Number.isNaN(parsedDate.getTime())) {
    return "unknown";
  }

  const elapsedSeconds = Math.max(
    0,
    Math.floor((Date.now() - parsedDate.getTime()) / 1000)
  );
  if (elapsedSeconds < 60) {
    return `${elapsedSeconds}s ago`;
  }
  if (elapsedSeconds < 3600) {
    return `${Math.floor(elapsedSeconds / 60)}m ago`;
  }
  return `${Math.floor(elapsedSeconds / 3600)}h ago`;
}

export default function ControlPlanePage({
  currentTime,
  systemState,
  onOpenWorkstation,
}) {
  const [minutes, setMinutes] = useState(30);
  const [assemblyType, setAssemblyType] = useState(systemState.assembly_type);
  const [busyAction, setBusyAction] = useState("");

  useEffect(() => {
    setAssemblyType(systemState.assembly_type);
  }, [systemState.assembly_type]);

  const urgentOrders = useMemo(
    () => systemState.orders.filter((order) => order.urgent),
    [systemState.orders]
  );
  const normalOrders = useMemo(
    () => systemState.orders.filter((order) => !order.urgent),
    [systemState.orders]
  );

  async function runTimerCommand(command) {
    setBusyAction(`timer:${command}`);
    try {
      await apiFetch("/api/timer/", {
        method: "POST",
        body: JSON.stringify({
          command,
          seconds: Number(minutes) * 60,
        }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function saveAssemblyType() {
    setBusyAction("assembly");
    try {
      await apiFetch("/api/manager/assembly", {
        method: "POST",
        body: JSON.stringify({ assembly_type: assemblyType }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function toggleStation(station, enabled) {
    setBusyAction(`station:${station.station_id}`);
    try {
      await apiFetch(`/api/manager/${enabled ? "enable" : "disable"}`, {
        method: "POST",
        body: JSON.stringify({ original_ws_ids: [station.station_id] }),
      });
    } finally {
      setBusyAction("");
    }
  }

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Control Plane</p>
          <h1>Live station orchestration</h1>
          <p className="hero-copy">
            Central timer control, station health, and order visibility now come
            from the backend state projection instead of local tablet logic.
          </p>
        </div>
        <div className="hero-stats">
          <div className="stat-card">
            <span className="stat-label">Timer</span>
            <strong>{formatTimer(systemState.timer, currentTime)}</strong>
            <span className="stat-meta">{systemState.timer.state}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Stations</span>
            <strong>{systemState.summary.stations}</strong>
            <span className="stat-meta">
              {systemState.stations.filter((station) => station.health === "online").length} online
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Orders</span>
            <strong>{systemState.summary.active_orders}</strong>
            <span className="stat-meta">
              {systemState.summary.urgent_orders} urgent
            </span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Session Control</p>
            <h2>Timer and assembly mode</h2>
          </div>
        </div>
        <div className="control-grid">
          <label className="field">
            <span>Start timer (minutes)</span>
            <input
              type="number"
              min="1"
              value={minutes}
              onChange={(event) => setMinutes(event.target.value)}
            />
          </label>
          <div className="button-row">
            <button
              className="primary-button"
              disabled={busyAction === "timer:start"}
              onClick={() => runTimerCommand("start")}
            >
              Start
            </button>
            <button
              className="ghost-button"
              disabled={busyAction === "timer:pause"}
              onClick={() => runTimerCommand("pause")}
            >
              Pause
            </button>
            <button
              className="ghost-button"
              disabled={busyAction === "timer:resume"}
              onClick={() => runTimerCommand("resume")}
            >
              Resume
            </button>
            <button
              className="danger-button"
              disabled={busyAction === "timer:stop"}
              onClick={() => runTimerCommand("stop")}
            >
              Stop
            </button>
          </div>
          <label className="field">
            <span>Assembly type</span>
            <select
              value={assemblyType}
              onChange={(event) => setAssemblyType(event.target.value)}
            >
              <option value="standard">Standard</option>
              <option value="simplified">Simplified</option>
            </select>
          </label>
          <div className="button-row">
            <button
              className="primary-button"
              disabled={busyAction === "assembly"}
              onClick={saveAssemblyType}
            >
              Save assembly type
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Stations</p>
            <h2>Roster and operator-side state</h2>
          </div>
        </div>
        <div className="station-grid">
          {systemState.stations.map((station) => (
            <article key={station.station_id} className="station-card">
              <div className="station-card-header">
                <div>
                  <h3>{station.display_name}</h3>
                  <p className="station-meta">
                    {station.station_id} · {station.client_type}
                  </p>
                </div>
                <span className={`badge badge-${station.health}`}>
                  {station.health}
                </span>
              </div>
              <div className="operator-state-grid">
                {Object.values(station.sides).map((sideState) => (
                  <div key={sideState.side} className="operator-chip">
                    <strong>{sideState.side}</strong>
                    <span>{sideState.andon_code}</span>
                    <small>
                      {sideState.pending_orders} orders · {sideState.manual_state}
                    </small>
                  </div>
                ))}
              </div>
              <div className="station-actions">
                <button
                  className="ghost-button"
                  onClick={() => onOpenWorkstation(station.station_id)}
                >
                  Open workstation
                </button>
                <button
                  className={station.enabled ? "danger-button" : "primary-button"}
                  disabled={busyAction === `station:${station.station_id}`}
                  onClick={() => toggleStation(station, !station.enabled)}
                >
                  {station.enabled ? "Disable" : "Enable"}
                </button>
              </div>
              <p className="station-meta">
                Last seen {formatRelative(station.last_seen)}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel split-panel">
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Orders</p>
              <h2>Urgent queue</h2>
            </div>
          </div>
          <div className="order-list">
            {urgentOrders.map((order) => (
              <div key={order.order_id} className="order-card urgent">
                <strong>{order.order_id}</strong>
                <span>
                  {order.ws_id} · {order.side}
                </span>
                <small>{Object.entries(order.items_dict).map(([name, qty]) => `${name} ${qty}`).join(" · ")}</small>
              </div>
            ))}
            {urgentOrders.length === 0 ? <p className="muted-copy">No urgent orders.</p> : null}
          </div>
        </div>
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Orders</p>
              <h2>Standard queue</h2>
            </div>
          </div>
          <div className="order-list">
            {normalOrders.map((order) => (
              <div key={order.order_id} className="order-card">
                <strong>{order.order_id}</strong>
                <span>
                  {order.ws_id} · {order.side}
                </span>
                <small>{Object.entries(order.items_dict).map(([name, qty]) => `${name} ${qty}`).join(" · ")}</small>
              </div>
            ))}
            {normalOrders.length === 0 ? <p className="muted-copy">No standard orders.</p> : null}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Observability</p>
            <h2>Recent state changes</h2>
          </div>
        </div>
        <div className="event-list">
          {systemState.recent_events.map((event, index) => (
            <div key={`${event.created_at}-${index}`} className="event-row">
              <strong>{event.event_type}</strong>
              <span>
                {event.station_id || "system"} {event.side ? `· ${event.side}` : ""}
              </span>
              <small>{formatRelative(event.created_at)}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
