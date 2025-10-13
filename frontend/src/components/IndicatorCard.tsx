import type { AssetIndicatorsResponse } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import './IndicatorCard.css';

interface IndicatorCardProps {
  indicators: AssetIndicatorsResponse;
}

export function IndicatorCard({ indicators }: IndicatorCardProps) {
  const formatPrice = (price: number) => {
    return price.toFixed(4);
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

  return (
    <div className="indicator-card">
      <div className="indicator-header">
        <h3>Market Indicators</h3>
        <div className="indicator-header-actions">
          <span className="unit-time-badge">{indicators.unit_time}</span>
          <a
            href={getTradingViewUrl(indicators.asset_symbol)}
            target="_blank"
            rel="noopener noreferrer"
            className="tradingview-link"
            title="View on TradingView"
          >
            📊 TradingView
          </a>
        </div>
      </div>

      <div className="price-section">
        <div className="price-info">
          <div className="current-price">
            <span className="label">Current Price</span>
            <span className="value">{formatPrice(indicators.current_price)}</span>
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
              <div className="ma-value">{formatPrice(ma.value)}</div>
              <div className={`ma-status ${ma.is_above ? 'above' : 'below'}`}>
                {ma.is_above ? 'Above MA' : 'Below MA'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
