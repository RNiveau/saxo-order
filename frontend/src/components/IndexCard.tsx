import { useNavigate } from 'react-router-dom';
import type { WatchlistItem } from '../services/api';
import './IndexCard.css';

interface IndexCardProps {
  item: WatchlistItem;
}

export function IndexCard({ item }: IndexCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/asset/${encodeURIComponent(item.asset_symbol)}?exchange=${item.exchange}`, {
      state: { description: item.description }
    });
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
    <div className="index-card" onClick={handleClick}>
      <div className="index-card-name">{item.description}</div>
      <div className="index-card-price">
        {formatPrice(item.current_price, item.currency)}
      </div>
      <div className={`index-card-variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}>
        {formatVariation(item.variation_pct)}
      </div>
    </div>
  );
}
