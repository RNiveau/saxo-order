import { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { indexesService, type WatchlistItem } from '../services/api';
import { isMarketOpen } from '../utils/marketHours';
import { IndexCard } from './IndexCard';
import './Navigation.css';

export function Navigation() {
  const [searchQuery, setSearchQuery] = useState('');
  const [indexes, setIndexes] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadIndexes();

    let intervalId: NodeJS.Timeout | null = null;
    let lastLoadTime = Date.now();

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        const timeSinceLastLoad = Date.now() - lastLoadTime;
        if (isMarketOpen() && timeSinceLastLoad >= 60000) {
          loadIndexes();
          lastLoadTime = Date.now();
        }
        if (!intervalId) {
          intervalId = setInterval(() => {
            if (isMarketOpen() && !document.hidden) {
              loadIndexes();
              lastLoadTime = Date.now();
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

  const loadIndexes = async () => {
    try {
      setLoading(true);
      const data = await indexesService.getIndexes();
      setIndexes(data.items);
    } catch (err) {
      console.error('Indexes error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
    }
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <NavLink to="/">Saxo Order Management</NavLink>
        </div>
        {!loading && indexes.length > 0 && (
          <div className="nav-indexes">
            {indexes.map((index) => (
              <IndexCard key={index.id} item={index} />
            ))}
          </div>
        )}
        <form className="nav-search" onSubmit={handleSearchSubmit}>
          <input
            type="text"
            placeholder="Search assets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="search-button">
            Search
          </button>
        </form>
      </div>
    </nav>
  );
}