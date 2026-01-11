import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import {
  workflowService,
  indicatorService,
  watchlistService,
  alertService,
  type WorkflowInfo,
  type AssetWorkflowsResponse,
  type AssetIndicatorsResponse,
  type AlertItem,
} from '../services/api';
import { IndicatorCard } from '../components/IndicatorCard';
import { AlertCard } from '../components/AlertCard';
import './AssetDetail.css';

export function AssetDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const exchange = searchParams.get('exchange') || 'saxo';
  const [workflowData, setWorkflowData] = useState<AssetWorkflowsResponse | null>(null);
  const [indicatorData, setIndicatorData] = useState<AssetIndicatorsResponse | null>(null);
  const [weeklyIndicatorData, setWeeklyIndicatorData] = useState<AssetIndicatorsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [indicatorLoading, setIndicatorLoading] = useState(false);
  const [weeklyIndicatorLoading, setWeeklyIndicatorLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indicatorError, setIndicatorError] = useState<string | null>(null);
  const [weeklyIndicatorError, setWeeklyIndicatorError] = useState<string | null>(null);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [watchlistSuccess, setWatchlistSuccess] = useState<string | null>(null);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [checkingWatchlist, setCheckingWatchlist] = useState(false);
  const [isShortTerm, setIsShortTerm] = useState(false);
  const [isLongTerm, setIsLongTerm] = useState(false);
  const [isHomepage, setIsHomepage] = useState(false);
  const [updatingLabel, setUpdatingLabel] = useState(false);

  // Alerts state
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [alertsData, setAlertsData] = useState<AlertItem[]>([]);
  const [alertsExpanded, setAlertsExpanded] = useState(false);

  useEffect(() => {
    if (symbol) {
      fetchWorkflows(symbol);
      fetchIndicators(symbol);
      fetchWeeklyIndicators(symbol);
      checkWatchlistStatus(symbol);
      fetchAlerts(symbol);
    }
  }, [symbol]);

  const fetchWorkflows = async (assetSymbol: string) => {
    try {
      setLoading(true);
      setError(null);
      // Handle both Saxo (CODE:MARKET) and Binance (SYMBOL) formats
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
      // Handle both Saxo (CODE:MARKET) and Binance (SYMBOL) formats
      const parts = assetSymbol.split(':');
      const code = parts[0];
      const countryCode = parts.length > 1 ? parts[1] : '';

      const data = await indicatorService.getAssetIndicators(code, countryCode, 'daily', exchange);
      setIndicatorData(data);
    } catch (err) {
      setIndicatorError('Failed to fetch indicators for this asset');
      console.error('Indicator fetch error:', err);
    } finally {
      setIndicatorLoading(false);
    }
  };

  const fetchWeeklyIndicators = async (assetSymbol: string) => {
    try {
      setWeeklyIndicatorLoading(true);
      setWeeklyIndicatorError(null);
      // Handle both Saxo (CODE:MARKET) and Binance (SYMBOL) formats
      const parts = assetSymbol.split(':');
      const code = parts[0];
      const countryCode = parts.length > 1 ? parts[1] : '';

      const data = await indicatorService.getAssetIndicators(code, countryCode, 'weekly', exchange);
      setWeeklyIndicatorData(data);
    } catch (err) {
      setWeeklyIndicatorError('Failed to fetch weekly indicators for this asset');
      console.error('Weekly indicator fetch error:', err);
    } finally {
      setWeeklyIndicatorLoading(false);
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
        const watchlistData = await watchlistService.getAllWatchlist();
        const item = watchlistData.items.find(item => item.id === code);
        if (item) {
          setIsShortTerm(item.labels.includes('short-term'));
          setIsLongTerm(item.labels.includes('long-term'));
          setIsHomepage(item.labels.includes('homepage'));
        }
      }
    } catch (err) {
      console.error('Check watchlist error:', err);
    } finally {
      setCheckingWatchlist(false);
    }
  };

  const fetchAlerts = async (assetSymbol: string) => {
    try {
      setAlertsLoading(true);
      setAlertsError(null);

      // Parse symbol to extract code and country_code
      const parts = assetSymbol.split(':');
      const code = parts[0];
      const countryCode = parts.length > 1 ? parts[1] : '';

      // Fetch alerts filtered by asset_code and country_code
      const data = await alertService.getAll({
        asset_code: code,
        country_code: countryCode,
      });

      setAlertsData(data.alerts);
    } catch (err) {
      setAlertsError('Unable to load alerts. Please try refreshing the page.');
      console.error('Alerts fetch error:', err);
    } finally {
      setAlertsLoading(false);
    }
  };

  const handleToggleWatchlist = async () => {
    if (!symbol) return;

    try {
      setAddingToWatchlist(true);
      setWatchlistError(null);
      setWatchlistSuccess(null);

      // Handle both Saxo (CODE:MARKET) and Binance (SYMBOL) formats
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
        setIsLongTerm(false);
        setIsHomepage(false);
      } else {
        // Add to watchlist
        const description = 'placeholder';
        await watchlistService.addToWatchlist({
          asset_id: code,
          asset_symbol: symbol,
          description: description,
          country_code: countryCode,
          exchange: exchange,
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

      // Build labels array keeping long-term if it exists, toggling short-term
      const newLabels: string[] = [];
      if (isLongTerm) newLabels.push('long-term');
      if (!isShortTerm) newLabels.push('short-term');

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

  const handleToggleLongTerm = async () => {
    if (!symbol) return;

    try {
      setUpdatingLabel(true);
      setWatchlistError(null);
      setWatchlistSuccess(null);

      const [code] = symbol.split(':');
      const assetName = indicatorData?.description || symbol;

      // Build labels array keeping short-term if it exists, toggling long-term
      const newLabels: string[] = [];
      if (isShortTerm) newLabels.push('short-term');
      if (!isLongTerm) newLabels.push('long-term');

      await watchlistService.updateLabels(code, newLabels);

      setIsLongTerm(!isLongTerm);
      const action = isLongTerm ? 'Removed from' : 'Added to';
      setWatchlistSuccess(`${action} long-term positions: ${assetName}`);

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

  const handleToggleHomepage = async () => {
    if (!symbol) return;

    try {
      setUpdatingLabel(true);
      setWatchlistError(null);
      setWatchlistSuccess(null);

      const [code] = symbol.split(':');
      const assetName = indicatorData?.description || symbol;

      // Build labels array keeping existing labels, toggling homepage
      const newLabels: string[] = [];
      if (isShortTerm) newLabels.push('short-term');
      if (isLongTerm) newLabels.push('long-term');
      if (!isHomepage) newLabels.push('homepage');

      await watchlistService.updateLabels(code, newLabels);

      setIsHomepage(!isHomepage);
      const action = isHomepage ? 'Removed from' : 'Pinned to';
      setWatchlistSuccess(`${action} homepage: ${assetName}`);

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

  const handleCreateOrder = () => {
    if (!symbol || !indicatorData) return;

    const parts = symbol.split(':');
    const code = parts[0];
    const countryCode = parts.length > 1 ? parts[1].toLowerCase() : '';
    const currentPrice = indicatorData.current_price || 0;

    const queryParams = new URLSearchParams({
      code: code,
      country_code: countryCode,
      price: currentPrice.toString(),
      exchange: exchange,
      prefill: 'true'
    });

    navigate(`/orders?${queryParams.toString()}`);
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
            <>
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
              <button
                onClick={handleToggleLongTerm}
                disabled={updatingLabel || checkingWatchlist}
                className={`long-term-btn ${isLongTerm ? 'active' : ''}`}
              >
                {updatingLabel
                  ? isLongTerm
                    ? 'Removing...'
                    : 'Adding...'
                  : isLongTerm
                  ? '📊 Long Term Position'
                  : '📊 Long Term Position'}
              </button>
              <button
                onClick={handleToggleHomepage}
                disabled={updatingLabel || checkingWatchlist}
                className={`homepage-btn ${isHomepage ? 'active' : ''}`}
              >
                {updatingLabel
                  ? isHomepage
                    ? 'Removing...'
                    : 'Adding...'
                  : isHomepage
                  ? '🏠 Remove from Homepage'
                  : '🏠 Pin to Homepage'}
              </button>
            </>
          )}
          <button
            onClick={handleCreateOrder}
            disabled={indicatorLoading || !indicatorData}
            className="create-order-btn"
            title="Create an order for this asset"
          >
            Create Order
          </button>
        </div>
      </div>

      {watchlistSuccess && <div className="success">{watchlistSuccess}</div>}
      {watchlistError && <div className="error">{watchlistError}</div>}

      {/* Indicators Section */}
      <div className="indicators-container">
        <div className="indicator-column">
          {indicatorLoading && <div className="loading">Loading daily indicators...</div>}
          {indicatorError && <div className="error">{indicatorError}</div>}
          {!indicatorLoading && !indicatorError && indicatorData && (
            <IndicatorCard
              indicators={indicatorData}
              onTradingViewUrlUpdated={(url) => {
                setIndicatorData({ ...indicatorData, tradingview_url: url });
              }}
            />
          )}
        </div>
        <div className="indicator-column">
          {weeklyIndicatorLoading && <div className="loading">Loading weekly indicators...</div>}
          {weeklyIndicatorError && <div className="error">{weeklyIndicatorError}</div>}
          {!weeklyIndicatorLoading && !weeklyIndicatorError && weeklyIndicatorData && (
            <IndicatorCard
              indicators={weeklyIndicatorData}
              onTradingViewUrlUpdated={(url) => {
                setWeeklyIndicatorData({ ...weeklyIndicatorData, tradingview_url: url });
              }}
            />
          )}
        </div>
      </div>

      {/* Alerts Section */}
      <div className="alerts-section">
        <h3>Alerts</h3>

        {alertsLoading && <div className="loading">Loading alerts...</div>}

        {alertsError && <div className="error">{alertsError}</div>}

        {!alertsLoading && !alertsError && alertsData.length === 0 && (
          <div className="empty-state">No active alerts for this asset</div>
        )}

        {!alertsLoading && !alertsError && alertsData.length > 0 && (
          <>
            <div className="alerts-list">
              {(alertsExpanded ? alertsData : alertsData.slice(0, 3)).map((alert) => (
                <AlertCard key={alert.id} alert={alert} />
              ))}
            </div>

            {alertsData.length > 3 && (
              <button
                className="expand-alerts-btn"
                onClick={() => setAlertsExpanded(!alertsExpanded)}
              >
                {alertsExpanded ? 'Show Less' : `Show All (${alertsData.length} alerts)`}
              </button>
            )}
          </>
        )}
      </div>

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
