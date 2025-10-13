import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistService, type WatchlistItem } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import './Watchlist.css';

export function Watchlist() {
  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMarketOpen = () => {
    const now = new Date();
    const hours = now.getHours();
    const day = now.getDay();

    // Market closed on weekends (0 = Sunday, 6 = Saturday)
    if (day === 0 || day === 6) return false;

    // Market open between 9:00 and 17:30 (local time)
    if (hours < 9 || hours >= 18) return false;
    if (hours === 17 && now.getMinutes() >= 30) return false;

    return true;
  };

  useEffect(() => {
    loadWatchlist();

    // Auto-refresh every 30 seconds if market is open
    const intervalId = setInterval(() => {
      if (isMarketOpen()) {
        loadWatchlist();
      }
    }, 30000);

    return () => clearInterval(intervalId);
  }, []);

  const loadWatchlist = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await watchlistService.getWatchlist();
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

  return (
    <div className="watchlist-container">
      <div className="watchlist-header-container">
        <h2>Watchlist</h2>
        <button
          className="reload-button"
          onClick={loadWatchlist}
          disabled={loading}
          title="Reload watchlist"
        >
          🔄 Reload
        </button>
      </div>

      {loading && <div className="loading">Loading watchlist...</div>}

      {error && <div className="error">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="no-items">
          Your watchlist is empty. Add assets by searching for them and clicking "Add to Watchlist".
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="watchlist-list">
          <div className="watchlist-header">
            {items.length} asset{items.length !== 1 ? 's' : ''} in watchlist
          </div>
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
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleAssetClick(item.asset_symbol, item.description)}
                    className="watchlist-row"
                  >
                    <td className="description">
                      <div className="description-with-icon">
                        <span className="description-text">{item.description || item.asset_symbol}</span>
                        <a
                          href={getTradingViewUrl(item.asset_symbol)}
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
