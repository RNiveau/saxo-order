import { useEffect, useState } from 'react';
import type { AlertItem } from '../services/api';
import { alertService } from '../services/api';
import { AlertCard } from '../components/AlertCard';
import './Alerts.css';

// Alert type display name mapping
const ALERT_TYPE_LABELS: Record<string, string> = {
  congestion20: 'Congestion 20',
  congestion100: 'Congestion 100',
  combo: 'Combo',
  double_top: 'Double Top',
  double_inside_bar: 'Double Inside Bar',
  containing_candle: 'Containing Candle',
};

const getAlertTypeLabel = (type: string): string => {
  return ALERT_TYPE_LABELS[type] || type;
};

export function Alerts() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [selectedAssetCode, setSelectedAssetCode] = useState<string>('');
  const [selectedAlertType, setSelectedAlertType] = useState<string>('');

  // Available filter options from API
  const [availableFilters, setAvailableFilters] = useState<{
    asset_codes: string[];
    alert_types: string[];
    country_codes: string[];
  }>({
    asset_codes: [],
    alert_types: [],
    country_codes: [],
  });

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await alertService.getAll();
      setAlerts(data.alerts);
      setAvailableFilters(data.available_filters);
    } catch (err) {
      setError('Failed to load alerts');
      console.error('Alerts error:', err);
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setSelectedAssetCode('');
    setSelectedAlertType('');
  };

  const hasActiveFilters = selectedAssetCode || selectedAlertType;

  // Client-side filtering
  const filteredAlerts = alerts.filter((alert) => {
    if (selectedAssetCode && alert.asset_code !== selectedAssetCode) {
      return false;
    }
    if (selectedAlertType && alert.alert_type !== selectedAlertType) {
      return false;
    }
    return true;
  });

  // Deduplicate filter options for rendering
  const uniqueAssetCodes = Array.from(new Set(availableFilters.asset_codes));
  const uniqueAlertTypes = Array.from(new Set(availableFilters.alert_types));

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

      {/* Filter Controls */}
      <div className="filter-controls">
        <div className="filter-group">
          <label htmlFor="asset-filter">
            Asset ({uniqueAssetCodes.length})
          </label>
          <select
            id="asset-filter"
            value={selectedAssetCode}
            onChange={(e) => setSelectedAssetCode(e.target.value)}
            className="filter-select"
          >
            <option value="">All Assets</option>
            {uniqueAssetCodes.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="type-filter">
            Type ({uniqueAlertTypes.length})
          </label>
          <select
            id="type-filter"
            value={selectedAlertType}
            onChange={(e) => setSelectedAlertType(e.target.value)}
            className="filter-select"
          >
            <option value="">All Types</option>
            {uniqueAlertTypes.map((type) => (
              <option key={type} value={type}>
                {getAlertTypeLabel(type)}
              </option>
            ))}
          </select>
        </div>

        {hasActiveFilters && (
          <button
            className="clear-filters-button"
            onClick={clearFilters}
            title="Clear all filters"
          >
            ✕ Clear Filters
          </button>
        )}
      </div>

      {error && (
        <div className="error">
          {error}
          <button onClick={loadAlerts} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!error && filteredAlerts.length === 0 && !loading && (
        <div className="no-items">
          {hasActiveFilters
            ? 'No alerts match the selected filters.'
            : 'No active alerts. Alerts from the last 7 days will appear here.'}
        </div>
      )}

      {!error && filteredAlerts.length > 0 && (
        <div className="alerts-list">
          <div className="alerts-count">
            {filteredAlerts.length} alert{filteredAlerts.length !== 1 ? 's' : ''}
            {hasActiveFilters && ` (filtered from ${alerts.length} total)`}
          </div>
          {filteredAlerts.map((alert) => (
            <AlertCard
              key={`${alert.asset_code}_${alert.alert_type}_${alert.date}`}
              alert={alert}
            />
          ))}
        </div>
      )}
    </div>
  );
}
