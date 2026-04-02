import React from "react";

import "./Modal.css";

export default function DecisionModal({
  title,
  message,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
}) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content decision-modal" onClick={(event) => event.stopPropagation()}>
        <p className="eyebrow">Confirmation</p>
        <h3>{title}</h3>
        <p className="decision-copy">{message}</p>
        <div className="decision-actions">
          <button className="ghost-button modal-action" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button className="primary-button modal-action" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
