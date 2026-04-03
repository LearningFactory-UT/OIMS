import React, { useState } from "react";

import { apiFetch } from "../lib/api";

export default function AdminLoginPage({ onAuthenticated }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const session = await apiFetch("/api/auth/admin/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onAuthenticated(session);
    } catch (requestError) {
      setError(requestError.message || "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-grid auth-page">
      <section className="panel auth-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Admin Access</p>
            <h2>Sign in to OIMS 2.0</h2>
          </div>
        </div>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label className="field">
            <span>Username</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <p className="auth-error">{error}</p> : null}
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}
