import { useNavigate } from 'react-router-dom';
import type { AlertDigest, TriagedAsset, WorkflowTrigger } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import './DailyBriefCarousel.css';

interface DailyBriefCarouselProps {
  digest: AlertDigest;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

const CONVICTION_BADGE: Record<string, string> = {
  high: '🔴',
  watch: '🟡',
};

function formatTriggerHour(placedAt: number): string {
  return new Date(placedAt * 1000).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Paris',
  });
}

interface TriggerGroup {
  key: string;
  workflowName: string;
  direction: WorkflowTrigger['direction'];
  dryRun: boolean;
  count: number;
  firstAt: number;
  lastAt: number;
}

function groupTriggers(triggers: WorkflowTrigger[]): TriggerGroup[] {
  const groups: TriggerGroup[] = [];
  const byKey = new Map<string, TriggerGroup>();

  for (const trigger of triggers) {
    const key = `${trigger.workflow_name}|${trigger.direction}|${trigger.dry_run}`;
    const existing = byKey.get(key);
    if (existing) {
      existing.count += 1;
      existing.firstAt = Math.min(existing.firstAt, trigger.placed_at);
      existing.lastAt = Math.max(existing.lastAt, trigger.placed_at);
      continue;
    }
    const group: TriggerGroup = {
      key,
      workflowName: trigger.workflow_name,
      direction: trigger.direction,
      dryRun: trigger.dry_run,
      count: 1,
      firstAt: trigger.placed_at,
      lastAt: trigger.placed_at,
    };
    byKey.set(key, group);
    groups.push(group);
  }

  return groups;
}

function assetSymbol(asset: TriagedAsset): string {
  return asset.country_code
    ? `${asset.asset_code}:${asset.country_code}`
    : asset.asset_code;
}

function AssetRow({ asset }: { asset: TriagedAsset }) {
  const navigate = useNavigate();

  const handleAssetClick = () => {
    const symbol = assetSymbol(asset);
    navigate(
      `/asset/${encodeURIComponent(symbol)}?exchange=${asset.exchange}`,
      { state: { description: asset.asset_description } }
    );
  };

  const handleTradingViewClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = asset.tradingview_url || getTradingViewUrl(assetSymbol(asset));
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="daily-brief-asset">
      <div className="daily-brief-asset-row">
        <span className="daily-brief-asset-badge">
          {CONVICTION_BADGE[asset.conviction] ?? ''}
        </span>
        <span className="daily-brief-asset-name" onClick={handleAssetClick}>
          {asset.asset_description} ({asset.asset_code})
        </span>
        <button
          className="daily-brief-asset-tradingview"
          onClick={handleTradingViewClick}
          title="View on TradingView"
        >
          📊
        </button>
      </div>
      {asset.rationale && (
        <div className="daily-brief-asset-rationale">{asset.rationale}</div>
      )}
      {groupTriggers(asset.workflow_triggers ?? []).map((group) => (
        <div className="daily-brief-asset-trigger" key={group.key}>
          <span
            className={`daily-brief-trigger-direction ${group.direction.toLowerCase()}`}
          >
            {group.direction === 'BUY' ? '▲' : '▼'} {group.direction}
          </span>
          <span className="daily-brief-trigger-name">{group.workflowName}</span>
          {group.count > 1 && (
            <span className="daily-brief-trigger-count">×{group.count}</span>
          )}
          <span className="daily-brief-trigger-hour">
            {group.count > 1
              ? `${formatTriggerHour(group.firstAt)} → ${formatTriggerHour(group.lastAt)}`
              : formatTriggerHour(group.firstAt)}
          </span>
          {group.dryRun && (
            <span className="daily-brief-trigger-dryrun">dry run</span>
          )}
        </div>
      ))}
    </div>
  );
}

export function DailyBriefCarousel({
  digest,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  collapsed,
  onToggleCollapsed,
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
          <button
            className="daily-brief-collapse"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? 'Expand' : 'Collapse'}
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? '▸' : '▾'}
          </button>
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

      {!collapsed && (
        <>
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
              + {noiseCount} lower-conviction signal
              {noiseCount > 1 ? 's' : ''}
            </div>
          )}
        </>
      )}
    </div>
  );
}
