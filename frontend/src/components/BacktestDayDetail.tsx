import { backtestService } from '../services/api';
import type { BacktestDayDetail as BacktestDayDetailData } from '../services/api';
import { formatParisTime } from '../utils/backtestTime';
import './BacktestDayDetail.css';

const formatReason = (reason: string) => reason.replace(/_/g, ' ');
const pointsClass = (points: number) => (points >= 0 ? 'positive' : 'negative');
// Backend sends the Direction enum value ("Buy"/"Sell"); the backtest
// speaks in long/short terms, so present it that way.
const formatDirection = (direction: string) =>
  direction === 'Buy' ? 'long' : 'short';

interface BacktestDayDetailProps {
  detail: BacktestDayDetailData;
  definition: string;
}

export function BacktestDayDetail({ detail, definition }: BacktestDayDetailProps) {
  return (
    <div className="backtest-day-detail">
      <div className="backtest-day-detail-header">
        <h2>{detail.date}</h2>
        <button onClick={() => backtestService.exportDayCsv(definition, detail.date)}>
          Export CSV
        </button>
      </div>

      {detail.status === 'no_data' && (
        <p className="backtest-status backtest-status--no-data">
          No data available for this day.
        </p>
      )}

      {detail.status === 'no_trade' && (
        <p className="backtest-status backtest-status--no-trade">
          No trade this day (H1 range: {detail.h1_low} - {detail.h1_high}).
        </p>
      )}

      {detail.status === 'traded' && (
        <>
          <p className="backtest-h1-range">
            H1 range: {detail.h1_low} - {detail.h1_high}
          </p>

          <table className="backtest-trades-table">
            <thead>
              <tr>
                <th>Direction</th>
                <th>Entry time (Paris)</th>
                <th>Entry price</th>
                <th>Exit time (Paris)</th>
                <th>Exit price</th>
                <th>Exit reason</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              {detail.trades.map((trade, index) => (
                <tr key={index}>
                  <td className={`backtest-direction backtest-direction--${formatDirection(trade.direction)}`}>
                    {formatDirection(trade.direction)}
                  </td>
                  <td>{formatParisTime(trade.entry_time)}</td>
                  <td>{trade.entry_price}</td>
                  <td>{formatParisTime(trade.exit_time)}</td>
                  <td>{trade.exit_price}</td>
                  <td>{formatReason(trade.exit_reason)}</td>
                  <td className={pointsClass(trade.points)}>{trade.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {detail.candles.length > 0 && (
        <details className="backtest-candles-details">
          <summary>
            5-minute candles from 10:00 Paris time ({detail.candles.length})
          </summary>
          <div className="backtest-candles-scroll">
            <table className="backtest-candles-table">
              <thead>
                <tr>
                  <th>Time (Paris)</th>
                  <th>Open</th>
                  <th>High</th>
                  <th>Low</th>
                  <th>Close</th>
                </tr>
              </thead>
              <tbody>
                {detail.candles.map((candle, index) => (
                  <tr key={index}>
                    <td>{formatParisTime(candle.date)}</td>
                    <td>{candle.open}</td>
                    <td>{candle.higher}</td>
                    <td>{candle.lower}</td>
                    <td>{candle.close}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
