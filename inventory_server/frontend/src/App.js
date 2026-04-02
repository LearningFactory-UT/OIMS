import React, { useEffect, useMemo, useState } from "react";

import "./App.css";
import ControlPlanePage from "./pages/ControlPlanePage";
import OrdersBoardPage from "./pages/OrdersBoardPage";
import ProvisionPage from "./pages/ProvisionPage";
import WorkstationPage from "./pages/WorkstationPage";
import { apiFetch } from "./lib/api";
import { getSocket } from "./lib/socket";
import { formatTimer } from "./timerUtils";

function getRouteState() {
  return window.location.pathname;
}

export default function App() {
  const [systemState, setSystemState] = useState({
    assembly_type: "standard",
    timer: {
      state: "stopped",
      total_seconds: 0,
      remaining_seconds: 0,
      paused_seconds: 0,
      start_time: null,
    },
    stations: [],
    orders: [],
    summary: {
      active_orders: 0,
      urgent_orders: 0,
      stations: 0,
    },
    recent_events: [],
  });
  const [route, setRoute] = useState(getRouteState);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    let active = true;
    const socket = getSocket();

    async function loadState() {
      try {
        const snapshot = await apiFetch("/api/system/state");
        if (active) {
          setSystemState(snapshot);
        }
      } catch (error) {
        console.error(error);
      }
    }

    function handleStateSnapshot(snapshot) {
      setSystemState(snapshot);
    }

    loadState();
    socket.on("state_snapshot", handleStateSnapshot);

    return () => {
      active = false;
      socket.off("state_snapshot", handleStateSnapshot);
    };
  }, []);

  useEffect(() => {
    function handlePopState() {
      setRoute(getRouteState());
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  function navigate(pathname) {
    if (pathname === route) {
      return;
    }
    window.history.pushState({}, "", pathname);
    setRoute(pathname);
  }

  const page = useMemo(() => {
    if (route.startsWith("/workstation/")) {
      const stationId = decodeURIComponent(route.replace("/workstation/", ""));
      return (
        <WorkstationPage
          currentTime={currentTime}
          stationId={stationId}
          systemState={systemState}
        />
      );
    }
    if (route === "/orders-board") {
      return <OrdersBoardPage systemState={systemState} />;
    }
    if (route === "/provision") {
      return (
        <ProvisionPage
          systemState={systemState}
          onOpenWorkstation={(stationId) => navigate(`/workstation/${stationId}`)}
        />
      );
    }
      return (
      <ControlPlanePage
        currentTime={currentTime}
        systemState={systemState}
        onOpenWorkstation={(stationId) => navigate(`/workstation/${stationId}`)}
      />
    );
  }, [currentTime, route, systemState]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <img src="/logo.png" alt="OIMS" />
          <div>
            <span className="eyebrow">Ordering and Inventory Management</span>
            <h1>OIMS</h1>
          </div>
        </div>
        <nav className="nav-links">
          <button
            className={route === "/" ? "nav-link active" : "nav-link"}
            onClick={() => navigate("/")}
          >
            Control Plane
          </button>
          <button
            className={route === "/orders-board" ? "nav-link active" : "nav-link"}
            onClick={() => navigate("/orders-board")}
          >
            Orders Board
          </button>
          <button
            className={route === "/provision" ? "nav-link active" : "nav-link"}
            onClick={() => navigate("/provision")}
          >
            Provision
          </button>
        </nav>
        <div className="header-status">
          <div>
            <span className="eyebrow">Clock</span>
            <strong>{currentTime.toLocaleTimeString()}</strong>
          </div>
          <div>
            <span className="eyebrow">Timer</span>
            <strong>{formatTimer(systemState.timer, currentTime)}</strong>
          </div>
        </div>
      </header>
      <main className="app-body">{page}</main>
    </div>
  );
}
