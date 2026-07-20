import { useEffect, useState } from 'react';
import type { AlertDigest } from '../services/api';
import { alertDigestService } from '../services/api';
import { DailyBriefCarousel } from './DailyBriefCarousel';
import './DailyBrief.css';

const RECENT_DIGESTS_LIMIT = 14;
const COLLAPSED_STORAGE_KEY = 'daily_brief_collapsed';

export function DailyBrief() {
  const [digests, setDigests] = useState<AlertDigest[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSED_STORAGE_KEY) === 'true'
  );

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSED_STORAGE_KEY, String(next));
      return next;
    });
  };

  useEffect(() => {
    const fetchDigests = async () => {
      try {
        setError(null);
        const data = await alertDigestService.listRecent(
          RECENT_DIGESTS_LIMIT
        );
        setDigests(data.digests);
        setIndex(0);
      } catch (err) {
        console.error('Failed to fetch alert digests:', err);
        setError('Failed to load the daily brief.');
      } finally {
        setLoading(false);
      }
    };
    fetchDigests();
  }, []);

  if (loading) {
    return (
      <div className="daily-brief-container">
        <div className="daily-brief-message">Loading daily brief...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="daily-brief-container">
        <div className="daily-brief-error">{error}</div>
      </div>
    );
  }

  if (digests.length === 0) {
    return null;
  }

  const digest = digests[index];

  return (
    <div className="daily-brief-container">
      <DailyBriefCarousel
        digest={digest}
        hasPrev={index < digests.length - 1}
        hasNext={index > 0}
        onPrev={() => setIndex((i) => Math.min(i + 1, digests.length - 1))}
        onNext={() => setIndex((i) => Math.max(i - 1, 0))}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
      />
    </div>
  );
}
