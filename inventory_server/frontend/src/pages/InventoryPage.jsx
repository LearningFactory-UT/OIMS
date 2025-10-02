// src/pages/InventoryPage.jsx
import React, { useState, useEffect } from "react";
import io from "socket.io-client";
import OrdersList from "../components/OrdersList";
import TopBar from "../components/TopBar";
import Modal from "../components/Modal";  // import our reusable modal

function InventoryPage() {
    const [orders, setOrders] = useState([]);
    const [socket, setSocket] = useState(null);

    // Modal-related state
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [assemblyType, setAssemblyType] = useState("standard");

    useEffect(() => {
        const newSocket = io("http://rtlsserver.local:3010");
        setSocket(newSocket);

        newSocket.on("orders_updated", (data) => {
            setOrders(data.orders || []);
        });

        newSocket.on("order_removed", (data) => {
            setOrders((prev) => prev.filter((o) => o.order_id !== data.order_id));
        });

        // Listen for order updates
        newSocket.on("order_updated", (data) => {
            setOrders((prev) => prev.map((order) => 
                order.order_id === data.order_id ? { ...order, urgent: data.urgent } : order
            ));
        });

        fetch("/api/orders")
            .then((res) => res.json())
            .then((fetchedOrders) => setOrders(fetchedOrders))
            .catch((err) => console.error(err));

        return () => {
            newSocket.disconnect();
        };
    }, []);

    // Separate them into urgent vs. non-urgent
    const urgentOrders = orders.filter((o) => o.urgent);
    const nonUrgentOrders = orders.filter((o) => !o.urgent);

    // Called when user clicks "Save" inside the modal
    const handleSaveAssemblyType = () => {
        // Post to the backend
        fetch("/api/manager/assembly", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ assembly_type: assemblyType }),
        })
            .then((res) => res.json())
            .then((data) => {
                console.log("Assembly type changed:", data);
                setShowSettingsModal(false);
            })
            .catch((err) => console.error("Error saving assembly type:", err));
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
            {/* We pass a callback for opening the modal */}
            <TopBar onSettingsClick={() => setShowSettingsModal(true)} />

            <div className="inventory-page">
                <div className="content-division">
                    <OrdersList
                        title="URGENT ORDERS"
                        orders={urgentOrders}
                        className="urgent-section"
                    />
                    <OrdersList
                        title="NON-URGENT ORDERS"
                        orders={nonUrgentOrders}
                        className="nonurgent-section"
                    />
                </div>
            </div>

            {/* Conditionally render the modal at the top level */}
            {showSettingsModal && (
                <Modal onClose={() => setShowSettingsModal(false)}>
                    <h3>Choose Assembly Type</h3>
                    <div style={{ marginBottom: "10px", textAlign: "left" }}>
                        <label>
                            <input
                                type="radio"
                                value="standard"
                                checked={assemblyType === "standard"}
                                onChange={(e) => setAssemblyType(e.target.value)}
                            />
                            Standard
                        </label>
                        <br />
                        <label>
                            <input
                                type="radio"
                                value="simplified"
                                checked={assemblyType === "simplified"}
                                onChange={(e) => setAssemblyType(e.target.value)}
                            />
                            Simplified
                        </label>
                    </div>

                    <button onClick={handleSaveAssemblyType} style={{ marginRight: "10px" }}>
                        Save
                    </button>
                    <button onClick={() => setShowSettingsModal(false)}>
                        Cancel
                    </button>
                </Modal>
            )}
        </div>
    );
}

export default InventoryPage;