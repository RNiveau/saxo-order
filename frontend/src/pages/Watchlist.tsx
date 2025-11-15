import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistService, type WatchlistItem } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import { isMarketOpen } from '../utils/marketHours';
import './Watchlist.css';

export function Watchlist() {
  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTag, setSelectedTag] = useState<string>('');

  useEffect(() => {
    loadWatchlist();

    let intervalId: NodeJS.Timeout | null = null;

    // Function to start/stop auto-refresh based on visibility
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Reload immediately when tab becomes visible
        if (isMarketOpen()) {
          loadWatchlist();
        }
        // Start auto-refresh when tab becomes visible
        if (!intervalId) {
          intervalId = setInterval(() => {
            if (isMarketOpen()) {
              loadWatchlist();
            }
          }, 60000); // 1 minute
        }
      } else {
        // Stop auto-refresh when tab is hidden
        if (intervalId) {
          clearInterval(intervalId);
          intervalId = null;
        }
      }
    };

    // Start auto-refresh immediately if visible
    handleVisibilityChange();

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const loadWatchlist = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await watchlistService.getAllWatchlist();
      setItems(data.items);
    } catch (err) {
      setError('Failed to load watchlist');
      console.error('Watchlist error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAssetClick = (symbol: string, description: string) => {
    navigate(`/asset/${encodeURIComponent(symbol)}`, { state: { description } });
  };

  const formatPrice = (price: number) => {
    return price.toFixed(2);
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  // Get all unique tags from items
  const allTags = Array.from(
    new Set(items.flatMap(item => item.labels || []))
  ).sort();

  // Filter items by selected tag
  const filteredItems = selectedTag
    ? items.filter(item => item.labels?.includes(selectedTag))
    : items;

  return (
    <div className="watchlist-container">
      <div className="watchlist-header-container">
        <h2>Watchlist {loading && <span className="loading-indicator">🔄</span>}</h2>
        <button
          className="reload-button"
          onClick={loadWatchlist}
          disabled={loading}
          title="Reload watchlist"
        >
          🔄 Reload
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {!error && items.length === 0 && !loading && (
        <div className="no-items">
          Your watchlist is empty. Add assets by searching for them and clicking "Add to Watchlist".
        </div>
      )}

      {items.length > 0 && (
        <div className="watchlist-list">
          <div className="watchlist-header">
            {filteredItems.length} asset{filteredItems.length !== 1 ? 's' : ''}
            {selectedTag ? ` with tag "${selectedTag}"` : ' in watchlist'}
          </div>

          {allTags.length > 0 && (
            <div className="tag-filter">
              <button
                className={`filter-tag ${!selectedTag ? 'active' : ''}`}
                onClick={() => setSelectedTag('')}
              >
                All ({items.length})
              </button>
              {allTags.map(tag => (
                <button
                  key={tag}
                  className={`filter-tag ${selectedTag === tag ? 'active' : ''}`}
                  onClick={() => setSelectedTag(tag)}
                >
                  {tag} ({items.filter(item => item.labels?.includes(tag)).length})
                </button>
              ))}
            </div>
          )}
          <div className="watchlist-table">
            <table>
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Symbol</th>
                  <th>Current Price</th>
                  <th>Variation</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleAssetClick(item.asset_symbol, item.description)}
                    className="watchlist-row"
                  >
                    <td className="description">
                      <div className="description-with-icon">
                        <div className="description-with-tags">
                          <span className="description-text">{item.description || item.asset_symbol}</span>
                          {item.labels && item.labels.length > 0 && (
                            <div className="tags-container">
                              {item.labels.map((label, idx) => (
                                <span key={idx} className="tag">{label}</span>
                              ))}
                            </div>
                          )}
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
                    <td className="price">{formatPrice(item.current_price)}</td>
                    <td className={`variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}>
                      {formatVariation(item.variation_pct)}
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
