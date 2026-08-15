const toIsoDay = (date: Date): string => {
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
};

/**
 * A workflow stops running once its end date is in the past: the engine only
 * executes it while `end_date >= today` (engines/workflow_engine.py).
 */
export const isWorkflowExpired = (
  endDate: string | null | undefined,
  today: Date = new Date()
): boolean => {
  if (!endDate) return false;
  return endDate.slice(0, 10) < toIsoDay(today);
};

/**
 * Compare two end dates for the End Date column. Workflows without an end date
 * never expire and stay at the bottom of the list in both sort directions.
 * Returns 0 when the direction should be applied by the caller.
 */
export const compareEndDates = (
  a: string | null,
  b: string | null,
  order: 'asc' | 'desc'
): number => {
  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;
  if (a === b) return 0;
  const ascending = a < b ? -1 : 1;
  return order === 'asc' ? ascending : -ascending;
};
