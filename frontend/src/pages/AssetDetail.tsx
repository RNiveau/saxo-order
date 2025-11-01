import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  workflowService,
  indicatorService,
  watchlistService,
  type WorkflowInfo,
  type AssetWorkflowsResponse,
  type AssetIndicatorsResponse,
} from '../services/api';
import { IndicatorCard } from '../components/IndicatorCard';
import './AssetDetail.css';

export function AssetDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const [workflowData, setWorkflowData] = useState<AssetWorkflowsResponse | null>(null);
  const [indicatorData, setIndicatorData] = useState<AssetIndicatorsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [indicatorLoading, setIndicatorLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indicatorError, setIndicatorError] = useState<string | null>(null);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [watchlistSuccess, setWatchlistSuccess] = useState<string | null>(null);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [checkingWatchlist, setCheckingWatchlist] = useState(false);
  const [isShortTerm, setIsShortTerm] = useState(false);
  const [updatingLabel, setUpdatingLabel] = useState(false);

  useEffect(() => {
    if (symbol) {
      fetchWorkflows(symbol);
      fetchIndicators(symbol);
      checkWatchlistStatus(symbol);
    }
  }, [symbol]);

  const fetchWorkflows = async (assetSymbol: string) => {
    try {
      setLoading(true);
      setError(null);
      const parts = assetSymbol.split(':');
      const code = parts[0];
      const countryCode = parts.length > 1 ? parts[1] : '';
      const data = await workflowService.getAssetWorkflows(code, countryCode);
      setWorkflowData(data);
    } catch (err) {
      setError('Failed to fetch workflows for this asset');
      console.error('Workflow fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchIndicators = async (assetSymbol: string) => {
    try {
      setIndicatorLoading(true);
      setIndicatorError(null);
      // Parse symbol to extract code and country_code
      const parts = assetSymbol.split(':');
      const code = parts[0];
      const countryCode = parts.length > 1 ? parts[1] : '';
      const data = await indicatorService.getAssetIndicators(code, countryCode);
      setIndicatorData(data);
    } catch (err) {
      setIndicatorError('Failed to fetch indicators for this asset');
      console.error('Indicator fetch error:', err);
    } finally {
      setIndicatorLoading(false);
    }
  };

  const checkWatchlistStatus = async (assetSymbol: string) => {
    try {
      setCheckingWatchlist(true);
      const [code] = assetSymbol.split(':');
      const response = await watchlistService.checkWatchlist(code);
      setIsInWatchlist(response.in_watchlist);

      // If in watchlist, get the full watchlist to check labels
      if (response.in_watchlist) {
        const watchlistData = await watchlistService.getWatchlist();
        const item = watchlistData.items.find(item => item.id === code);
        if (item) {
          setIsShortTerm(item.labels.includes('short-term'));
        }
      }
    } catch (err) {
      console.error('Check watchlist error:', err);
    } finally {
      setCheckingWatchlist(false);
    }
  };

  const handleToggleWatchlist = async () => {
    if (!symbol) return;

    try {
      setAddingToWatchlist(true);
      setWatchlistError(null);
      setWatchlistSuccess(null);

      // Parse symbol to extract code and country_code
      const parts = symbol.split(':');
      const code = parts[0];
      const countryCode = parts.length > 1 ? parts[1] : '';
      const assetName = indicatorData?.description || symbol;

      if (isInWatchlist) {
        // Remove from watchlist
        await watchlistService.removeFromWatchlist(code);
        setWatchlistSuccess(`Removed ${assetName} from watchlist`);
        setIsInWatchlist(false);
        setIsShortTerm(false);
      } else {
        // Add to watchlist
        const description = 'placeholder';
        await watchlistService.addToWatchlist({
          asset_id: code,
          asset_symbol: symbol,
          description: description,
          country_code: countryCode,
        });
        setWatchlistSuccess(`Added ${assetName} to watchlist`);
        setIsInWatchlist(true);
      }

      setTimeout(() => setWatchlistSuccess(null), 3000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to update watchlist';
      setWatchlistError(errorMessage);
      console.error('Watchlist toggle error:', err);
      setTimeout(() => setWatchlistError(null), 5000);
    } finally {
      setAddingToWatchlist(false);
    }
  };

  const handleToggleShortTerm = async () => {
    if (!symbol) return;

    try {
      setUpdatingLabel(true);
      setWatchlistError(null);
      setWatchlistSuccess(null);

      const [code] = symbol.split(':');
      const assetName = indicatorData?.description || symbol;

      // Toggle the short-term label
      const newLabels = isShortTerm ? [] : ['short-term'];
      await watchlistService.updateLabels(code, newLabels);

      setIsShortTerm(!isShortTerm);
      const action = isShortTerm ? 'Removed from' : 'Added to';
      setWatchlistSuccess(`${action} short-term positions: ${assetName}`);

      setTimeout(() => setWatchlistSuccess(null), 3000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to update label';
      setWatchlistError(errorMessage);
      console.error('Label toggle error:', err);
      setTimeout(() => setWatchlistError(null), 5000);
    } finally {
      setUpdatingLabel(false);
    }
  };

  const renderWorkflowStatus = (workflow: WorkflowInfo) => {
    if (!workflow.enabled) {
      return <span className="status-badge disabled">✗ Disabled</span>;
    }
    if (workflow.dry_run) {
      return (
        <>
          <span className="status-badge enabled">✓ Enabled</span>
          <span className="status-badge dry-run">Dry Run</span>
        </>
      );
    }
    return <span className="status-badge enabled">✓ Enabled</span>;
  };

  return (
    <div className="asset-detail-container">
      <div className="asset-header">
        <div className="asset-title">
          <h2>{indicatorData?.description || symbol}</h2>
          {indicatorData?.description && <div className="asset-symbol">{symbol}</div>}
        </div>
        <div className="asset-actions">
          <button
            onClick={handleToggleWatchlist}
            disabled={addingToWatchlist || checkingWatchlist}
            className="add-to-watchlist-btn"
          >
            {addingToWatchlist
              ? isInWatchlist
                ? 'Removing...'
                : 'Adding...'
              : isInWatchlist
              ? '- Remove from Watchlist'
              : '+ Add to Watchlist'}
          </button>
          {isInWatchlist && (
            <button
              onClick={handleToggleShortTerm}
              disabled={updatingLabel || checkingWatchlist}
              className={`short-term-btn ${isShortTerm ? 'active' : ''}`}
            >
              {updatingLabel
                ? isShortTerm
                  ? 'Removing...'
                  : 'Adding...'
                : isShortTerm
                ? '⭐ Close Short Term Position'
                : '⭐ Short Term Position'}
            </button>
          )}
        </div>
      </div>

      {watchlistSuccess && <div className="success">{watchlistSuccess}</div>}
      {watchlistError && <div className="error">{watchlistError}</div>}

      {/* Indicators Section */}
      {indicatorLoading && <div className="loading">Loading indicators...</div>}
      {indicatorError && <div className="error">{indicatorError}</div>}
      {!indicatorLoading && !indicatorError && indicatorData && (
        <IndicatorCard indicators={indicatorData} />
      )}

      {/* Workflows Section */}
      {loading && <div className="loading">Loading workflows...</div>}

      {error && <div className="error">{error}</div>}

      {!loading && !error && workflowData && (
        <>
          {workflowData.total === 0 ? (
            <div className="no-workflows">
              No workflows found for asset: {workflowData.asset_symbol}
            </div>
          ) : (
            <div className="workflows-section">
              <div className="workflows-header">
                <h3>Workflows for {workflowData.asset_symbol}</h3>
                <div className="workflow-count">
                  Total: {workflowData.total} workflow{workflowData.total !== 1 ? 's' : ''}
                </div>
              </div>

              <div className="workflows-list">
                {workflowData.workflows.map((workflow, index) => (
                  <div key={index} className="workflow-card">
                    <div className="workflow-header">
                      <h4>{workflow.name}</h4>
                      <div className="workflow-status">
                        {renderWorkflowStatus(workflow)}
                      </div>
                    </div>

                    <div className="workflow-details">
                      <div className="detail-row">
                        <span className="label">Index:</span>
                        <span className="value">{workflow.index}</span>
                      </div>
                      <div className="detail-row">
                        <span className="label">CFD:</span>
                        <span className="value">{workflow.cfd}</span>
                      </div>
                      {workflow.end_date && (
                        <div className="detail-row">
                          <span className="label">End Date:</span>
                          <span className="value">{workflow.end_date}</span>
                        </div>
                      )}
                      {workflow.is_us && (
                        <div className="detail-row">
                          <span className="label">Market:</span>
                          <span className="value badge-us">US Market</span>
                        </div>
                      )}
                    </div>

                    <div className="workflow-section">
                      <h5>Conditions</h5>
                      <div className="conditions-list">
                        {workflow.conditions.map((condition, condIndex) => (
                          <div key={condIndex} className="condition-item">
                            <div className="condition-text">
                              <span className="indicator-name">
                                {condition.indicator.name}
                              </span>
                              <span className="indicator-ut">
                                {condition.indicator.unit_time}
                              </span>
                              {condition.indicator.value !== undefined && (
                                <span className="indicator-value">
                                  = {condition.indicator.value}
                                </span>
                              )}
                              {condition.indicator.zone_value !== undefined && (
                                <span className="indicator-zone">
                                  (zone: {condition.indicator.zone_value})
                                </span>
                              )}
                              <span className="direction">
                                {condition.close.direction}
                              </span>
                              <span className="close-label">close</span>
                              <span className="close-ut">
                                {condition.close.unit_time}
                              </span>
                              {condition.close.value !== undefined && (
                                <span className="close-value">
                                  ({condition.close.value})
                                </span>
                              )}
                              {condition.element && (
                                <span className="element">
                                  [{condition.element}]
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="workflow-section">
                      <h5>Trigger</h5>
                      <div className="trigger-info">
                        <div className="trigger-text">
                          <span className="trigger-signal">{workflow.trigger.signal}</span>
                          <span className="trigger-location">{workflow.trigger.location}</span>
                          <span className="arrow">→</span>
                          <span className={`trigger-direction ${workflow.trigger.order_direction}`}>
                            {workflow.trigger.order_direction.toUpperCase()}
                          </span>
                          <span className="trigger-quantity">
                            (qty: {workflow.trigger.quantity})
                          </span>
                        </div>
                        <div className="trigger-detail">
                          Unit Time: <span className="value">{workflow.trigger.unit_time}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
