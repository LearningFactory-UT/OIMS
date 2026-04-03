import React, { useEffect, useMemo, useState } from "react";

import DecisionModal from "../components/DecisionModal";
import { ITEM_CATALOG } from "../constants";
import { apiFetch } from "../lib/api";
import { formatTimer } from "../timerUtils";

function buildDraft(items) {
  return items.reduce((draft, item) => ({ ...draft, [item.name]: 0 }), {});
}

function compactItems(items) {
  return Object.fromEntries(
    Object.entries(items).filter(([, quantity]) => Number(quantity) > 0)
  );
}

function formatOrderItems(items) {
  return Object.entries(items)
    .map(([name, qty]) => `${name} ${qty}`)
    .join(" · ");
}

export default function WorkstationPage({ currentTime, stationId, systemState }) {
  const catalog = ITEM_CATALOG[systemState.assembly_type] || ITEM_CATALOG.standard;
  const [draft, setDraft] = useState(() => buildDraft(catalog));
  const [busyAction, setBusyAction] = useState("");
  const [decisionDialog, setDecisionDialog] = useState(null);

  const station = useMemo(
    () =>
      systemState.stations.find(
        (candidate) =>
          candidate.station_id === stationId || candidate.display_name === stationId
      ),
    [stationId, systemState.stations]
  );
  const stationHeading =
    station && station.display_name !== station.station_id
      ? `${station.display_name} · ${station.station_id}`
      : station?.station_id || station?.display_name || "";

  useEffect(() => {
    if (!stationId) {
      return undefined;
    }

    let cancelled = false;

    async function heartbeat() {
      try {
        await apiFetch(`/api/stations/${stationId}/heartbeat`, {
          method: "POST",
          body: JSON.stringify({ client_type: "web-tablet" }),
        });
      } catch (error) {
        console.error(error);
      }
    }

    heartbeat();
    const intervalId = window.setInterval(heartbeat, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [stationId]);

  useEffect(() => {
    setDraft(buildDraft(catalog));
  }, [systemState.assembly_type]);

  function askUrgency({ title, message }) {
    return new Promise((resolve) => {
      setDecisionDialog({
        title,
        message,
        resolve,
      });
    });
  }

  function closeDecision(result) {
    if (decisionDialog?.resolve) {
      decisionDialog.resolve(result);
    }
    setDecisionDialog(null);
  }

  async function createOrder(side) {
    const items = compactItems(draft);
    if (Object.keys(items).length === 0) {
      return;
    }

    const urgent = await askUrgency({
      title: "Order priority",
      message: "Should this new order be treated as urgent?",
    });

    setBusyAction(`order:${side}`);
    try {
      await apiFetch(`/api/stations/${stationId}/orders`, {
        method: "POST",
        body: JSON.stringify({
          side,
          urgent,
          items,
        }),
      });
      setDraft(buildDraft(catalog));
    } finally {
      setBusyAction("");
    }
  }

  async function toggleHelp(side, active) {
    const immediate = active
      ? await askUrgency({
          title: "Help request priority",
          message: "Does this help request need immediate attention?",
        })
      : false;

    setBusyAction(`help:${side}`);
    try {
      await apiFetch(`/api/stations/${stationId}/help`, {
        method: "POST",
        body: JSON.stringify({
          side,
          active,
          idle: immediate,
        }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function toggleWaitingPrevious(side, active) {
    const immediate = active
      ? await askUrgency({
          title: "Waiting from previous",
          message: "Is this request from the previous workstation urgent?",
        })
      : false;

    setBusyAction(`waiting:${side}`);
    try {
      await apiFetch(`/api/stations/${stationId}/waiting-previous`, {
        method: "POST",
        body: JSON.stringify({
          side,
          active,
          idle: immediate,
        }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function toggleReadyNext(side, active) {
    setBusyAction(`ready:${side}`);
    try {
      await apiFetch(`/api/stations/${stationId}/ready-next`, {
        method: "POST",
        body: JSON.stringify({
          side,
          active,
        }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function setManualState(side, command) {
    setBusyAction(`manual:${side}`);
    try {
      await apiFetch(`/api/stations/${stationId}/manual`, {
        method: "POST",
        body: JSON.stringify({
          side,
          command,
        }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function updateOrder(orderId, urgent) {
    setBusyAction(`update:${orderId}`);
    try {
      await apiFetch(`/api/orders/${orderId}`, {
        method: "PATCH",
        body: JSON.stringify({ urgent }),
      });
    } finally {
      setBusyAction("");
    }
  }

  async function deliverOrder(orderId) {
    setBusyAction(`deliver:${orderId}`);
    try {
      await apiFetch(`/api/orders/${orderId}/deliver`, {
        method: "POST",
      });
    } finally {
      setBusyAction("");
    }
  }

  async function deleteOrder(orderId) {
    setBusyAction(`delete:${orderId}`);
    try {
      await apiFetch(`/api/orders/${orderId}`, {
        method: "DELETE",
      });
    } finally {
      setBusyAction("");
    }
  }

  function adjustQuantity(item, delta) {
    setDraft((currentDraft) => ({
      ...currentDraft,
      [item.name]: Math.max(0, Number(currentDraft[item.name]) + delta * item.step),
    }));
  }

  if (!station) {
    return (
      <div className="page-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
          <p className="eyebrow">Workstation</p>
          <h2>Waiting for station projection</h2>
            </div>
          </div>
          <p className="muted-copy">
            The workstation is being registered with the central server.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="page-grid">
      <section className="hero-panel workstation-hero">
        <div>
          <p className="eyebrow">Web Workstation</p>
          <h1>{stationHeading}</h1>
          <p className="hero-copy">
            One shared item grid with operator-specific actions and live central state.
          </p>
        </div>
        <div className="hero-stats">
          <div className="stat-card">
            <span className="stat-label">Timer</span>
            <strong>{formatTimer(systemState.timer, currentTime)}</strong>
            <span className="stat-meta">{systemState.timer.state}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Status</span>
            <strong>{station.health}</strong>
            <span className="stat-meta">
              {station.enabled ? "enabled" : "disabled"}
            </span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Order Builder</p>
            <h2>Shared parts grid</h2>
          </div>
        </div>
        <div className="shared-item-grid">
          {catalog.map((item) => (
            <article key={item.name} className="item-card image-item-card">
              <img className="item-illustration" src={item.image} alt={item.name} />
              <span>{item.name}</span>
              <div className="stepper">
                <button onClick={() => adjustQuantity(item, -1)}>−</button>
                <strong>{draft[item.name] || 0}</strong>
                <button onClick={() => adjustQuantity(item, 1)}>+</button>
              </div>
            </article>
          ))}
        </div>
        <div className="button-row wrap send-row">
          <button
            className="primary-button"
            disabled={!station.enabled || busyAction === "order:L"}
            onClick={() => createOrder("L")}
          >
            Send order left
          </button>
          <button
            className="primary-button"
            disabled={!station.enabled || busyAction === "order:R"}
            onClick={() => createOrder("R")}
          >
            Send order right
          </button>
        </div>
      </section>

      <section className="operator-layout">
        {Object.values(station.sides).map((sideState) => (
          <article key={sideState.side} className="panel operator-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Operator {sideState.side}</p>
                <h2>Actions and orders</h2>
              </div>
              <span className="badge badge-inline andon-badge">{sideState.andon_code}</span>
            </div>

            <div className="button-row wrap">
              <button
                className={sideState.help_request ? "danger-button" : "ghost-button"}
                disabled={!station.enabled || busyAction === `help:${sideState.side}`}
                onClick={() => toggleHelp(sideState.side, !sideState.help_request)}
              >
                {sideState.help_request ? "Clear help" : "Request help"}
              </button>
              <button
                className={
                  sideState.waiting_from_previous ? "danger-button" : "ghost-button"
                }
                disabled={!station.enabled || busyAction === `waiting:${sideState.side}`}
                onClick={() =>
                  toggleWaitingPrevious(
                    sideState.side,
                    !sideState.waiting_from_previous
                  )
                }
              >
                {sideState.waiting_from_previous
                  ? "Done waiting"
                  : "Waiting from previous"}
              </button>
              <button
                className={sideState.ready_for_next ? "primary-button" : "ghost-button"}
                disabled={!station.enabled || busyAction === `ready:${sideState.side}`}
                onClick={() =>
                  toggleReadyNext(sideState.side, !sideState.ready_for_next)
                }
              >
                {sideState.ready_for_next ? "Preassembly delivered" : "Ready for next"}
              </button>
            </div>

            <div className="button-row wrap">
              <button
                className="primary-button"
                disabled={!station.enabled || busyAction === `manual:${sideState.side}`}
                onClick={() => setManualState(sideState.side, "start")}
              >
                Start
              </button>
              <button
                className="danger-button"
                disabled={!station.enabled || busyAction === `manual:${sideState.side}`}
                onClick={() => setManualState(sideState.side, "stop")}
              >
                Stop
              </button>
              <button
                className="ghost-button"
                disabled={!station.enabled || busyAction === `manual:${sideState.side}`}
                onClick={() => setManualState(sideState.side, "reset")}
              >
                Reset
              </button>
            </div>

            <div className="order-list compact">
              {station.active_orders
                .filter((order) => order.side === sideState.side)
                .map((order) => (
                  <div key={order.order_id} className="order-card">
                    <strong>{order.order_id}</strong>
                    <small>{formatOrderItems(order.items_dict)}</small>
                    <div className="button-row wrap">
                      <button
                        className="ghost-button"
                        disabled={busyAction === `update:${order.order_id}`}
                        onClick={() => updateOrder(order.order_id, !order.urgent)}
                      >
                        Mark {order.urgent ? "standard" : "urgent"}
                      </button>
                      <button
                        className="primary-button"
                        disabled={busyAction === `deliver:${order.order_id}`}
                        onClick={() => deliverOrder(order.order_id)}
                      >
                        Delivered
                      </button>
                      <button
                        className="danger-button"
                        disabled={busyAction === `delete:${order.order_id}`}
                        onClick={() => deleteOrder(order.order_id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              {station.active_orders.filter((order) => order.side === sideState.side).length === 0 ? (
                <p className="muted-copy">No active orders for this operator.</p>
              ) : null}
            </div>
          </article>
        ))}
      </section>

      {decisionDialog ? (
        <DecisionModal
          title={decisionDialog.title}
          message={decisionDialog.message}
          confirmLabel="Urgent"
          cancelLabel="Not urgent"
          onConfirm={() => closeDecision(true)}
          onCancel={() => closeDecision(false)}
        />
      ) : null}
    </div>
  );
}
