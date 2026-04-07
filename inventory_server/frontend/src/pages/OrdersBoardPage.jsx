import React, { useEffect, useMemo } from "react";

function renderItemsTable(items) {
  const rows = Object.entries(items);

  if (rows.length === 0) {
    return <p className="muted-copy">No items in this order.</p>;
  }

  return (
    <table className="order-items-table">
      <thead>
        <tr>
          <th>Quantity</th>
          <th>Item</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([name, quantity]) => (
          <tr key={name}>
            <td>{quantity}</td>
            <td>{name}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function OrdersBoardPage({ systemState, onRefreshState }) {
  useEffect(() => {
    onRefreshState?.();
    if (!onRefreshState) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      onRefreshState();
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [onRefreshState]);

  const urgentOrders = useMemo(
    () => systemState.orders.filter((order) => order.urgent),
    [systemState.orders]
  );
  const standardOrders = useMemo(
    () => systemState.orders.filter((order) => !order.urgent),
    [systemState.orders]
  );

  return (
    <div className="page-grid">
      <section className="panel split-panel">
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Orders</p>
              <h2>Urgent orders ({urgentOrders.length})</h2>
            </div>
          </div>
          <div className="board-list">
            {urgentOrders.map((order) => (
              <article key={order.order_id} className="board-row urgent">
                <div className="board-header-block">
                  <div className="board-destination-card">
                    <span className="board-station-id">{order.ws_id}</span>
                    <span className="board-side-chip">Side {order.side}</span>
                  </div>
                  <div className="board-order-id">
                    <span className="board-order-id-label">Order ID:</span>
                    <span className="board-order-id-value">{order.order_id}</span>
                  </div>
                </div>
                {renderItemsTable(order.items_dict)}
              </article>
            ))}
            {urgentOrders.length === 0 ? (
              <p className="muted-copy">No urgent orders.</p>
            ) : null}
          </div>
        </div>
        <div>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Orders</p>
              <h2>Standard orders ({standardOrders.length})</h2>
            </div>
          </div>
          <div className="board-list">
            {standardOrders.map((order) => (
              <article key={order.order_id} className="board-row">
                <div className="board-header-block">
                  <div className="board-destination-card">
                    <span className="board-station-id">{order.ws_id}</span>
                    <span className="board-side-chip">Side {order.side}</span>
                  </div>
                  <div className="board-order-id">
                    <span className="board-order-id-label">Order ID:</span>
                    <span className="board-order-id-value">{order.order_id}</span>
                  </div>
                </div>
                {renderItemsTable(order.items_dict)}
              </article>
            ))}
            {standardOrders.length === 0 ? (
              <p className="muted-copy">No standard orders.</p>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
