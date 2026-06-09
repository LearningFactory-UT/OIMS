import React, { useCallback, useEffect, useMemo, useState } from "react";

import "./App.css";
import AccessDeniedPage from "./pages/AccessDeniedPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import ControlPlanePage from "./pages/ControlPlanePage";
import DeviceBootstrapPage from "./pages/DeviceBootstrapPage";
import OrdersBoardPage from "./pages/OrdersBoardPage";
import ProvisionPage from "./pages/ProvisionPage";
import WorkstationPage from "./pages/WorkstationPage";
import { apiFetch } from "./lib/api";
import { disconnectSocket, getSocket } from "./lib/socket";
import { formatTimer } from "./timerUtils";

const EMPTY_STATE = {
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
  devices: [],
};

const EMPTY_AUTH = {
  loading: true,
  authenticated: false,
  role: null,
  auth_kind: null,
  device_id: null,
  device_label: null,
  station_id: null,
  is_admin: false,
};

function getRouteState() {
  return window.location.pathname;
}

function isAdminRoute(route) {
  return (
    route === "/admin" ||
    route === "/orders-board" ||
    route === "/provision" ||
    route.startsWith("/workstation/")
  );
}

function defaultRouteForAuth(authState) {
  if (!authState.authenticated) {
    return "/admin";
  }
  if (authState.role === "admin") {
    return "/admin";
  }
  if (authState.role === "inventory") {
    return "/inventory";
  }
  if (authState.role === "tablet") {
    return "/tablet";
  }
  return "/admin";
}

function stateEndpointForRoute(authState, route) {
  if (!authState.authenticated) {
    return null;
  }
  if (authState.role === "inventory") {
    return "/api/system/orders";
  }
  if (authState.role === "tablet") {
    return "/api/system/tablet-state";
  }
  if (route === "/orders-board") {
    return "/api/system/orders";
  }
  return "/api/system/state";
}

function statePollIntervalForRoute(authState, route) {
  if (!authState.authenticated) {
    return null;
  }
  if (["inventory", "tablet"].includes(authState.role) || route === "/orders-board") {
    return 2000;
  }
  if (authState.role === "admin") {
    return 10000;
  }
  return 5000;
}

export default function App() {
  const [systemState, setSystemState] = useState(EMPTY_STATE);
  const [authState, setAuthState] = useState(EMPTY_AUTH);
  const [route, setRoute] = useState(getRouteState);
  const [currentTime, setCurrentTime] = useState(new Date());

  const resolvedRoute = useMemo(() => {
    if (route === "/") {
      return defaultRouteForAuth(authState);
    }
    if (route === "/orders-board" && authState.role === "inventory") {
      return "/inventory";
    }
    return route;
  }, [authState, route]);

  const stateEndpoint = useMemo(
    () => stateEndpointForRoute(authState, resolvedRoute),
    [authState, resolvedRoute]
  );

  const statePollIntervalMs = useMemo(
    () => statePollIntervalForRoute(authState, resolvedRoute),
    [authState, resolvedRoute]
  );

  const refreshSystemState = useCallback(async () => {
    if (!stateEndpoint) {
      return;
    }
    try {
      const snapshot = await apiFetch(stateEndpoint);
      setSystemState((current) => ({ ...current, ...snapshot }));
    } catch (error) {
      console.error(error);
    }
  }, [stateEndpoint]);

  useEffect(() => {
    let active = true;

    async function loadSession() {
      try {
        const sessionState = await apiFetch("/api/auth/session");
        if (active) {
          setAuthState({ loading: false, ...EMPTY_AUTH, ...sessionState });
        }
      } catch (error) {
        if (active) {
          setAuthState({ ...EMPTY_AUTH, loading: false });
        }
      }
    }

    loadSession();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (authState.loading || !authState.authenticated) {
      disconnectSocket();
      if (!authState.loading) {
        setSystemState(EMPTY_STATE);
      }
      return undefined;
    }

    if (authState.role !== "admin") {
      disconnectSocket();
      refreshSystemState();
      return undefined;
    }

    const socket = getSocket();

    function handleStateSnapshot(snapshot) {
      setSystemState((current) => ({ ...current, ...snapshot }));
    }

    function handleTimerState(timer) {
      setSystemState((current) => ({ ...current, timer }));
    }

    refreshSystemState();
    socket.connect();
    socket.on("state_snapshot", handleStateSnapshot);
    socket.on("timer_state", handleTimerState);

    return () => {
      socket.off("state_snapshot", handleStateSnapshot);
      socket.off("timer_state", handleTimerState);
    };
  }, [
    authState.authenticated,
    authState.loading,
    authState.role,
    authState.station_id,
    refreshSystemState,
  ]);

  useEffect(() => {
    if (authState.loading || !authState.authenticated || !statePollIntervalMs) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      refreshSystemState();
    }, statePollIntervalMs);

    return () => window.clearInterval(intervalId);
  }, [
    authState.authenticated,
    authState.loading,
    refreshSystemState,
    statePollIntervalMs,
  ]);

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

  async function handleLogout() {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
      console.error(error);
    } finally {
      disconnectSocket();
      setAuthState({ ...EMPTY_AUTH, loading: false });
      setSystemState(EMPTY_STATE);
      navigate("/admin");
    }
  }

  function handleAuthenticated(sessionState) {
    setAuthState({ loading: false, ...EMPTY_AUTH, ...sessionState });
  }

  function handleTimerSnapshot(timer) {
    setSystemState((current) => ({ ...current, timer }));
  }

  const isWorkstationSurface =
    resolvedRoute === "/tablet" || resolvedRoute.startsWith("/workstation/");

  useEffect(() => {
    document.body.classList.toggle("workstation-mode", isWorkstationSurface);
    document.documentElement.classList.toggle("workstation-mode", isWorkstationSurface);

    return () => {
      document.body.classList.remove("workstation-mode");
      document.documentElement.classList.remove("workstation-mode");
    };
  }, [isWorkstationSurface]);

  const page = useMemo(() => {
    if (resolvedRoute === "/inventory") {
      if (!authState.authenticated) {
        return (
          <DeviceBootstrapPage
            expectedRole="inventory"
            title="Inventory Orders Board"
            description="This device is restricted to the live order queue."
            onAuthenticated={handleAuthenticated}
          />
        );
      }
      if (!["inventory", "admin"].includes(authState.role)) {
        return (
          <AccessDeniedPage
            title="Inventory access denied"
            description="This device is not allowed to open the inventory orders board."
          />
        );
      }
      return <OrdersBoardPage systemState={systemState} />;
    }

    if (resolvedRoute === "/tablet") {
      if (!authState.authenticated) {
        return (
          <DeviceBootstrapPage
            expectedRole="tablet"
            title="Tablet Workstation"
            description="This tablet opens directly into its assigned workstation."
            onAuthenticated={handleAuthenticated}
          />
        );
      }
      if (authState.role !== "tablet") {
        return (
          <AccessDeniedPage
            title="Tablet access denied"
            description="Only a tablet-bound device token can open this workstation surface."
          />
        );
      }
      return (
        <WorkstationPage
          currentTime={currentTime}
          onRefreshState={refreshSystemState}
          stationId={authState.station_id}
          systemState={systemState}
        />
      );
    }

    if (resolvedRoute === "/provision") {
      if (!authState.authenticated) {
        return <AdminLoginPage onAuthenticated={handleAuthenticated} />;
      }
      if (authState.role !== "admin") {
        return (
          <AccessDeniedPage
            title="Admin access required"
            description="Provisioning is available only from the admin surface."
          />
        );
      }
      return (
        <ProvisionPage
          systemState={systemState}
          onRefreshState={refreshSystemState}
          onOpenWorkstation={(stationId) => navigate(`/workstation/${stationId}`)}
        />
      );
    }

    if (resolvedRoute.startsWith("/workstation/")) {
      if (!authState.authenticated) {
        return <AdminLoginPage onAuthenticated={handleAuthenticated} />;
      }
      if (authState.role !== "admin") {
        return (
          <AccessDeniedPage
            title="Admin access required"
            description="Only the admin surface can preview arbitrary workstation routes."
          />
        );
      }
      const stationId = decodeURIComponent(resolvedRoute.replace("/workstation/", ""));
      return (
        <WorkstationPage
          currentTime={currentTime}
          onRefreshState={refreshSystemState}
          stationId={stationId}
          systemState={systemState}
        />
      );
    }

    if (resolvedRoute === "/orders-board") {
      if (!authState.authenticated) {
        return <AdminLoginPage onAuthenticated={handleAuthenticated} />;
      }
      if (authState.role !== "admin") {
        return (
          <AccessDeniedPage
            title="Admin access required"
            description="Use the dedicated inventory surface on inventory devices."
          />
        );
      }
      return <OrdersBoardPage systemState={systemState} />;
    }

    if (!authState.authenticated) {
      return <AdminLoginPage onAuthenticated={handleAuthenticated} />;
    }

    if (authState.role !== "admin") {
      return (
        <AccessDeniedPage
          title="Admin access required"
          description="This URL belongs to the admin surface."
        />
      );
    }

    return (
      <ControlPlanePage
        currentTime={currentTime}
        onRefreshState={refreshSystemState}
        systemState={systemState}
        onTimerSnapshot={handleTimerSnapshot}
        onOpenWorkstation={(stationId) => navigate(`/workstation/${stationId}`)}
      />
    );
  }, [authState, currentTime, resolvedRoute, systemState]);

  const showAdminChrome =
    authState.authenticated && authState.role === "admin" && isAdminRoute(resolvedRoute);

  return (
    <div className={isWorkstationSurface ? "app-shell workstation-app-shell" : "app-shell"}>
      {showAdminChrome ? (
        <header className="app-header">
          <div className="brand-block">
            <img src="/logo.png" alt="OIMS" />
            <div>
              <span className="eyebrow">Ordering and Inventory Management</span>
              <h1>OIMS Admin</h1>
            </div>
          </div>
          <nav className="nav-links">
            <button
              className={resolvedRoute === "/admin" ? "nav-link active" : "nav-link"}
              onClick={() => navigate("/admin")}
            >
              Control Plane
            </button>
            <button
              className={resolvedRoute === "/orders-board" ? "nav-link active" : "nav-link"}
              onClick={() => navigate("/orders-board")}
            >
              Orders Board
            </button>
            <button
              className={resolvedRoute === "/provision" ? "nav-link active" : "nav-link"}
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
            <div>
              <span className="eyebrow">Session</span>
              <button className="ghost-button compact-button" onClick={handleLogout}>
                Sign out
              </button>
            </div>
          </div>
        </header>
      ) : null}
      <main className={isWorkstationSurface ? "app-body workstation-app-body" : "app-body"}>
        {page}
      </main>
    </div>
  );
}
