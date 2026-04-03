import React, { useEffect, useMemo, useState } from "react";

import { apiFetch } from "../lib/api";

function getTokenFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return params.get("token") || "";
}

export default function DeviceBootstrapPage({
  expectedRole,
  title,
  description,
  onAuthenticated,
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const token = useMemo(() => getTokenFromLocation(), []);

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    async function bootstrap() {
      setBusy(true);
      setError("");
      try {
        const session = await apiFetch("/api/auth/device-login", {
          method: "POST",
          body: JSON.stringify({ token }),
        });
        if (cancelled) {
          return;
        }
        if (session.role !== expectedRole) {
          setError(`This token is not allowed to open the ${expectedRole} surface.`);
          return;
        }
        window.history.replaceState({}, "", window.location.pathname);
        onAuthenticated(session);
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.message || "Unable to bootstrap this device.");
        }
      } finally {
        if (!cancelled) {
          setBusy(false);
        }
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [expectedRole, onAuthenticated, token]);

  return (
    <div className="page-grid auth-page">
      <section className="panel auth-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Device Access</p>
            <h2>{title}</h2>
          </div>
        </div>
        <p className="muted-copy">{description}</p>
        {busy ? <p className="muted-copy">Authenticating device token...</p> : null}
        {!busy && !token ? (
          <p className="auth-error">
            No bootstrap token was found in the URL. Launch this surface from the
            configured tablet or inventory device.
          </p>
        ) : null}
        {error ? <p className="auth-error">{error}</p> : null}
      </section>
    </div>
  );
}
