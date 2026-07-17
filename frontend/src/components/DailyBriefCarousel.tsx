import type { AlertDigest, TriagedAsset } from '../services/api';
import './DailyBriefCarousel.css';

interface DailyBriefCarouselProps {
  digest: AlertDigest;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}

const CONVICTION_BADGE: Record<string, string> = {
  high: '🔴',
  watch: '🟡',
};

function AssetRow({ asset }: { asset: TriagedAsset }) {
  return (
    <div className="daily-brief-asset">
      <span className="daily-brief-asset-badge">
        {CONVICTION_BADGE[asset.conviction] ?? ''}
      </span>
      <span className="daily-brief-asset-name">
        {asset.asset_description} ({asset.asset_code})
      </span>
      {asset.rationale && (
        <span className="daily-brief-asset-rationale">
          {asset.rationale}
        </span>
      )}
    </div>
  );
}

export function DailyBriefCarousel({
  digest,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
}: DailyBriefCarouselProps) {
  const rankedAssets = digest.triaged_assets
    .filter((asset) => asset.conviction !== 'noise')
    .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  const noiseCount = digest.counts['noise'] ?? 0;

  return (
    <div className="daily-brief-card">
      <div className="daily-brief-header">
        <button
          className="daily-brief-nav"
          onClick={onPrev}
          disabled={!hasPrev}
          aria-label="Previous day"
        >
          ‹
        </button>
        <div className="daily-brief-title">
          <span className="daily-brief-date">{digest.run_date}</span>
          {digest.fallback_used && (
            <span
              className="daily-brief-fallback-badge"
              title="Produced by the deterministic fallback (reasoning was unavailable)"
            >
              fallback
            </span>
          )}
        </div>
        <button
          className="daily-brief-nav"
          onClick={onNext}
          disabled={!hasNext}
          aria-label="Next day"
        >
          ›
        </button>
      </div>

      <div className="daily-brief-summary">{digest.summary}</div>

      {rankedAssets.length > 0 ? (
        <div className="daily-brief-assets">
          {rankedAssets.map((asset) => (
            <AssetRow
              key={`${asset.asset_code}_${asset.country_code ?? ''}`}
              asset={asset}
            />
          ))}
        </div>
      ) : (
        <div className="daily-brief-empty">
          No high or watch signals today.
        </div>
      )}

      {noiseCount > 0 && (
        <div className="daily-brief-noise">
          + {noiseCount} lower-conviction signal{noiseCount > 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
