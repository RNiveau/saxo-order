import { useEffect, useState } from 'react';
import type { HomepageResponse } from '../services/api';
import { homepageService } from '../services/api';
import { DailyBrief } from './DailyBrief';
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

  return (
    <>
      <DailyBrief />
      {loading ? (
        <div className="home-container">
          <div className="home-message">Loading homepage assets...</div>
        </div>
      ) : error ? (
        <div className="home-container">
          <div className="home-error">{error}</div>
        </div>
      ) : !homepageData || homepageData.items.length === 0 ? (
        <div className="home-container">
          <div className="home-empty">
            No assets on homepage. Add assets from the asset detail page.
          </div>
        </div>
      ) : (
        <div className="home-container">
          <div className="home-grid">
            {homepageData.items.map((item) => (
              <HomepageCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      )}
    </>
  );
}