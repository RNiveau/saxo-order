import { useEffect, useState } from 'react';
import { backtestService } from '../services/api';
import type {
  BacktestDefinition,
  BacktestDayDetail as BacktestDayDetailData,
  BacktestRunResponse,
} from '../services/api';
import { BacktestDayDetail } from '../components/BacktestDayDetail';
import './Backtest.css';

type Mode = 'day' | 'range';

const formatReason = (reason: string) => reason.replace(/_/g, ' ');

const pointsClass = (points: number) => (points >= 0 ? 'positive' : 'negative');

export function Backtest() {
  const [definitions, setDefinitions] = useState<BacktestDefinition[]>([]);
  const [selectedDefinition, setSelectedDefinition] = useState<string>('');
  const [mode, setMode] = useState<Mode>('day');

  const [date, setDate] = useState<string>('');
  const [dayResult, setDayResult] = useState<BacktestDayDetailData | null>(null);

  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [runResult, setRunResult] = useState<BacktestRunResponse | null>(null);

  const [drilldown, setDrilldown] = useState<BacktestDayDetailData | null>(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [drilldownError, setDrilldownError] = useState<string | null>(null);

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

  const runDateRange = async () => {
    if (!selectedDefinition || !startDate || !endDate) return;
    setError(null);

    const today = new Date().toISOString().slice(0, 10);
    if (endDate < startDate) {
      setError('End date must not be before start date.');
      return;
    }
    if (startDate > today || endDate > today) {
      setError('Dates must not be in the future.');
      return;
    }

    setLoading(true);
    setRunResult(null);
    setDrilldown(null);
    try {
      const result = await backtestService.runRange(selectedDefinition, startDate, endDate);
      setRunResult(result);
    } catch (err) {
      setError('Failed to run backtest');
      console.error('Backtest range run error:', err);
    } finally {
      setLoading(false);
    }
  };

  const openDrilldown = async (dayDate: string) => {
    if (!selectedDefinition) return;
    setDrilldownLoading(true);
    setDrilldownError(null);
    setDrilldown(null);
    try {
      const result = await backtestService.getDayDetail(selectedDefinition, dayDate);
      setDrilldown(result);
    } catch (err) {
      setDrilldownError('Failed to load day detail');
      console.error('Backtest day detail error:', err);
    } finally {
      setDrilldownLoading(false);
    }
  };

  return (
    <div className="backtest-page">
      <h1>Backtest</h1>

      <div className="backtest-mode-toggle">
        <button
          className={mode === 'day' ? 'active' : ''}
          onClick={() => setMode('day')}
        >
          Single day
        </button>
        <button
          className={mode === 'range' ? 'active' : ''}
          onClick={() => setMode('range')}
        >
          Date range
        </button>
      </div>

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

        {mode === 'day' ? (
          <>
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
          </>
        ) : (
          <>
            <label>
              Start date
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </label>
            <label>
              End date
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </label>
            <button
              onClick={runDateRange}
              disabled={loading || !selectedDefinition || !startDate || !endDate}
            >
              {loading ? 'Running...' : 'Run'}
            </button>
          </>
        )}
      </div>

      {error && <div className="backtest-error">{error}</div>}

      {mode === 'day' && dayResult && <BacktestDayDetail detail={dayResult} />}

      {mode === 'range' && runResult && (
        <div className="backtest-range-result">
          <div className="backtest-summary-grid">
            <div className="backtest-summary-tile">
              <span className="label">Days</span>
              <span className="value">{runResult.summary.number_of_days}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">Trades</span>
              <span className="value">{runResult.summary.number_of_trades}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">Wins</span>
              <span className="value">{runResult.summary.number_of_winning_positions}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">Losses</span>
              <span className="value">{runResult.summary.number_of_losing_positions}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">BE</span>
              <span className="value">{runResult.summary.number_of_be}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">Avg win</span>
              <span className="value">{runResult.summary.average_win ?? '-'}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">Avg loss</span>
              <span className="value">{runResult.summary.average_loss ?? '-'}</span>
            </div>
            <div className="backtest-summary-tile">
              <span className="label">Final result</span>
              <span className={`value ${pointsClass(runResult.summary.final_result)}`}>
                {runResult.summary.final_result}
              </span>
            </div>
          </div>

          <table className="backtest-days-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Status</th>
                <th>Trades</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              {runResult.days.map((day) => {
                const clickable = day.status === 'traded';
                return (
                  <tr
                    key={day.date}
                    className={clickable ? 'backtest-day-row--clickable' : ''}
                    onClick={clickable ? () => openDrilldown(day.date) : undefined}
                  >
                    <td>{day.date}</td>
                    <td>{formatReason(day.status)}</td>
                    <td>{day.trade_count}</td>
                    <td className={pointsClass(day.points)}>{day.points}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {drilldownLoading && <p className="backtest-status">Loading day detail...</p>}
          {drilldownError && <div className="backtest-error">{drilldownError}</div>}
          {drilldown && (
            <div className="backtest-day-drilldown">
              <BacktestDayDetail detail={drilldown} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
