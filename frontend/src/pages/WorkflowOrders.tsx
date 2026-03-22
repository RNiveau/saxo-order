import { useEffect, useState } from 'react';
import type { AllWorkflowOrderItem } from '../services/api';
import { workflowService } from '../services/api';
import './WorkflowOrders.css';

function WorkflowOrders() {
  const [orders, setOrders] = useState<AllWorkflowOrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowFilter, setWorkflowFilter] = useState('');
  const [directionFilter, setDirectionFilter] = useState('all');

  const loadOrders = async () => {
    try {
      setError(null);
      const response = await workflowService.getAllOrders();
      setOrders(response.orders);
    } catch (err) {
      console.error('Error loading workflow orders:', err);
      setError('Failed to load workflow orders. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const workflowNames = [...new Set(orders.map((o) => o.workflow_name))];

  const filteredOrders = orders.filter((order) => {
    if (workflowFilter && order.workflow_name !== workflowFilter) return false;
    if (directionFilter !== 'all' && order.order_direction !== directionFilter) return false;
    return true;
  });

  const formatDate = (epochSeconds: number) => {
    return new Date(epochSeconds * 1000).toLocaleString();
  };

  if (loading) {
    return (
      <div className="workflow-orders-container">
        <div className="workflow-orders-header">
          <h1>Workflow Orders</h1>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading orders...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="workflow-orders-container">
        <div className="workflow-orders-header">
          <h1>Workflow Orders</h1>
        </div>
        <div className="error-state">
          <p className="error-message">{error}</p>
          <button onClick={loadOrders} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="workflow-orders-container">
      <div className="workflow-orders-header">
        <h1>Workflow Orders</h1>
        <p className="orders-count">
          {filteredOrders.length} of {orders.length} order(s)
        </p>
      </div>

      <div className="workflow-orders-filters">
        <div className="filter-group">
          <label>Workflow:</label>
          <select
            className="filter-select"
            value={workflowFilter}
            onChange={(e) => setWorkflowFilter(e.target.value)}
          >
            <option value="">All workflows</option>
            {workflowNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Direction:</label>
          <select
            className="filter-select"
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value)}
          >
            <option value="all">All</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </div>
      </div>

      {filteredOrders.length === 0 ? (
        <div className="empty-state">
          <p>No recent workflow orders</p>
        </div>
      ) : (
        <table className="workflow-orders-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Workflow</th>
              <th>Asset</th>
              <th>Direction</th>
              <th>Price</th>
              <th>Quantity</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((order) => (
              <tr key={order.id}>
                <td>{formatDate(order.placed_at)}</td>
                <td>{order.workflow_name}</td>
                <td>{order.order_code}</td>
                <td>
                  <span
                    className={`direction-badge ${order.order_direction.toLowerCase()}`}
                  >
                    {order.order_direction}
                  </span>
                </td>
                <td>{order.order_price.toFixed(2)}</td>
                <td>{order.order_quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default WorkflowOrders;
