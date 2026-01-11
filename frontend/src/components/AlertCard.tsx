import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AlertItem } from '../services/api';
import './AlertCard.css';

interface AlertCardProps {
  alert: AlertItem;
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert }) => {
  const navigate = useNavigate();
  const [isDataExpanded, setIsDataExpanded] = useState(false);
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

  const handleAssetClick = () => {
    navigate(`/asset/${encodeURIComponent(alert.asset_code)}?exchange=${alert.exchange}`, {
      state: { description: alert.asset_description }
    });
  };

  return (
    <div className="alert-card">
      <div className="alert-card-header">
        <div className="alert-card-type">
          <span className="alert-type-badge">{formatAlertType(alert.alert_type)}</span>
        </div>
        <div className="alert-card-age">
          <span className="age-label">{getAgeLabel(alert.age_hours)}</span>
        </div>
      </div>
      <div className="alert-card-body">
        <div className="alert-card-asset">
          <h3 className="asset-name" onClick={handleAssetClick}>
            {alert.asset_description}
          </h3>
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
