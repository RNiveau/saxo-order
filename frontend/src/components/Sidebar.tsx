import { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { watchlistService, type WatchlistItem } from '../services/api';
import { isMarketOpen } from '../utils/marketHours';
import './Sidebar.css';

export function Sidebar() {
  const navigate = useNavigate();
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWatchlist();

    let intervalId: NodeJS.Timeout | null = null;
    let lastLoadTime = Date.now();

    // Function to start/stop auto-refresh based on visibility
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Reload only if more than 1 minute has passed since last load
        const timeSinceLastLoad = Date.now() - lastLoadTime;
        if (isMarketOpen() && timeSinceLastLoad >= 60000) {
          loadWatchlist();
          lastLoadTime = Date.now();
        }
        // Start auto-refresh when tab becomes visible
        if (!intervalId) {
          intervalId = setInterval(() => {
            if (isMarketOpen() && !document.hidden) {
              loadWatchlist();
              lastLoadTime = Date.now();
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
      const data = await watchlistService.getWatchlist();
      setWatchlistItems(data.items);
    } catch (err) {
      setError('Failed to load watchlist');
      console.error('Watchlist error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleWatchlistItemClick = (symbol: string, description: string) => {
    navigate(`/asset/${encodeURIComponent(symbol)}`, { state: { description } });
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        <ul className="sidebar-menu">
          <li>
            <NavLink
              to="/"
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              <span className="icon">🏠</span>
              <span className="label">Home</span>
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/available-funds"
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              <span className="icon">💰</span>
              <span className="label">Available Funds</span>
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/watchlist"
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              <span className="icon">⭐</span>
              <span className="label">Watchlist</span>
            </NavLink>
          </li>
        </ul>
      </nav>

      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <span className="icon">📊</span>
          <span className="label">Live Watchlist</span>
          <button
            className="reload-button"
            onClick={loadWatchlist}
            disabled={loading}
            title="Reload watchlist"
          >
            🔄
          </button>
        </div>

        {loading && <div className="sidebar-loading">Loading...</div>}
        {error && <div className="sidebar-error">{error}</div>}

        {!loading && !error && watchlistItems.length === 0 && (
          <div className="sidebar-empty">
            No items in watchlist
          </div>
        )}

        {!loading && watchlistItems.length > 0 && (
          <ul className="watchlist-items">
            {watchlistItems.map((item, index) => {
              const isShortTerm = item.labels.includes('short-term');
              const prevItem = index > 0 ? watchlistItems[index - 1] : null;
              const prevIsShortTerm = prevItem?.labels.includes('short-term');
              const showDivider = prevIsShortTerm && !isShortTerm;

              return (
                <li key={item.id}>
                  {showDivider && <div className="watchlist-divider" />}
                  <div
                    className="watchlist-item"
                    onClick={() => handleWatchlistItemClick(item.asset_symbol, item.description)}
                  >
                    <div className="watchlist-item-name">
                      {item.description || item.asset_symbol}
                    </div>
                    <div className="watchlist-item-symbol">
                      {item.asset_symbol}
                    </div>
                    <div className="watchlist-item-details">
                      <span className="price">{item.current_price.toFixed(2)}</span>
                      <span className={`variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}>
                        {formatVariation(item.variation_pct)}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
