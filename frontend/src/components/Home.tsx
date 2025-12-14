import { useEffect, useState } from 'react';
import { homepageService, type HomepageResponse } from '../services/api';
import { HomepageCard } from './HomepageCard';
import './Home.css';

export function Home() {
  const [homepageData, setHomepageData] = useState<HomepageResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHomepage = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await homepageService.getHomepageAssets();
      setHomepageData(data);
    } catch (err) {
      setError('Failed to load homepage assets');
      console.error('Homepage fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHomepage();

    const interval = setInterval(() => {
      fetchHomepage();
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  if (loading && !homepageData) {
    return (
      <div className="home-container">
        <div className="home-loading">Loading homepage assets...</div>
      </div>
    );
  }

  if (error && !homepageData) {
    return (
      <div className="home-container">
        <div className="home-error">{error}</div>
      </div>
    );
  }

  if (!homepageData || homepageData.items.length === 0) {
    return (
      <div className="home-container">
        <div className="home-empty">
          <p>No assets on homepage.</p>
          <p>Add assets from the asset detail page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="home-container">
      <h1 className="home-title">Homepage Assets</h1>
      <div className="home-grid">
        {homepageData.items.map((item) => (
          <HomepageCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}