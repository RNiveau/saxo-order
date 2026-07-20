/**
 * The backend returns naive-UTC ISO datetime strings (no "Z"/offset) for
 * all backtest timestamps (candle dates, trade entry/exit times) - the
 * strategy itself is defined in Paris exchange local time, so the
 * detail view must convert back to Europe/Paris before display,
 * otherwise the audit view is 1-2h off depending on DST.
 */
export function formatParisTime(isoString: string | null): string {
  if (!isoString) return '-';
  const utcIso = isoString.endsWith('Z') ? isoString : `${isoString}Z`;
  const date = new Date(utcIso);
  if (Number.isNaN(date.getTime())) return isoString;

  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Europe/Paris',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
}
