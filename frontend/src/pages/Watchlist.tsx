import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistService, type WatchlistItem } from '../services/api';
import './Watchlist.css';

export function Watchlist() {
  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWatchlist();
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

  const handleAssetClick = (symbol: string) => {
    navigate(`/asset/${encodeURIComponent(symbol)}`);
  };

  const formatPrice = (price: number) => {
    return price.toFixed(2);
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  return (
    <div className="watchlist-container">
      <h2>Watchlist</h2>

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
                  <th>Symbol</th>
                  <th>Current Price</th>
                  <th>Variation</th>
                  <th>Added At</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleAssetClick(item.asset_symbol)}
                    className="watchlist-row"
                  >
                    <td className="symbol">{item.asset_symbol}</td>
                    <td className="price">{formatPrice(item.current_price)}</td>
                    <td className={`variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}>
                      {formatVariation(item.variation_pct)}
                    </td>
                    <td className="added-at">{formatDate(item.added_at)}</td>
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
