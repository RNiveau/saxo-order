import { useEffect, useState } from 'react';
import type { AlertItem } from '../services/api';
import { alertService } from '../services/api';
import { AlertCard } from '../components/AlertCard';
import { processAlerts } from '../utils/alertFilters';
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

  // Sort state - default to MA50 slope (descending)
  const [sortBy, setSortBy] = useState<'ma50_slope' | 'date'>('ma50_slope');

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
      const processedAlerts = processAlerts(data.alerts);
      setAlerts(processedAlerts);
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
  const filteredAlerts = alerts
    .filter((alert) => {
      if (selectedAssetCode && alert.asset_code !== selectedAssetCode) {
        return false;
      }
      if (selectedAlertType && alert.alert_type !== selectedAlertType) {
        return false;
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'ma50_slope') {
        // Sort by MA50 slope descending (highest slope first)
        // Treat missing/null values as 0
        const aSlope = a.data?.ma50_slope ?? 0;
        const bSlope = b.data?.ma50_slope ?? 0;
        return bSlope - aSlope; // Descending order
      } else {
        // Sort by date descending (newest first)
        return new Date(b.date).getTime() - new Date(a.date).getTime();
      }
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

      {/* Filter and Sort Controls */}
      <div className="filter-controls">
        <div className="filter-group">
          <label htmlFor="sort-by">Sort By</label>
          <select
            id="sort-by"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'ma50_slope' | 'date')}
            className="filter-select"
          >
            <option value="ma50_slope">MA50 Slope (Trend Strength)</option>
            <option value="date">Recent (Date)</option>
          </select>
        </div>

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
            : 'No active alerts. Alerts from the last 5 days will appear here.'}
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
