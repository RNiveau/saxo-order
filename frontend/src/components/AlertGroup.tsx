import React, { useState } from 'react';
import type { AssetAlertGroup } from '../utils/alertFilters';
import { AlertCard } from './AlertCard';
import './AlertGroup.css';

interface AlertGroupProps {
  group: AssetAlertGroup;
  onAlertExcluded?: () => void;
}

export const AlertGroup: React.FC<AlertGroupProps> = ({ group, onAlertExcluded }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const toggle = () => setIsExpanded((v) => !v);

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  };

  return (
    <div className="alert-group">
      <div
        className="alert-group-header"
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        onClick={toggle}
        onKeyDown={onKeyDown}
      >
        <span className="alert-group-arrow" aria-hidden="true">
          {isExpanded ? '▼' : '▶'}
        </span>
        <span className="alert-group-name">{group.asset_description || group.asset_code}</span>
        <span className="alert-group-count">{group.alerts.length}</span>
      </div>
      {isExpanded && (
        <div className="alert-group-body">
          {group.alerts.map((alert) => (
            <AlertCard
              key={`${alert.asset_code}_${alert.alert_type}_${alert.date}`}
              alert={alert}
              onExclude={onAlertExcluded}
            />
          ))}
        </div>
      )}
    </div>
  );
};
