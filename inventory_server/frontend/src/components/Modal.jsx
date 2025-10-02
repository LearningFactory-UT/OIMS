// src/components/Modal.jsx
import React from "react";
import "./Modal.css";

function Modal({ children, onClose }) {
    // Clicking the backdrop closes the modal (onClose).
    // But clicking inside the white box shouldn't close it, so we do stopPropagation().
    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                {children}
            </div>
        </div>
    );
}

export default Modal;