import { useEffect, useState } from 'react';
import type { AlertItem } from '../services/api';
import { alertService } from '../services/api';
import { AlertCard } from '../components/AlertCard';
import './Alerts.css';

export function Alerts() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await alertService.getAll();
      setAlerts(data.alerts);
    } catch (err) {
      setError('Failed to load alerts');
      console.error('Alerts error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="alerts-container">
      <div className="alerts-header-container">
        <h2>Alerts {loading && <span className="loading-indicator">🔄</span>}</h2>
        <button
          className="reload-button"
          onClick={loadAlerts}
          disabled={loading}
          title="Reload alerts"
        >
          🔄 Reload
        </button>
      </div>

      {error && (
        <div className="error">
          {error}
          <button onClick={loadAlerts} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!error && alerts.length === 0 && !loading && (
        <div className="no-items">
          No active alerts. Alerts from the last 7 days will appear here.
        </div>
      )}

      {!error && alerts.length > 0 && (
        <div className="alerts-list">
          <div className="alerts-count">
            {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
          </div>
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
