import { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { AlertItem } from '../services/api';
import { alertService } from '../services/api';
import { AlertCard } from '../components/AlertCard';
import './Alerts.css';

interface AvailableFilters {
  asset_codes: string[];
  alert_types: string[];
  country_codes: string[];
}

export function Alerts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [allAlerts, setAllAlerts] = useState<AlertItem[]>([]);
  const [availableFilters, setAvailableFilters] = useState<AvailableFilters>({
    asset_codes: [],
    alert_types: [],
    country_codes: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state from URL params
  const assetFilter = searchParams.get('asset') || '';
  const typeFilter = searchParams.get('type') || '';

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await alertService.getAll();
      setAllAlerts(data.alerts);
      setAvailableFilters(data.available_filters);
    } catch (err) {
      setError('Failed to load alerts');
      console.error('Alerts error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Client-side filtering
  const filteredAlerts = useMemo(() => {
    return allAlerts.filter((alert) => {
      if (assetFilter && alert.asset_code !== assetFilter) return false;
      if (typeFilter && alert.alert_type !== typeFilter) return false;
      return true;
    });
  }, [allAlerts, assetFilter, typeFilter]);

  const handleAssetFilterChange = (value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set('asset', value);
    } else {
      params.delete('asset');
    }
    setSearchParams(params);
  };

  const handleTypeFilterChange = (value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set('type', value);
    } else {
      params.delete('type');
    }
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  const hasActiveFilters = assetFilter || typeFilter;

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

      {/* Filters Section */}
      <div className="alerts-filters">
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="asset-filter">Asset:</label>
            <select
              id="asset-filter"
              value={assetFilter}
              onChange={(e) => handleAssetFilterChange(e.target.value)}
              disabled={loading}
            >
              <option value="">All Assets ({availableFilters.asset_codes.length})</option>
              {availableFilters.asset_codes.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="type-filter">Type:</label>
            <select
              id="type-filter"
              value={typeFilter}
              onChange={(e) => handleTypeFilterChange(e.target.value)}
              disabled={loading}
            >
              <option value="">All Types ({availableFilters.alert_types.length})</option>
              {availableFilters.alert_types.map((type) => (
                <option key={type} value={type}>
                  {type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilters && (
            <button
              className="clear-filters-button"
              onClick={clearFilters}
              disabled={loading}
              title="Clear all filters"
            >
              Clear Filters
            </button>
          )}
        </div>
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
            {hasActiveFilters && (
              <span className="filter-info"> (filtered from {allAlerts.length} total)</span>
            )}
          </div>
          {filteredAlerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
