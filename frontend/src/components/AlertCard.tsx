import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AlertItem } from '../services/api';
import { getTradingViewUrl } from '../utils/tradingview';
import { assetDetailsService } from '../services/api';
import './AlertCard.css';

interface AlertCardProps {
  alert: AlertItem;
  onExclude?: () => void;
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert, onExclude }) => {
  const navigate = useNavigate();
  const [isDataExpanded, setIsDataExpanded] = useState(false);
  const [isExcluding, setIsExcluding] = useState(false);

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatAlertType = (type: string): string => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getAgeLabel = (hours: number): string => {
    if (hours < 1) return 'Just now';
    if (hours === 1) return '1 hour ago';
    if (hours < 24) return `${hours} hours ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return '1 day ago';
    return `${days} days ago`;
  };

  const formatMA50Slope = (slope: any): string => {
    // Handle null, undefined, or non-numeric values
    if (slope === null || slope === undefined || slope === '') {
      return 'N/A';
    }

    // Convert to number if it's a string
    const numericSlope = typeof slope === 'number' ? slope : parseFloat(slope);

    // Check if conversion was successful
    if (isNaN(numericSlope)) {
      return 'N/A';
    }

    const sign = numericSlope > 0 ? '+' : '';
    return `${sign}${numericSlope.toFixed(1)}%`;
  };

  const getMA50SlopeClass = (slope: any): string => {
    // Handle null, undefined, or non-numeric values
    if (slope === null || slope === undefined || slope === '') {
      return 'ma50-slope-neutral';
    }

    // Convert to number if it's a string
    const numericSlope = typeof slope === 'number' ? slope : parseFloat(slope);

    // Check if conversion was successful
    if (isNaN(numericSlope)) {
      return 'ma50-slope-neutral';
    }

    return numericSlope >= 0 ? 'ma50-slope-positive' : 'ma50-slope-negative';
  };

  const handleAssetClick = () => {
    const symbol = alert.country_code
      ? `${alert.asset_code}:${alert.country_code}`
      : alert.asset_code;
    navigate(`/asset/${encodeURIComponent(symbol)}?exchange=${alert.exchange}`, {
      state: { description: alert.asset_description }
    });
  };

  const handleTradingViewClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const assetSymbol = alert.country_code
      ? `${alert.asset_code}:${alert.country_code}`
      : alert.asset_code;
    // Use custom TradingView URL if configured, otherwise generate default URL
    const url = alert.tradingview_url || getTradingViewUrl(assetSymbol);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Extract MA50 slope from alert data
  const ma50Slope = alert.data?.ma50_slope;

  const handleExcludeClick = async (e: React.MouseEvent) => {
    e.stopPropagation();

    if (!confirm(`Exclude "${alert.asset_description}" from alerts?\n\nThis will hide all future alerts for this asset.`)) {
      return;
    }

    setIsExcluding(true);
    try {
      const assetId = alert.country_code
        ? `${alert.asset_code}:${alert.country_code}`
        : alert.asset_code;

      await assetDetailsService.updateExclusion(assetId, true);

      if (onExclude) {
        onExclude();
      }
    } catch (error) {
      console.error('Failed to exclude asset:', error);
      alert('Failed to exclude asset. Please try again.');
    } finally {
      setIsExcluding(false);
    }
  };

  return (
    <div className="alert-card">
      <div className="alert-card-header">
        <div className="alert-card-type">
          <span className="alert-type-badge">{formatAlertType(alert.alert_type)}</span>
        </div>
        <div className="alert-card-header-right">
          <span className="age-label">{getAgeLabel(alert.age_hours)}</span>
          <button
            className="exclude-button"
            onClick={handleExcludeClick}
            disabled={isExcluding}
            title="Exclude this asset from alerts"
          >
            🚫
          </button>
        </div>
      </div>
      <div className="alert-card-body">
        <div className="alert-card-asset">
          <div className="asset-name-row">
            <h3 className="asset-name" onClick={handleAssetClick}>
              {alert.asset_description}
            </h3>
            <button
              className="tradingview-button"
              onClick={handleTradingViewClick}
              title="View on TradingView"
            >
              📊
            </button>
          </div>
        </div>
        <div className="alert-card-ma50">
          <span className="ma50-label">MA50 Slope:</span>
          <span className={`ma50-value ${getMA50SlopeClass(ma50Slope)}`}>
            {formatMA50Slope(ma50Slope)}
          </span>
        </div>
        <div className="alert-card-timestamp">
          <span className="timestamp">{formatDate(alert.date)}</span>
        </div>
        <div className="alert-card-data">
          <div
            className="data-header"
            onClick={() => setIsDataExpanded(!isDataExpanded)}
          >
            <span>Data</span>
            <span className="expand-icon">{isDataExpanded ? '▼' : '▶'}</span>
          </div>
          {isDataExpanded && (
            <pre className="data-content">{JSON.stringify(alert.data, null, 2)}</pre>
          )}
        </div>
      </div>
    </div>
  );
};
