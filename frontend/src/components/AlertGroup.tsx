import React from 'react';
import type { AssetAlertGroup } from '../utils/alertFilters';
import { AlertCard } from './AlertCard';
import './AlertGroup.css';

interface AlertGroupProps {
  group: AssetAlertGroup;
  onAlertExcluded?: () => void;
}

export const AlertGroup: React.FC<AlertGroupProps> = ({ group, onAlertExcluded }) => {
  return (
    <div className="alert-group">
      <div className="alert-group-header">
        <span className="alert-group-name">{group.asset_description || group.asset_code}</span>
        <span className="alert-group-count">{group.alerts.length}</span>
      </div>
      <div className="alert-group-body">
        {group.alerts.map((alert) => (
          <AlertCard
            key={`${alert.asset_code}_${alert.alert_type}_${alert.date}`}
            alert={alert}
            onExclude={onAlertExcluded}
          />
        ))}
      </div>
    </div>
  );
};
