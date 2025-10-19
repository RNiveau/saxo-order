import { useEffect, useState } from 'react';
import {
  fundService,
  reportConfigService,
  reportService,
  type AccountInfo,
  type EnumOption,
  type ReportOrder,
  type ReportSummary,
} from '../services/api';
import './Report.css';

export function Report() {
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [fromDate, setFromDate] = useState<string>('');
  const [orders, setOrders] = useState<ReportOrder[]>([]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<{
    order: ReportOrder;
    index: number;
  } | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await fundService.getAccounts();
      setAccounts(data.accounts);
      if (data.accounts.length > 0) {
        setSelectedAccount(data.accounts[0].account_id);
      }
    } catch (err) {
      setError('Failed to load accounts');
      console.error('Accounts error:', err);
    }
  };

  const loadReport = async () => {
    if (!selectedAccount || !fromDate) {
      setError('Please select an account and from date');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [ordersData, summaryData] = await Promise.all([
        reportService.getOrders(selectedAccount, fromDate),
        reportService.getSummary(selectedAccount, fromDate),
      ]);

      setOrders(ordersData.orders);
      setSummary(summaryData);
    } catch (err) {
      setError('Failed to load report');
      console.error('Report error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOrderClick = (order: ReportOrder, index: number) => {
    setSelectedOrder({ order, index });
    setShowModal(true);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  };

  const formatPrice = (price: number, decimals: number = 2) => {
    return price.toFixed(decimals);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'EUR',
    }).format(amount);
  };

  return (
    <div className="report-container">
      <div className="report-header">
        <h2>📊 Trading Report</h2>

        <div className="report-filters">
          <div className="filter-group">
            <label>Account:</label>
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
            >
              {accounts.map((acc) => (
                <option key={acc.account_id} value={acc.account_id}>
                  {acc.account_name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>From Date:</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
            />
          </div>

          <button
            className="load-button"
            onClick={loadReport}
            disabled={loading || !selectedAccount || !fromDate}
          >
            {loading ? 'Loading...' : 'Load Report'}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {summary && (
        <div className="report-summary">
          <div className="summary-card">
            <div className="summary-label">Total Orders</div>
            <div className="summary-value">{summary.total_orders}</div>
          </div>
          <div className="summary-card">
            <div className="summary-label">Total Volume</div>
            <div className="summary-value">
              {formatCurrency(summary.total_volume_eur)}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-label">Total Fees</div>
            <div className="summary-value">
              {formatCurrency(summary.total_fees_eur)}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-label">BUY Orders</div>
            <div className="summary-value">
              {summary.buy_orders}
              <span className="summary-subvalue">
                {formatCurrency(summary.buy_volume_eur)}
              </span>
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-label">SELL Orders</div>
            <div className="summary-value">
              {summary.sell_orders}
              <span className="summary-subvalue">
                {formatCurrency(summary.sell_volume_eur)}
              </span>
            </div>
          </div>
        </div>
      )}

      {orders.length > 0 && (
        <div className="orders-table-container">
          <table className="orders-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Direction</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Total</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order, index) => (
                <tr key={index}>
                  <td>{formatDate(order.date)}</td>
                  <td>
                    <div className="symbol-cell">
                      <span className="symbol-code">{order.code}</span>
                      <span className="symbol-name">{order.name}</span>
                    </div>
                  </td>
                  <td>
                    <span
                      className={`direction-badge ${order.direction.toLowerCase()}`}
                    >
                      {order.direction === 'BUY' ? '🟢' : '🔴'} {order.direction}
                    </span>
                    {order.asset_type !== 'Stock' && (
                      <span className="asset-type-badge">{order.asset_type}</span>
                    )}
                  </td>
                  <td>{order.quantity}</td>
                  <td>
                    <div className="price-cell">
                      <span className="price-original">
                        {order.currency} {formatPrice(order.price, 4)}
                      </span>
                      {order.price_eur && (
                        <span className="price-eur">
                          € {formatPrice(order.price_eur, 4)}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="total-cell">
                      <span className="total-original">
                        {order.currency} {formatPrice(order.total)}
                      </span>
                      <span className="total-eur">
                        € {formatPrice(order.total_eur)}
                      </span>
                      {order.underlying_price && (
                        <span className="underlying-price">
                          Under: € {formatPrice(order.underlying_price)}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <button
                      className="manage-button"
                      onClick={() => handleOrderClick(order, index)}
                      title="Manage order"
                    >
                      📝
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && orders.length === 0 && fromDate && (
        <div className="no-orders">
          No orders found for the selected date range.
        </div>
      )}

      {showModal && selectedOrder && (
        <OrderModal
          order={selectedOrder.order}
          orderIndex={selectedOrder.index}
          accountId={selectedAccount}
          accountName={accounts.find(a => a.account_id === selectedAccount)?.account_name || selectedAccount}
          fromDate={fromDate}
          onClose={() => {
            setShowModal(false);
            setSelectedOrder(null);
          }}
          onSuccess={() => {
            setShowModal(false);
            setSelectedOrder(null);
            loadReport();
          }}
        />
      )}
    </div>
  );
}

interface OrderModalProps {
  order: ReportOrder;
  orderIndex: number;
  accountId: string;
  accountName: string;
  fromDate: string;
  onClose: () => void;
  onSuccess: () => void;
}

function OrderModal({
  order,
  orderIndex,
  accountId,
  accountName,
  fromDate,
  onClose,
  onSuccess,
}: OrderModalProps) {
  const [positionType, setPositionType] = useState<'open' | 'update'>('open');
  const [updateKeepsOpen, setUpdateKeepsOpen] = useState(true);
  const [stop, setStop] = useState<string>('');
  const [objective, setObjective] = useState<string>('');
  const [strategy, setStrategy] = useState<string>('');
  const [signal, setSignal] = useState<string>('');
  const [comment, setComment] = useState<string>('');
  const [lineNumber, setLineNumber] = useState<string>('');
  const [stopped, setStopped] = useState(false);
  const [beStopped, setBeStopped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<EnumOption[]>([]);
  const [signals, setSignals] = useState<EnumOption[]>([]);

  useEffect(() => {
    loadEnums();
  }, []);

  const loadEnums = async () => {
    try {
      const config = await reportConfigService.getConfig();
      setStrategies([{ value: '', label: 'Select strategy...' }, ...config.strategies]);
      setSignals([{ value: '', label: 'Select signal...' }, ...config.signals]);
    } catch (err) {
      console.error('Failed to load config:', err);
    }
  };

  const calculateRiskReward = () => {
    const stopNum = parseFloat(stop);
    const objectiveNum = parseFloat(objective);
    const price = order.price_eur || order.price;

    if (!stopNum || !objectiveNum || stopNum >= price || objectiveNum <= price) {
      return null;
    }

    const risk = price - stopNum;
    const reward = objectiveNum - price;
    const ratio = reward / risk;

    return {
      ratio: ratio.toFixed(2),
      isValid: ratio >= 1.1,
    };
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      // Convert enum keys to labels (display values)
      const strategyLabel = strategy ? strategies.find(s => s.value === strategy)?.label : undefined;
      const signalLabel = signal ? signals.find(s => s.value === signal)?.label : undefined;

      if (positionType === 'open') {
        await reportService.createGSheetOrder({
          account_id: accountName,
          from_date: fromDate,
          order_index: orderIndex,
          stop: stop ? parseFloat(stop) : undefined,
          objective: objective ? parseFloat(objective) : undefined,
          strategy: strategyLabel,
          signal: signalLabel,
          comment: comment || undefined,
        });
      } else {
        // Update mode
        if (!lineNumber) {
          setError('Please enter the Google Sheet line number');
          return;
        }

        if (updateKeepsOpen) {
          // Update an open position (adjust stop/objective)
          await reportService.updateGSheetOrder({
            account_id: accountName,
            from_date: fromDate,
            order_index: orderIndex,
            line_number: parseInt(lineNumber),
            stopped: false,
            be_stopped: false,
            stop: stop ? parseFloat(stop) : undefined,
            objective: objective ? parseFloat(objective) : undefined,
            strategy: strategyLabel,
            signal: signalLabel,
            comment: comment || undefined,
          });
        } else {
          // Close the position
          await reportService.updateGSheetOrder({
            account_id: accountName,
            from_date: fromDate,
            order_index: orderIndex,
            line_number: parseInt(lineNumber),
            stopped,
            be_stopped: beStopped,
          });
        }
      }
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save to Google Sheets');
      console.error('Save error:', err);
    } finally {
      setLoading(false);
    }
  };

  const riskReward = calculateRiskReward();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Manage Order - {order.code}</h3>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="order-info">
            <div className="info-row">
              <span>Date:</span> <strong>{new Date(order.date).toLocaleDateString()}</strong>
            </div>
            <div className="info-row">
              <span>Direction:</span> <strong>{order.direction}</strong>
            </div>
            <div className="info-row">
              <span>Quantity:</span> <strong>{order.quantity}</strong>
            </div>
            <div className="info-row">
              <span>Entry Price:</span>{' '}
              <strong>
                {order.currency} {order.price.toFixed(4)}
                {order.price_eur && ` (€ ${order.price_eur.toFixed(4)})`}
              </strong>
            </div>
            <div className="info-row">
              <span>Total:</span>{' '}
              <strong>
                {order.currency} {order.total.toFixed(2)}
              </strong>
            </div>
          </div>

          <div className="position-type-selector">
            <label>
              <input
                type="radio"
                value="open"
                checked={positionType === 'open'}
                onChange={() => setPositionType('open')}
              />
              This opens a NEW position
            </label>
            <label>
              <input
                type="radio"
                value="update"
                checked={positionType === 'update'}
                onChange={() => setPositionType('update')}
              />
              This updates an EXISTING position
            </label>
          </div>

          {positionType === 'open' ? (
            <div className="form-section">
              <h4>Opening Position</h4>
              <div className="form-group">
                <label>Stop Loss (€):</label>
                <input
                  type="number"
                  step="0.01"
                  value={stop}
                  onChange={(e) => setStop(e.target.value)}
                  placeholder="Enter stop loss price"
                />
              </div>
              <div className="form-group">
                <label>Target (€):</label>
                <input
                  type="number"
                  step="0.01"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  placeholder="Enter target price"
                />
              </div>
              {riskReward && (
                <div className={`risk-reward ${riskReward.isValid ? 'valid' : 'invalid'}`}>
                  Risk/Reward Ratio: {riskReward.ratio}:1{' '}
                  {riskReward.isValid ? '✅' : '⚠️'}
                </div>
              )}
              <div className="form-group">
                <label>Strategy:</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                >
                  {strategies.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Signal:</label>
                <select
                  value={signal}
                  onChange={(e) => setSignal(e.target.value)}
                >
                  {signals.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Comment:</label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Additional notes"
                  rows={3}
                />
              </div>
            </div>
          ) : (
            <div className="form-section">
              <h4>Update Existing Position</h4>
              <div className="form-group">
                <label>Google Sheet Line #:</label>
                <input
                  type="number"
                  value={lineNumber}
                  onChange={(e) => setLineNumber(e.target.value)}
                  placeholder="Enter row number to update"
                />
              </div>

              <div className="position-type-selector">
                <label>
                  <input
                    type="radio"
                    checked={updateKeepsOpen}
                    onChange={() => setUpdateKeepsOpen(true)}
                  />
                  Keep position OPEN (adjust stop/objective)
                </label>
                <label>
                  <input
                    type="radio"
                    checked={!updateKeepsOpen}
                    onChange={() => setUpdateKeepsOpen(false)}
                  />
                  CLOSE the position
                </label>
              </div>

              {updateKeepsOpen ? (
                <>
                  <div className="form-group">
                    <label>Stop Loss (€):</label>
                    <input
                      type="number"
                      step="0.01"
                      value={stop}
                      onChange={(e) => setStop(e.target.value)}
                      placeholder="New stop loss price"
                    />
                  </div>
                  <div className="form-group">
                    <label>Target (€):</label>
                    <input
                      type="number"
                      step="0.01"
                      value={objective}
                      onChange={(e) => setObjective(e.target.value)}
                      placeholder="New target price"
                    />
                  </div>
                  {riskReward && (
                    <div className={`risk-reward ${riskReward.isValid ? 'valid' : 'invalid'}`}>
                      Risk/Reward Ratio: {riskReward.ratio}:1{' '}
                      {riskReward.isValid ? '✅' : '⚠️'}
                    </div>
                  )}
                  <div className="form-group">
                    <label>Strategy:</label>
                    <select
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                    >
                      {strategies.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Signal:</label>
                    <select
                      value={signal}
                      onChange={(e) => setSignal(e.target.value)}
                    >
                      {signals.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Comment:</label>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Additional notes"
                      rows={3}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={stopped}
                        onChange={(e) => setStopped(e.target.checked)}
                      />
                      Stopped out
                    </label>
                  </div>
                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={beStopped}
                        onChange={(e) => setBeStopped(e.target.checked)}
                      />
                      Break-even stopped
                    </label>
                  </div>
                </>
              )}
            </div>
          )}

          {error && <div className="modal-error">{error}</div>}
        </div>

        <div className="modal-footer">
          <button className="cancel-button" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            className="save-button"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save to Google Sheet'}
          </button>
        </div>
      </div>
    </div>
  );
}
