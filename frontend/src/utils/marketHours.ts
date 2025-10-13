/**
 * Check if the market is currently open.
 * Market hours: Weekdays 9:00 AM to 5:30 PM (closed on weekends)
 */
export const isMarketOpen = (): boolean => {
  const now = new Date();
  const hours = now.getHours();
  const day = now.getDay();

  // Market closed on weekends (0 = Sunday, 6 = Saturday)
  if (day === 0 || day === 6) return false;

  // Market open between 9:00 and 17:30 (local time)
  if (hours < 9 || hours >= 18) return false;
  if (hours === 17 && now.getMinutes() >= 30) return false;

  return true;
};
