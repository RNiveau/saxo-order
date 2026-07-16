import { useEffect, useState } from 'react';
import { backtestService } from '../services/api';
import type { BacktestDefinition, BacktestDayDetail } from '../services/api';
import './Backtest.css';

export function Backtest() {
  const [definitions, setDefinitions] = useState<BacktestDefinition[]>([]);
  const [selectedDefinition, setSelectedDefinition] = useState<string>('');
  const [date, setDate] = useState<string>('');
  const [dayResult, setDayResult] = useState<BacktestDayDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    backtestService
      .getDefinitions()
      .then((defs) => {
        setDefinitions(defs);
        if (defs.length > 0) {
          setSelectedDefinition(defs[0].code);
        }
      })
      .catch((err) => {
        setError('Failed to load backtest definitions');
        console.error('Backtest definitions error:', err);
      });
  }, []);

  const runSingleDay = async () => {
    if (!selectedDefinition || !date) return;
    setLoading(true);
    setError(null);
    setDayResult(null);
    try {
      const result = await backtestService.getDayDetail(selectedDefinition, date);
      setDayResult(result);
    } catch (err) {
      setError('Failed to run backtest');
      console.error('Backtest run error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatReason = (reason: string) => reason.replace(/_/g, ' ');

  return (
    <div className="backtest-page">
      <h1>Backtest</h1>

      <div className="backtest-controls">
        <label>
          Backtest
          <select
            value={selectedDefinition}
            onChange={(e) => setSelectedDefinition(e.target.value)}
          >
            {definitions.map((def) => (
              <option key={def.code} value={def.code}>
                {def.display_name} ({def.instrument})
              </option>
            ))}
          </select>
        </label>

        <label>
          Date
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>

        <button onClick={runSingleDay} disabled={loading || !selectedDefinition || !date}>
          {loading ? 'Running...' : 'Run'}
        </button>
      </div>

      {error && <div className="backtest-error">{error}</div>}

      {dayResult && (
        <div className="backtest-day-result">
          <h2>{dayResult.date}</h2>

          {dayResult.status === 'no_data' && (
            <p className="backtest-status backtest-status--no-data">
              No data available for this day.
            </p>
          )}

          {dayResult.status === 'no_trade' && (
            <p className="backtest-status backtest-status--no-trade">
              No trade this day (H1 range: {dayResult.h1_low} - {dayResult.h1_high}).
            </p>
          )}

          {dayResult.status === 'traded' && (
            <>
              <p className="backtest-h1-range">
                H1 range: {dayResult.h1_low} - {dayResult.h1_high}
              </p>
              <table className="backtest-trades-table">
                <thead>
                  <tr>
                    <th>Entry time</th>
                    <th>Entry price</th>
                    <th>Exit time</th>
                    <th>Exit price</th>
                    <th>Exit reason</th>
                    <th>Points</th>
                  </tr>
                </thead>
                <tbody>
                  {dayResult.trades.map((trade, index) => (
                    <tr key={index}>
                      <td>{trade.entry_time}</td>
                      <td>{trade.entry_price}</td>
                      <td>{trade.exit_time}</td>
                      <td>{trade.exit_price}</td>
                      <td>{formatReason(trade.exit_reason)}</td>
                      <td className={trade.points >= 0 ? 'positive' : 'negative'}>
                        {trade.points}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  );
}
