import { useState } from 'react';
import type { AssetIndicatorsResponse } from '../services/api';
import { tradingViewService } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import './IndicatorCard.css';

interface IndicatorCardProps {
  indicators: AssetIndicatorsResponse;
  onTradingViewUrlUpdated?: (url: string) => void;
}

export function IndicatorCard({ indicators, onTradingViewUrlUpdated }: IndicatorCardProps) {
  const [showModal, setShowModal] = useState(false);
  const [tradingViewUrl, setTradingViewUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formatPrice = (price: number, currency: string) => {
    // Format with thousands separator
    const formatted = price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

    // Add currency symbol on the right
    if (currency === 'USD') {
      return `${formatted} $`;
    } else if (currency === 'EUR') {
      return `${formatted} €`;
    } else {
      return `${formatted} ${currency}`;
    }
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  const getVariationClass = (variation: number) => {
    if (variation > 0) return 'positive';
    if (variation < 0) return 'negative';
    return 'neutral';
  };

  const handleEditClick = () => {
    setTradingViewUrl(indicators.tradingview_url || '');
    setError(null);
    setShowModal(true);
  };

  const handleSave = async () => {
    const assetId = indicators.asset_symbol.split(':')[0];
    setSaving(true);
    setError(null);

    try {
      await tradingViewService.setTradingViewLink(assetId, tradingViewUrl);
      setShowModal(false);
      if (onTradingViewUrlUpdated) {
        onTradingViewUrlUpdated(tradingViewUrl);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save TradingView URL');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setShowModal(false);
    setError(null);
  };

  return (
    <div className="indicator-card">
      <div className="indicator-header">
        <h3>Market Indicators</h3>
        <div className="indicator-header-actions">
          <span className="unit-time-badge">{indicators.unit_time}</span>
          <a
            href={getTradingViewUrl(indicators.asset_symbol, indicators.tradingview_url)}
            target="_blank"
            rel="noopener noreferrer"
            className="tradingview-link"
            title="View on TradingView"
          >
            📊 TradingView
          </a>
          <button
            onClick={handleEditClick}
            className="edit-tradingview-btn"
            title="Edit TradingView URL"
          >
            ✏️
          </button>
        </div>
      </div>

      <div className="price-section">
        <div className="price-info">
          <div className="current-price">
            <span className="label">Current Price</span>
            <span className="value">{formatPrice(indicators.current_price, indicators.currency)}</span>
          </div>
          <div className={`variation ${getVariationClass(indicators.variation_pct)}`}>
            <span className="label">Variation</span>
            <span className="value">{formatVariation(indicators.variation_pct)}</span>
          </div>
        </div>
      </div>

      <div className="moving-averages-section">
        <h4>Moving Averages</h4>
        <div className="ma-grid">
          {indicators.moving_averages.map((ma) => (
            <div key={ma.period} className="ma-item">
              <div className="ma-header">
                <span className="ma-period">MA{ma.period}</span>
                <span className={`ma-indicator ${ma.is_above ? 'above' : 'below'}`}>
                  {ma.is_above ? '▲' : '▼'}
                </span>
              </div>
              <div className="ma-value">{formatPrice(ma.value, indicators.currency)}</div>
              <div className={`ma-status ${ma.is_above ? 'above' : 'below'}`}>
                {ma.is_above ? 'Above MA' : 'Below MA'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={handleCancel}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Edit TradingView URL</h3>
            <p className="modal-description">
              Enter a custom TradingView URL for {indicators.asset_symbol}
            </p>
            <input
              type="text"
              value={tradingViewUrl}
              onChange={(e) => setTradingViewUrl(e.target.value)}
              placeholder="https://www.tradingview.com/chart/?symbol=..."
              className="tradingview-input"
              disabled={saving}
            />
            {error && <div className="error-message">{error}</div>}
            <div className="modal-actions">
              <button
                onClick={handleCancel}
                className="btn-cancel"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="btn-save"
                disabled={saving || !tradingViewUrl.trim()}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
