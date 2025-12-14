import { useNavigate } from 'react-router-dom';
import type { HomepageItem } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import './HomepageCard.css';

interface HomepageCardProps {
  item: HomepageItem;
}

export function HomepageCard({ item }: HomepageCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(
      `/asset/${encodeURIComponent(item.asset_symbol)}?exchange=${item.exchange}`,
      {
        state: { description: item.description },
      }
    );
  };

  const handleTradingViewClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = item.tradingview_url || getTradingViewUrl(item.asset_symbol);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  const formatPrice = (price: number, currency: string) => {
    const formatted = price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    if (currency === 'USD') {
      return `${formatted} $`;
    } else if (currency === 'EUR') {
      return `${formatted} €`;
    } else {
      return `${formatted} ${currency}`;
    }
  };

  return (
    <div className="homepage-card" onClick={handleClick}>
      <div className="homepage-card-header">
        <div className="homepage-card-name">{item.description}</div>
        <button
          className="homepage-card-tradingview"
          onClick={handleTradingViewClick}
          title="View on TradingView"
        >
          📊
        </button>
      </div>

      <div className="homepage-card-price">
        {formatPrice(item.current_price, item.currency)}
      </div>

      <div
        className={`homepage-card-variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}
      >
        {formatVariation(item.variation_pct)}
      </div>

      <div className="homepage-card-divider"></div>

      <div className="homepage-card-ma50">
        <div className="homepage-card-ma50-label">MA50</div>
        <div className="homepage-card-ma50-content">
          <div className="homepage-card-ma50-value">
            {formatPrice(item.ma50_value, item.currency)}
          </div>
          <div
            className={`homepage-card-ma50-indicator ${item.is_above_ma50 ? 'above' : 'below'}`}
          >
            {item.is_above_ma50 ? '▲' : '▼'}{' '}
            {item.is_above_ma50 ? 'Above' : 'Below'}
          </div>
        </div>
      </div>
    </div>
  );
}
