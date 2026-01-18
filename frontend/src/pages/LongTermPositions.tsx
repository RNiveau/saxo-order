import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistService, type WatchlistItem } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import { isMarketOpen } from '../utils/marketHours';
import './LongTermPositions.css';

export function LongTermPositions() {
  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();

    let intervalId: NodeJS.Timeout | null = null;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        if (isMarketOpen()) {
          loadData();
        }
        if (!intervalId) {
          intervalId = setInterval(() => {
            if (isMarketOpen()) {
              loadData();
            }
          }, 60000);
        }
      } else {
        if (intervalId) {
          clearInterval(intervalId);
          intervalId = null;
        }
      }
    };

    handleVisibilityChange();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await watchlistService.getLongTermPositions();
      setItems(data.items);
    } catch (err) {
      setError('Failed to load long-term positions');
      console.error('Long-term positions error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAssetClick = (symbol: string, description: string, exchange: string) => {
    navigate(`/asset/${encodeURIComponent(symbol)}?exchange=${exchange}`, { state: { description } });
  };

  const formatPrice = (price: number) => {
    return price.toFixed(2);
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  const isStalePrice = (lastUpdated: string): boolean => {
    const now = new Date();
    const updated = new Date(lastUpdated);
    const diffMinutes = (now.getTime() - updated.getTime()) / (1000 * 60);
    return diffMinutes > 15;
  };

  const handleRemoveLongTermTag = async (e: React.MouseEvent, assetId: string, currentLabels: string[]) => {
    e.stopPropagation();

    try {
      const updatedLabels = currentLabels.filter(label => label !== 'long-term');
      await watchlistService.updateLabels(assetId, updatedLabels);
      await loadData();
      alert('Long-term tag removed successfully');
    } catch (err) {
      console.error('Failed to remove long-term tag:', err);
      alert('Failed to remove long-term tag');
    }
  };

  const handleDeleteAsset = async (e: React.MouseEvent, assetId: string, description: string) => {
    e.stopPropagation();

    const confirmed = window.confirm(
      `Are you sure you want to delete "${description}" from your watchlist?\n\nThis action cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    try {
      await watchlistService.removeFromWatchlist(assetId);
      await loadData();
      alert('Asset deleted successfully');
    } catch (err) {
      console.error('Failed to delete asset:', err);
      alert('Failed to delete asset');
    }
  };

  return (
    <div className="long-term-positions-container">
      <div className="long-term-positions-header-container">
        <h2>Long-Term Positions {loading && <span className="loading-indicator">🔄</span>}</h2>
        <button
          className="reload-button"
          onClick={loadData}
          disabled={loading}
          title="Reload long-term positions"
        >
          🔄 Reload
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {!error && items.length === 0 && !loading && (
        <div className="no-items">
          No long-term positions found. Tag assets with "long-term" in your watchlist to see them here.
        </div>
      )}

      {items.length > 0 && (
        <div className="long-term-positions-list">
          <div className="long-term-positions-header">
            {items.length} long-term position{items.length !== 1 ? 's' : ''}
          </div>
          <div className="long-term-positions-table">
            <table>
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Symbol</th>
                  <th>Current Price</th>
                  <th>Variation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleAssetClick(item.asset_symbol, item.description, item.exchange)}
                    className="long-term-positions-row"
                  >
                    <td className="description">
                      <div className="description-with-icon">
                        <div className="description-with-tags">
                          <span className="description-text">{item.description || item.asset_symbol}</span>
                          <div className="tags-container">
                            {item.labels?.includes('crypto') && (
                              <span className="tag crypto-badge">₿ Crypto</span>
                            )}
                          </div>
                        </div>
                        <a
                          href={getTradingViewUrl(item.asset_symbol, item.tradingview_url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tradingview-icon"
                          onClick={(e) => e.stopPropagation()}
                          title="View on TradingView"
                        >
                          📈
                        </a>
                      </div>
                    </td>
                    <td className="symbol">{item.asset_symbol}</td>
                    <td className="price">
                      {formatPrice(item.current_price)}
                      {isStalePrice(item.added_at) && (
                        <span className="stale-indicator" title="Price data may be outdated (>15 minutes old)">
                          ⚠️
                        </span>
                      )}
                    </td>
                    <td className={`variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}>
                      {formatVariation(item.variation_pct)}
                    </td>
                    <td className="actions">
                      <button
                        className="remove-btn"
                        onClick={(e) => handleRemoveLongTermTag(e, item.id, item.labels || [])}
                        title="Remove long-term tag (asset remains in All Watchlist)"
                      >
                        ❌ Remove Tag
                      </button>
                      <button
                        className="delete-btn"
                        onClick={(e) => handleDeleteAsset(e, item.id, item.description)}
                        title="Delete asset from watchlist"
                      >
                        🗑️ Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
