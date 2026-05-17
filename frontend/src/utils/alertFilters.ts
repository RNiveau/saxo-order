import type { AlertItem } from '../services/api';

export const FIVE_DAYS_HOURS = 120;

export const filterRecentAlerts = (
  alerts: AlertItem[],
  maxAgeHours: number = FIVE_DAYS_HOURS
): AlertItem[] => {
  const now = new Date();
  return alerts.filter(alert => {
    if (!alert.date) {
      console.warn(`Invalid date for alert ${alert.id}: date field is missing`);
      return false;
    }

    const alertDate = new Date(alert.date);
    if (isNaN(alertDate.getTime())) {
      console.warn(`Invalid date for alert ${alert.id}: ${alert.date}`);
      return false;
    }

    const ageHours = (now.getTime() - alertDate.getTime()) / (1000 * 60 * 60);
    return ageHours <= maxAgeHours;
  });
};

export const deduplicateAlertsByType = (alerts: AlertItem[]): AlertItem[] => {
  const keyMap = new Map<string, AlertItem>();

  for (const alert of alerts) {
    const key = `${alert.asset_code}:${alert.country_code || 'null'}:${alert.alert_type}`;
    const existing = keyMap.get(key);

    if (!existing || new Date(alert.date) > new Date(existing.date)) {
      keyMap.set(key, alert);
    }
  }

  return Array.from(keyMap.values());
};

export const processAlerts = (alerts: AlertItem[]): AlertItem[] => {
  const recent = filterRecentAlerts(alerts);
  const deduped = deduplicateAlertsByType(recent);
  return deduped.sort((a, b) =>
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};

export interface AssetAlertGroup {
  key: string;
  asset_code: string;
  country_code: string | null;
  asset_description: string;
  alerts: AlertItem[];
}

export const groupAlertsByAsset = (alerts: AlertItem[]): AssetAlertGroup[] => {
  const groups = new Map<string, AssetAlertGroup>();

  for (const alert of alerts) {
    const key = `${alert.asset_code}__${alert.country_code ?? ''}`;
    const existing = groups.get(key);

    if (existing) {
      existing.alerts.push(alert);
    } else {
      groups.set(key, {
        key,
        asset_code: alert.asset_code,
        country_code: alert.country_code,
        asset_description: alert.asset_description,
        alerts: [alert],
      });
    }
  }

  return Array.from(groups.values());
};
