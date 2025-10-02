// src/components/OrdersList.jsx
import React, { useEffect, useState } from "react";

function OrdersList({ title, orders, className }) {
    const [elapsedTimes, setElapsedTimes] = useState({});

    useEffect(() => {
        // We update the elapsed time every second
        const interval = setInterval(() => {
            const updated = {};
            orders.forEach((order) => {
                const createdAt = new Date(order.creation_time).getTime();
                const now = Date.now();
                const diffSec = Math.floor((now - createdAt) / 1000);

                updated[order.order_id] = formatTime(diffSec);
            });
            setElapsedTimes(updated);
        }, 1000);

        return () => clearInterval(interval);
    }, [orders]);

    const formatTime = (diffSec) => {
        const hrs = Math.floor(diffSec / 3600);
        const mins = Math.floor((diffSec % 3600) / 60);
        const secs = diffSec % 60;

        if (hrs > 0) {
            return `${hrs}h ${mins}m ${secs}s`;
        } else if (mins > 0) {
            return `${mins}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    };

    return (
        <div className={`section ${className}`}>
            <div className="section-title">{title}</div>
            {orders.length === 0 ? (
                <div> </div>
            ) : (
                orders.map((order) => (
                    <div key={order.order_id} style={{ marginBottom: "10px" }}>
                        {/* Example: "WS5_005 — 5 R" plus elapsed time */}
                        <div>
                            <strong>{order.order_id}</strong> — {order.ws_id}{" "}
                            {order.side} | Elapsed:{" "}
                            {elapsedTimes[order.order_id] || "0s"}
                        </div>
                        {/* Show items */}
                        <div style={{ marginLeft: "15px" }}>
                            {Object.entries(order.items_dict).map(([itemName, qty]) => (
                                <div key={itemName}>
                                    {itemName}: {qty}
                                </div>
                            ))}
                        </div>
                    </div>
                ))
            )}
        </div>
    );
}

export default OrdersList;