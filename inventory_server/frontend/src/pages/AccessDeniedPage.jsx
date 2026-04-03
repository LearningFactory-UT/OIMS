import React from "react";

export default function AccessDeniedPage({ title, description }) {
  return (
    <div className="page-grid auth-page">
      <section className="panel auth-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Access Control</p>
            <h2>{title}</h2>
          </div>
        </div>
        <p className="auth-error">{description}</p>
      </section>
    </div>
  );
}
