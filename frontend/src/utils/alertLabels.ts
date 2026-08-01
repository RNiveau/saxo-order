const ALERT_TYPE_LABELS: Record<string, string> = {
  congestion20: 'Congestion 20',
  congestion100: 'Congestion 100',
  combo: 'Combo',
  double_top: 'Double Top',
  double_bottom: 'Double Bottom',
  double_inside_bar: 'Double Inside Bar',
  containing_candle: 'Containing Candle',
  mm50_touch: 'MM50 Touch',
  mm7_break: 'MM7 Break',
};

const titleCase = (type: string): string =>
  type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

export const getAlertTypeLabel = (type: string): string =>
  ALERT_TYPE_LABELS[type] || titleCase(type);
