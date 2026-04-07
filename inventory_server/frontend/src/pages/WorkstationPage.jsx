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

function actionButtonClasses(kind, active) {
  return `action-button action-${kind}${active ? " is-active" : ""}`;
}

export default function WorkstationPage({ currentTime, onRefreshState, stationId, systemState }) {
  const catalog = ITEM_CATALOG[systemState.assembly_type] || ITEM_CATALOG.standard;
  const firstRowCount = Math.ceil(catalog.length / 2);
  const topRowItems = catalog.slice(0, firstRowCount);
  const bottomRowItems = catalog.slice(firstRowCount);
  const [draft, setDraft] = useState(() => buildDraft(catalog));
  const [busyAction, setBusyAction] = useState("");
  const [decisionDialog, setDecisionDialog] = useState(null);
  const [stationFallback, setStationFallback] = useState(null);
  const [localTimer, setLocalTimer] = useState(systemState.timer);

  const stationFromSnapshot = useMemo(
    () =>
      systemState.stations.find(
        (candidate) =>
          candidate.station_id === stationId || candidate.display_name === stationId
      ),
    [stationId, systemState.stations]
  );
  const station = stationFromSnapshot || stationFallback;
  const timerState = localTimer || systemState.timer;
  const isTimerRunning = timerState?.state === "running";
  const interactionEnabled = Boolean(station?.enabled && isTimerRunning);
  const inactivityTitle = !station?.enabled
    ? "Workstation disabled"
    : timerState?.state === "paused"
      ? "Timer paused"
      : "Session inactive";
  const inactivityMessage = !station?.enabled
    ? "This workstation has been disabled from the admin control plane."
    : timerState?.state === "paused"
      ? "The central timer is paused. Workstation actions are temporarily locked."
      : "Start the central timer from the admin surface to unlock workstation actions.";

  useEffect(() => {
    onRefreshState?.();
  }, [onRefreshState]);

  useEffect(() => {
    if (!stationId) {
      return undefined;
    }

    let cancelled = false;

    async function refreshStationProjection() {
      try {
        const projection = await apiFetch(`/api/stations/${stationId}`);
        if (!cancelled) {
          setStationFallback(projection);
        }
      } catch (error) {
        if (!cancelled) {
          console.error(error);
        }
      }
    }

    async function heartbeat() {
      try {
        const projection = await apiFetch(`/api/stations/${stationId}/heartbeat`, {
          method: "POST",
          body: JSON.stringify({ client_type: "web-tablet" }),
        });
        if (!cancelled) {
          setStationFallback(projection);
        }
      } catch (error) {
        console.error(error);
      }
    }

    refreshStationProjection();
    heartbeat();
    const intervalId = window.setInterval(heartbeat, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [stationId]);

  useEffect(() => {
    if (stationFromSnapshot) {
      setStationFallback(stationFromSnapshot);
    }
  }, [stationFromSnapshot]);

  useEffect(() => {
    setLocalTimer(systemState.timer);
  }, [systemState.timer]);

  useEffect(() => {
    let cancelled = false;

    async function refreshLocalTimer() {
      try {
        const timer = await apiFetch("/api/timer/");
        if (!cancelled) {
          setLocalTimer(timer);
        }
      } catch (error) {
        if (!cancelled) {
          console.error(error);
        }
      }
    }

    refreshLocalTimer();
    const intervalId = window.setInterval(refreshLocalTimer, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

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
    if (!interactionEnabled) {
      return;
    }
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
      const projection = await apiFetch(`/api/stations/${stationId}`);
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function toggleHelp(side, active) {
    if (!interactionEnabled) {
      return;
    }
    const immediate = active
      ? await askUrgency({
          title: "Help request priority",
          message: "Does this help request need immediate attention?",
        })
      : false;

    setBusyAction(`help:${side}`);
    try {
      const projection = await apiFetch(`/api/stations/${stationId}/help`, {
        method: "POST",
        body: JSON.stringify({
          side,
          active,
          idle: immediate,
        }),
      });
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function toggleWaitingPrevious(side, active) {
    if (!interactionEnabled) {
      return;
    }
    const immediate = active
      ? await askUrgency({
          title: "Waiting from previous",
          message: "Is this request from the previous workstation urgent?",
        })
      : false;

    setBusyAction(`waiting:${side}`);
    try {
      const projection = await apiFetch(`/api/stations/${stationId}/waiting-previous`, {
        method: "POST",
        body: JSON.stringify({
          side,
          active,
          idle: immediate,
        }),
      });
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function toggleReadyNext(side, active) {
    if (!interactionEnabled) {
      return;
    }
    setBusyAction(`ready:${side}`);
    try {
      const projection = await apiFetch(`/api/stations/${stationId}/ready-next`, {
        method: "POST",
        body: JSON.stringify({
          side,
          active,
        }),
      });
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function setManualState(side, command) {
    if (!interactionEnabled) {
      return;
    }
    setBusyAction(`manual:${side}`);
    try {
      const projection = await apiFetch(`/api/stations/${stationId}/manual`, {
        method: "POST",
        body: JSON.stringify({
          side,
          command,
        }),
      });
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function updateOrder(orderId, urgent) {
    if (!interactionEnabled) {
      return;
    }
    setBusyAction(`update:${orderId}`);
    try {
      await apiFetch(`/api/orders/${orderId}`, {
        method: "PATCH",
        body: JSON.stringify({ urgent }),
      });
      const projection = await apiFetch(`/api/stations/${stationId}`);
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function deliverOrder(orderId) {
    if (!interactionEnabled) {
      return;
    }
    setBusyAction(`deliver:${orderId}`);
    try {
      await apiFetch(`/api/orders/${orderId}/deliver`, {
        method: "POST",
      });
      const projection = await apiFetch(`/api/stations/${stationId}`);
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  async function deleteOrder(orderId) {
    if (!interactionEnabled) {
      return;
    }
    setBusyAction(`delete:${orderId}`);
    try {
      await apiFetch(`/api/orders/${orderId}`, {
        method: "DELETE",
      });
      const projection = await apiFetch(`/api/stations/${stationId}`);
      setStationFallback(projection);
      await onRefreshState?.();
    } finally {
      setBusyAction("");
    }
  }

  function adjustQuantity(item, delta) {
    if (!interactionEnabled) {
      return;
    }
    setDraft((currentDraft) => ({
      ...currentDraft,
      [item.name]: Math.max(0, Number(currentDraft[item.name]) + delta * item.step),
    }));
  }

  function renderItemCard(item) {
    return (
      <article key={item.name} className="item-card image-item-card">
        <img className="item-illustration" src={item.image} alt={item.name} />
        <span>{item.name}</span>
        <div className="stepper">
          <button
            disabled={!interactionEnabled}
            onClick={() => adjustQuantity(item, -1)}
          >
            −
          </button>
          <strong>{draft[item.name] || 0}</strong>
          <button
            disabled={!interactionEnabled}
            onClick={() => adjustQuantity(item, 1)}
          >
            +
          </button>
        </div>
      </article>
    );
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
    <div className={`page-grid workstation-shell${interactionEnabled ? "" : " is-inactive"}`}>
      <header className="workstation-toolbar">
        <div className="workstation-brand-mark">
          <img src="/logo.png" alt="FAB²" className="workstation-logo" />
        </div>
        <div className="workstation-identity-block">
          <p className="eyebrow">Web Workstation</p>
          <strong className="workstation-name">
            {station?.display_name || station?.station_id || stationId}
          </strong>
          <span className="workstation-id">Station ID {station?.station_id || stationId}</span>
        </div>
        <div className="workstation-topbar-stats">
          <div className="workstation-topbar-metric">
            <span className="workstation-metric-label">Time left</span>
            <strong className="workstation-metric-value">
              {formatTimer(timerState, currentTime)}
            </strong>
            <span className="workstation-metric-meta">{timerState?.state || "stopped"}</span>
          </div>
          <div className="workstation-topbar-metric">
            <span className="workstation-metric-label">Status</span>
            <strong className="workstation-metric-value status-value">{station.health}</strong>
            <span className="workstation-metric-meta">
              {station.enabled ? "enabled" : "disabled"}
            </span>
          </div>
        </div>
      </header>
      <div className="workstation-content">
        {!interactionEnabled ? (
          <section className="panel inactive-banner-panel">
            <div className="inactive-banner">
              <p className="eyebrow">{inactivityTitle}</p>
              <p className="muted-copy">{inactivityMessage}</p>
            </div>
          </section>
        ) : null}

        <section
          className={`panel workstation-parts-panel interaction-surface${
            interactionEnabled ? "" : " is-locked"
          }`}
        >
          <div className="shared-item-rows" style={{ "--row-columns": firstRowCount }}>
            <div className="shared-item-row">{topRowItems.map(renderItemCard)}</div>
            {bottomRowItems.length > 0 ? (
              <div className="shared-item-row shared-item-row-bottom">
                {bottomRowItems.map(renderItemCard)}
              </div>
            ) : null}
          </div>
        </section>

        <section
          className={`operator-layout interaction-surface${interactionEnabled ? "" : " is-locked"}`}
        >
          {Object.values(station.sides).map((sideState) => {
            const sideOrders = station.active_orders.filter(
              (order) => order.side === sideState.side
            );

            return (
              <article key={sideState.side} className="panel operator-panel">
                <div className="panel-header operator-panel-header">
                  <p className="eyebrow">Operator {sideState.side}</p>
                  <span className="badge badge-inline andon-badge">{sideState.andon_code}</span>
                </div>

                <div className="operator-groups">
                  <div className="operator-action-row">
                    <div className="operator-actions-grid">
                      <button
                        className="primary-button send-order-button"
                        disabled={
                          !interactionEnabled || busyAction === `order:${sideState.side}`
                        }
                        onClick={() => createOrder(sideState.side)}
                      >
                        Send order
                      </button>
                      <button
                        className={actionButtonClasses(
                          "waiting",
                          Boolean(sideState.waiting_from_previous)
                        )}
                        disabled={!interactionEnabled || busyAction === `waiting:${sideState.side}`}
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
                        className={actionButtonClasses(
                          "ready",
                          Boolean(sideState.ready_for_next)
                        )}
                        disabled={!interactionEnabled || busyAction === `ready:${sideState.side}`}
                        onClick={() =>
                          toggleReadyNext(sideState.side, !sideState.ready_for_next)
                        }
                      >
                        {sideState.ready_for_next
                          ? "Preassembly delivered"
                          : "Ready for next"}
                      </button>
                    </div>
                  </div>

                  <div className="operator-action-row">
                    <div className="operator-actions-grid">
                      <button
                        className={actionButtonClasses("help", Boolean(sideState.help_request))}
                        disabled={!interactionEnabled || busyAction === `help:${sideState.side}`}
                        onClick={() => toggleHelp(sideState.side, !sideState.help_request)}
                      >
                        {sideState.help_request ? "Clear help" : "Request help"}
                      </button>
                      <button
                        className={actionButtonClasses(
                          "start",
                          sideState.manual_state === "start"
                        )}
                        disabled={!interactionEnabled || busyAction === `manual:${sideState.side}`}
                        onClick={() => setManualState(sideState.side, "start")}
                      >
                        Start
                      </button>
                      <button
                        className={actionButtonClasses(
                          "stop",
                          sideState.manual_state === "stop"
                        )}
                        disabled={!interactionEnabled || busyAction === `manual:${sideState.side}`}
                        onClick={() => setManualState(sideState.side, "stop")}
                      >
                        Stop
                      </button>
                    </div>
                  </div>
                </div>

                <section className="order-list-shell">
                  <p className="eyebrow">
                    Active orders: {sideOrders.length} · oldest first
                  </p>
                  <div className="order-list compact operator-order-list">
                    {sideOrders.map((order) => (
                      <div key={order.order_id} className="order-card">
                        <p className="operator-order-items">{formatOrderItems(order.items_dict)}</p>
                        <div className="button-row wrap">
                          <button
                            className="ghost-button"
                            disabled={
                              !interactionEnabled || busyAction === `update:${order.order_id}`
                            }
                            onClick={() => updateOrder(order.order_id, !order.urgent)}
                          >
                            Make {order.urgent ? "standard" : "urgent"}
                          </button>
                          <button
                            className="primary-button"
                            disabled={
                              !interactionEnabled || busyAction === `deliver:${order.order_id}`
                            }
                            onClick={() => deliverOrder(order.order_id)}
                          >
                            Delivered
                          </button>
                          <button
                            className="danger-button"
                            disabled={
                              !interactionEnabled || busyAction === `delete:${order.order_id}`
                            }
                            onClick={() => deleteOrder(order.order_id)}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                    {sideOrders.length === 0 ? (
                      <p className="muted-copy">No active orders for this operator.</p>
                    ) : null}
                  </div>
                </section>
              </article>
            );
          })}
        </section>
      </div>

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
