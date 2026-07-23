import { useEffect, useState } from 'react';
import { backtestService } from '../services/api';
import type {
  BacktestDefinition,
  BacktestDayDetail as BacktestDayDetailData,
  BacktestParameters,
  BacktestRunResponse,
} from '../services/api';
import { BacktestDayDetail } from '../components/BacktestDayDetail';
import './Backtest.css';

type Mode = 'day' | 'range';

// Strategy thresholds. Each field is pre-filled from the selected
// definition's default_parameters (CAC40 50/10/20/20, GER40 150/10/50/40);
// clearing a field falls back to that same backend default (not sent).
const PARAM_FIELDS: { key: keyof BacktestParameters; label: string }[] = [
  { key: 'stop_loss_points', label: 'Stop loss (pts)' },
  { key: 'take_profit_offset_points', label: 'Take profit offset (pts)' },
  { key: 'break_even_trigger_points', label: 'Break-even trigger (pts)' },
  { key: 'max_entry_distance_points', label: 'Max entry distance (pts)' },
];

const paramValuesFromDefinition = (
  definition?: BacktestDefinition
): Record<string, string> =>
  Object.fromEntries(
    PARAM_FIELDS.map((f) => [
      f.key,
      definition ? String(definition.default_parameters[f.key]) : '',
    ])
  );

const formatReason = (reason: string) => reason.replace(/_/g, ' ');

const pointsClass = (points: number) => (points >= 0 ? 'positive' : 'negative');

// Matches the backend's Paris-local "today" (Europe/Paris), not the
// browser's UTC day, so the client-side check agrees with the API's.
const parisToday = () =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Paris' }).format(new Date());

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

  const [paramValues, setParamValues] = useState<Record<string, string>>(
    paramValuesFromDefinition
  );
  const [appliedParams, setAppliedParams] = useState<BacktestParameters>({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedDef = definitions.find((d) => d.code === selectedDefinition);

  const buildParameters = (): BacktestParameters => {
    const params: BacktestParameters = {};
    PARAM_FIELDS.forEach(({ key }) => {
      const raw = paramValues[key];
      if (raw !== undefined && raw.trim() !== '') {
        const value = Number(raw);
        if (!Number.isNaN(value)) {
          params[key] = value;
        }
      }
    });
    return params;
  };

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

  useEffect(() => {
    const def = definitions.find((d) => d.code === selectedDefinition);
    if (def) {
      setParamValues(paramValuesFromDefinition(def));
    }
  }, [selectedDefinition, definitions]);

  const runSingleDay = async () => {
    if (!selectedDefinition || !date) return;
    setLoading(true);
    setError(null);
    setDayResult(null);
    const parameters = buildParameters();
    setAppliedParams(parameters);
    try {
      const result = await backtestService.getDayDetail(selectedDefinition, date, parameters);
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

    const today = parisToday();
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
    const parameters = buildParameters();
    setAppliedParams(parameters);
    try {
      const result = await backtestService.runRange(selectedDefinition, startDate, endDate, parameters);
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
      const result = await backtestService.getDayDetail(selectedDefinition, dayDate, appliedParams);
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

      <div className="backtest-parameters">
        <span className="backtest-parameters-title">Parameters</span>
        <div className="backtest-parameters-fields">
          {PARAM_FIELDS.map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                type="number"
                min="0"
                step="any"
                value={paramValues[field.key] ?? ''}
                placeholder={
                  selectedDef ? String(selectedDef.default_parameters[field.key]) : ''
                }
                onChange={(e) =>
                  setParamValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                }
              />
            </label>
          ))}
          <button
            type="button"
            className="backtest-parameters-reset"
            onClick={() => setParamValues(paramValuesFromDefinition(selectedDef))}
          >
            Reset
          </button>
        </div>
      </div>

      {error && <div className="backtest-error">{error}</div>}

      {mode === 'day' && dayResult && (
        <BacktestDayDetail
          detail={dayResult}
          definition={selectedDefinition}
          parameters={appliedParams}
        />
      )}

      {mode === 'range' && runResult && (
        <div className="backtest-range-result">
          <button
            className="backtest-export-csv"
            onClick={() =>
              backtestService.exportRunCsv(selectedDefinition, startDate, endDate, appliedParams)
            }
          >
            Export CSV
          </button>

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
              <BacktestDayDetail
                detail={drilldown}
                definition={selectedDefinition}
                parameters={appliedParams}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
