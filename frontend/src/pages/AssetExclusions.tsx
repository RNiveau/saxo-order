import { useEffect, useState } from 'react';
import type { AssetDetailResponse } from '../services/api';
import { assetDetailsService } from '../services/api';
import './AssetExclusions.css';

export function AssetExclusions() {
  const [assets, setAssets] = useState<AssetDetailResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [updatingAssets, setUpdatingAssets] = useState<Set<string>>(new Set());
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadAssets();
  }, []);

  const loadAssets = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await assetDetailsService.getAllAssets();
      setAssets(data.assets);
    } catch (err) {
      setError('Failed to load assets');
      console.error('Assets error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleExclusion = async (
    assetId: string,
    currentStatus: boolean
  ) => {
    const confirmed = window.confirm(
      `Are you sure you want to ${
        currentStatus ? 'un-exclude' : 'exclude'
      } ${assetId}?`
    );

    if (!confirmed) return;

    setUpdatingAssets((prev) => new Set(prev).add(assetId));
    setError(null);
    setSuccessMessage(null);

    try {
      await assetDetailsService.updateExclusion(assetId, !currentStatus);

      // Update local state
      setAssets((prev) =>
        prev.map((asset) =>
          asset.asset_id === assetId
            ? { ...asset, is_excluded: !currentStatus }
            : asset
        )
      );

      setSuccessMessage(
        `Successfully ${currentStatus ? 'un-excluded' : 'excluded'} ${assetId}`
      );
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(`Failed to update ${assetId}`);
      console.error('Update error:', err);
    } finally {
      setUpdatingAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetId);
        return next;
      });
    }
  };

  // Filter assets by search term
  const filteredAssets = assets.filter((asset) =>
    asset.asset_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Separate excluded and active assets
  const excludedAssets = filteredAssets.filter((a) => a.is_excluded);
  const activeAssets = filteredAssets.filter((a) => !a.is_excluded);

  if (loading) {
    return (
      <div className="asset-exclusions">
        <h1>Asset Exclusion Management</h1>
        <div className="loading">Loading assets...</div>
      </div>
    );
  }

  return (
    <div className="asset-exclusions">
      <h1>Asset Exclusion Management</h1>

      <p className="info-text">
        Excluded assets are skipped during batch alerting runs and their alerts
        are hidden from the alert view.
      </p>

      {error && <div className="error-message">{error}</div>}
      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}

      <div className="search-box">
        <input
          type="text"
          placeholder="Search assets..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="asset-sections">
        {/* Excluded Assets Section */}
        <section className="asset-section">
          <h2>Excluded Assets ({excludedAssets.length})</h2>

          {excludedAssets.length === 0 ? (
            <p className="empty-state">No excluded assets</p>
          ) : (
            <div className="asset-list">
              {excludedAssets.map((asset) => (
                <div key={asset.asset_id} className="asset-item excluded">
                  <div className="asset-info">
                    <span className="asset-id">{asset.asset_id}</span>
                    {asset.tradingview_url && (
                      <a
                        href={asset.tradingview_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="tradingview-link"
                        title="View on TradingView"
                      >
                        📈
                      </a>
                    )}
                    {asset.updated_at && (
                      <span className="updated-at">
                        Updated: {new Date(asset.updated_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() =>
                      handleToggleExclusion(asset.asset_id, true)
                    }
                    disabled={updatingAssets.has(asset.asset_id)}
                    className="toggle-button un-exclude"
                  >
                    {updatingAssets.has(asset.asset_id)
                      ? 'Updating...'
                      : 'Un-exclude'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Active Assets Section */}
        <section className="asset-section">
          <h2>Active Assets ({activeAssets.length})</h2>

          {activeAssets.length === 0 ? (
            <p className="empty-state">No active assets</p>
          ) : (
            <div className="asset-list">
              {activeAssets.map((asset) => (
                <div key={asset.asset_id} className="asset-item active">
                  <div className="asset-info">
                    <span className="asset-id">{asset.asset_id}</span>
                    {asset.tradingview_url && (
                      <a
                        href={asset.tradingview_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="tradingview-link"
                        title="View on TradingView"
                      >
                        📈
                      </a>
                    )}
                    {asset.updated_at && (
                      <span className="updated-at">
                        Updated: {new Date(asset.updated_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() =>
                      handleToggleExclusion(asset.asset_id, false)
                    }
                    disabled={updatingAssets.has(asset.asset_id)}
                    className="toggle-button exclude"
                  >
                    {updatingAssets.has(asset.asset_id)
                      ? 'Updating...'
                      : 'Exclude'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
