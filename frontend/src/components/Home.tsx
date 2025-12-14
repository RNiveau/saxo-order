import { useEffect, useState } from 'react';
import type { HomepageResponse } from '../services/api';
import { homepageService } from '../services/api';
import { HomepageCard } from './HomepageCard';
import './Home.css';

export function Home() {
  const [homepageData, setHomepageData] = useState<HomepageResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHomepage = async () => {
    try {
      setError(null);
      const data = await homepageService.getHomepageAssets();
      setHomepageData(data);
    } catch (err) {
      console.error('Failed to fetch homepage assets:', err);
      setError('Failed to load homepage assets. Please try again later.');
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

  if (loading) {
    return (
      <div className="home-container">
        <div className="home-message">Loading homepage assets...</div>
      </div>
    );
  }

  if (error) {
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
          No assets on homepage. Add assets from the asset detail page.
        </div>
      </div>
    );
  }

  return (
    <div className="home-container">
      <div className="home-grid">
        {homepageData.items.map((item) => (
          <HomepageCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}