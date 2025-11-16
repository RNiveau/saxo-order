import { useState, useEffect } from 'react';
import {
  orderService,
  fundService,
  reportConfigService,
  type OrderRequest,
  type OcoOrderRequest,
  type StopLimitOrderRequest,
  type AccountInfo,
  type EnumOption,
} from '../services/api';
import './Orders.css';

type OrderType = 'regular' | 'oco' | 'stop-limit';

export function Orders() {
  const [orderType, setOrderType] = useState<OrderType>('regular');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [strategies, setStrategies] = useState<EnumOption[]>([]);
  const [signals, setSignals] = useState<EnumOption[]>([]);

  const [regularForm, setRegularForm] = useState<OrderRequest>({
    code: '',
    price: 0,
    quantity: 0,
    order_type: 'limit',
    direction: 'Buy',
    country_code: 'xpar',
    stop: undefined,
    objective: undefined,
    strategy: undefined,
    signal: undefined,
    comment: undefined,
    account_key: '',
  });

  useEffect(() => {
    loadAccounts();
    loadConfig();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoadingAccounts(true);
      const data = await fundService.getAccounts();
      setAccounts(data.accounts);

      if (data.accounts.length > 0) {
        const defaultAccountKey = data.accounts[0].account_key;
        setRegularForm(prev => ({ ...prev, account_key: defaultAccountKey }));
        setOcoForm(prev => ({ ...prev, account_key: defaultAccountKey }));
        setStopLimitForm(prev => ({ ...prev, account_key: defaultAccountKey }));
      }
    } catch (err) {
      console.error('Failed to load accounts:', err);
      setError('Failed to load accounts. Please refresh the page.');
    } finally {
      setLoadingAccounts(false);
    }
  };

  const loadConfig = async () => {
    try {
      const config = await reportConfigService.getConfig();
      setStrategies(config.strategies);
      setSignals(config.signals);
    } catch (err) {
      console.error('Failed to load config:', err);
    }
  };

  const [ocoForm, setOcoForm] = useState<OcoOrderRequest>({
    code: '',
    quantity: 0,
    limit_price: 0,
    limit_direction: 'Sell',
    stop_price: 0,
    stop_direction: 'Sell',
    country_code: 'xpar',
    stop: undefined,
    objective: undefined,
    strategy: undefined,
    signal: undefined,
    comment: undefined,
    account_key: '',
  });

  const [stopLimitForm, setStopLimitForm] = useState<StopLimitOrderRequest>({
    code: '',
    quantity: 0,
    limit_price: 0,
    stop_price: 0,
    country_code: 'xpar',
    stop: undefined,
    objective: undefined,
    strategy: undefined,
    signal: undefined,
    comment: undefined,
    account_key: '',
  });

  const handleRegularSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await orderService.createOrder(regularForm);
      setSuccess(response.message);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
        const detail = axiosError.response?.data?.detail;
        if (Array.isArray(detail)) {
          setError(detail.map(e => e.msg).join(', '));
        } else {
          setError(detail || 'Failed to create order');
        }
      } else {
        setError('Failed to create order');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOcoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await orderService.createOcoOrder(ocoForm);
      setSuccess(response.message);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
        const detail = axiosError.response?.data?.detail;
        if (Array.isArray(detail)) {
          setError(detail.map(e => e.msg).join(', '));
        } else {
          setError(detail || 'Failed to create OCO order');
        }
      } else {
        setError('Failed to create OCO order');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStopLimitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await orderService.createStopLimitOrder(stopLimitForm);
      setSuccess(response.message);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
        const detail = axiosError.response?.data?.detail;
        if (Array.isArray(detail)) {
          setError(detail.map(e => e.msg).join(', '));
        } else {
          setError(detail || 'Failed to create stop-limit order');
        }
      } else {
        setError('Failed to create stop-limit order');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="orders-container">
      <h1>Create Order</h1>

      <div className="order-tabs">
        <button
          className={`tab ${orderType === 'regular' ? 'active' : ''}`}
          onClick={() => setOrderType('regular')}
        >
          Regular Order
        </button>
        <button
          className={`tab ${orderType === 'oco' ? 'active' : ''}`}
          onClick={() => setOrderType('oco')}
        >
          OCO Order
        </button>
        <button
          className={`tab ${orderType === 'stop-limit' ? 'active' : ''}`}
          onClick={() => setOrderType('stop-limit')}
        >
          Stop-Limit Order
        </button>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {loadingAccounts && (
        <div className="loading-accounts">Loading accounts...</div>
      )}

      {!loadingAccounts && accounts.length === 0 && (
        <div className="alert alert-error">
          No accounts available. Please check your configuration.
        </div>
      )}

      {!loadingAccounts && accounts.length > 0 && orderType === 'regular' && (
        <form onSubmit={handleRegularSubmit} className="order-form">
          <div className="form-section">
            <h2>Order Details</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="code">Asset Code *</label>
                <input
                  type="text"
                  id="code"
                  value={regularForm.code}
                  onChange={(e) =>
                    setRegularForm({ ...regularForm, code: e.target.value })
                  }
                  required
                  placeholder="e.g., AAPL, BNP"
                />
              </div>
              <div className="form-group">
                <label htmlFor="country_code">Market Code</label>
                <input
                  type="text"
                  id="country_code"
                  value={regularForm.country_code}
                  onChange={(e) =>
                    setRegularForm({ ...regularForm, country_code: e.target.value })
                  }
                  placeholder="xpar, xnas, etc."
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="order_type">Order Type *</label>
                <select
                  id="order_type"
                  value={regularForm.order_type}
                  onChange={(e) =>
                    setRegularForm({ ...regularForm, order_type: e.target.value })
                  }
                  required
                >
                  <option value="limit">Limit</option>
                  <option value="market">Market</option>
                  <option value="stop">Stop</option>
                  <option value="open_stop">Open Stop</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="direction">Direction *</label>
                <select
                  id="direction"
                  value={regularForm.direction}
                  onChange={(e) =>
                    setRegularForm({ ...regularForm, direction: e.target.value })
                  }
                  required
                >
                  <option value="Buy">Buy</option>
                  <option value="Sell">Sell</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="price">Price *</label>
                <input
                  type="number"
                  id="price"
                  step="0.01"
                  value={regularForm.price}
                  onChange={(e) =>
                    setRegularForm({
                      ...regularForm,
                      price: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="quantity">Quantity *</label>
                <input
                  type="number"
                  id="quantity"
                  step="1"
                  value={regularForm.quantity}
                  onChange={(e) =>
                    setRegularForm({
                      ...regularForm,
                      quantity: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Risk Management (Optional)</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="stop">Stop Loss</label>
                <input
                  type="number"
                  id="stop"
                  step="0.01"
                  value={regularForm.stop || ''}
                  onChange={(e) =>
                    setRegularForm({
                      ...regularForm,
                      stop: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                />
              </div>
              <div className="form-group">
                <label htmlFor="objective">Objective</label>
                <input
                  type="number"
                  id="objective"
                  step="0.01"
                  value={regularForm.objective || ''}
                  onChange={(e) =>
                    setRegularForm({
                      ...regularForm,
                      objective: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Additional Information (Optional)</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="strategy">Strategy</label>
                <select
                  id="strategy"
                  value={regularForm.strategy || ''}
                  onChange={(e) =>
                    setRegularForm({
                      ...regularForm,
                      strategy: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">-- Select Strategy --</option>
                  {strategies.map((strategy) => (
                    <option key={strategy.value} value={strategy.label}>
                      {strategy.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="signal">Signal</label>
                <select
                  id="signal"
                  value={regularForm.signal || ''}
                  onChange={(e) =>
                    setRegularForm({
                      ...regularForm,
                      signal: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">-- Select Signal --</option>
                  {signals.map((signal) => (
                    <option key={signal.value} value={signal.label}>
                      {signal.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="comment">Comment</label>
              <textarea
                id="comment"
                value={regularForm.comment || ''}
                onChange={(e) =>
                  setRegularForm({
                    ...regularForm,
                    comment: e.target.value || undefined,
                  })
                }
                rows={3}
              />
            </div>

            <div className="form-group">
              <label htmlFor="account_key">Account *</label>
              <select
                id="account_key"
                value={regularForm.account_key}
                onChange={(e) =>
                  setRegularForm({
                    ...regularForm,
                    account_key: e.target.value,
                  })
                }
                required
              >
                {accounts.map((account) => (
                  <option key={account.account_id} value={account.account_key}>
                    {account.account_name} ({account.account_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Creating Order...' : 'Create Order'}
          </button>
        </form>
      )}

      {!loadingAccounts && accounts.length > 0 && orderType === 'oco' && (
        <form onSubmit={handleOcoSubmit} className="order-form">
          <div className="form-section">
            <h2>OCO Order Details</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="oco_code">Asset Code *</label>
                <input
                  type="text"
                  id="oco_code"
                  value={ocoForm.code}
                  onChange={(e) => setOcoForm({ ...ocoForm, code: e.target.value })}
                  required
                  placeholder="e.g., AAPL, BNP"
                />
              </div>
              <div className="form-group">
                <label htmlFor="oco_country_code">Market Code</label>
                <input
                  type="text"
                  id="oco_country_code"
                  value={ocoForm.country_code}
                  onChange={(e) =>
                    setOcoForm({ ...ocoForm, country_code: e.target.value })
                  }
                  placeholder="xpar, xnas, etc."
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="oco_quantity">Quantity *</label>
              <input
                type="number"
                id="oco_quantity"
                step="1"
                value={ocoForm.quantity}
                onChange={(e) =>
                  setOcoForm({
                    ...ocoForm,
                    quantity: parseFloat(e.target.value) || 0,
                  })
                }
                required
              />
            </div>
          </div>

          <div className="form-section">
            <h2>Limit Order</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="limit_price">Limit Price *</label>
                <input
                  type="number"
                  id="limit_price"
                  step="0.01"
                  value={ocoForm.limit_price}
                  onChange={(e) =>
                    setOcoForm({
                      ...ocoForm,
                      limit_price: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="limit_direction">Limit Direction *</label>
                <select
                  id="limit_direction"
                  value={ocoForm.limit_direction}
                  onChange={(e) =>
                    setOcoForm({ ...ocoForm, limit_direction: e.target.value })
                  }
                  required
                >
                  <option value="Buy">Buy</option>
                  <option value="Sell">Sell</option>
                </select>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Stop Order</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="stop_price_oco">Stop Price *</label>
                <input
                  type="number"
                  id="stop_price_oco"
                  step="0.01"
                  value={ocoForm.stop_price}
                  onChange={(e) =>
                    setOcoForm({
                      ...ocoForm,
                      stop_price: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="stop_direction_oco">Stop Direction *</label>
                <select
                  id="stop_direction_oco"
                  value={ocoForm.stop_direction}
                  onChange={(e) =>
                    setOcoForm({ ...ocoForm, stop_direction: e.target.value })
                  }
                  required
                >
                  <option value="Buy">Buy</option>
                  <option value="Sell">Sell</option>
                </select>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Risk Management (Optional)</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="oco_stop">Stop Loss</label>
                <input
                  type="number"
                  id="oco_stop"
                  step="0.01"
                  value={ocoForm.stop || ''}
                  onChange={(e) =>
                    setOcoForm({
                      ...ocoForm,
                      stop: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                />
              </div>
              <div className="form-group">
                <label htmlFor="oco_objective">Objective</label>
                <input
                  type="number"
                  id="oco_objective"
                  step="0.01"
                  value={ocoForm.objective || ''}
                  onChange={(e) =>
                    setOcoForm({
                      ...ocoForm,
                      objective: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Additional Information (Optional)</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="oco_strategy">Strategy</label>
                <select
                  id="oco_strategy"
                  value={ocoForm.strategy || ''}
                  onChange={(e) =>
                    setOcoForm({
                      ...ocoForm,
                      strategy: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">-- Select Strategy --</option>
                  {strategies.map((strategy) => (
                    <option key={strategy.value} value={strategy.label}>
                      {strategy.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="oco_signal">Signal</label>
                <select
                  id="oco_signal"
                  value={ocoForm.signal || ''}
                  onChange={(e) =>
                    setOcoForm({
                      ...ocoForm,
                      signal: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">-- Select Signal --</option>
                  {signals.map((signal) => (
                    <option key={signal.value} value={signal.label}>
                      {signal.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="oco_comment">Comment</label>
              <textarea
                id="oco_comment"
                value={ocoForm.comment || ''}
                onChange={(e) =>
                  setOcoForm({
                    ...ocoForm,
                    comment: e.target.value || undefined,
                  })
                }
                rows={3}
              />
            </div>

            <div className="form-group">
              <label htmlFor="oco_account_key">Account *</label>
              <select
                id="oco_account_key"
                value={ocoForm.account_key}
                onChange={(e) =>
                  setOcoForm({
                    ...ocoForm,
                    account_key: e.target.value,
                  })
                }
                required
              >
                {accounts.map((account) => (
                  <option key={account.account_id} value={account.account_key}>
                    {account.account_name} ({account.account_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Creating OCO Order...' : 'Create OCO Order'}
          </button>
        </form>
      )}

      {!loadingAccounts && accounts.length > 0 && orderType === 'stop-limit' && (
        <form onSubmit={handleStopLimitSubmit} className="order-form">
          <div className="form-section">
            <h2>Stop-Limit Order Details</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="sl_code">Asset Code *</label>
                <input
                  type="text"
                  id="sl_code"
                  value={stopLimitForm.code}
                  onChange={(e) =>
                    setStopLimitForm({ ...stopLimitForm, code: e.target.value })
                  }
                  required
                  placeholder="e.g., AAPL, BNP"
                />
              </div>
              <div className="form-group">
                <label htmlFor="sl_country_code">Market Code</label>
                <input
                  type="text"
                  id="sl_country_code"
                  value={stopLimitForm.country_code}
                  onChange={(e) =>
                    setStopLimitForm({ ...stopLimitForm, country_code: e.target.value })
                  }
                  placeholder="xpar, xnas, etc."
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="sl_quantity">Quantity *</label>
                <input
                  type="number"
                  id="sl_quantity"
                  step="1"
                  value={stopLimitForm.quantity}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      quantity: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="sl_limit_price">Limit Price *</label>
                <input
                  type="number"
                  id="sl_limit_price"
                  step="0.01"
                  value={stopLimitForm.limit_price}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      limit_price: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="sl_stop_price">Stop Trigger Price *</label>
                <input
                  type="number"
                  id="sl_stop_price"
                  step="0.01"
                  value={stopLimitForm.stop_price}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      stop_price: parseFloat(e.target.value) || 0,
                    })
                  }
                  required
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Risk Management (Optional)</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="sl_stop">Stop Loss</label>
                <input
                  type="number"
                  id="sl_stop"
                  step="0.01"
                  value={stopLimitForm.stop || ''}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      stop: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                />
              </div>
              <div className="form-group">
                <label htmlFor="sl_objective">Objective</label>
                <input
                  type="number"
                  id="sl_objective"
                  step="0.01"
                  value={stopLimitForm.objective || ''}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      objective: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Additional Information (Optional)</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="sl_strategy">Strategy</label>
                <select
                  id="sl_strategy"
                  value={stopLimitForm.strategy || ''}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      strategy: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">-- Select Strategy --</option>
                  {strategies.map((strategy) => (
                    <option key={strategy.value} value={strategy.label}>
                      {strategy.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="sl_signal">Signal</label>
                <select
                  id="sl_signal"
                  value={stopLimitForm.signal || ''}
                  onChange={(e) =>
                    setStopLimitForm({
                      ...stopLimitForm,
                      signal: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">-- Select Signal --</option>
                  {signals.map((signal) => (
                    <option key={signal.value} value={signal.label}>
                      {signal.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="sl_comment">Comment</label>
              <textarea
                id="sl_comment"
                value={stopLimitForm.comment || ''}
                onChange={(e) =>
                  setStopLimitForm({
                    ...stopLimitForm,
                    comment: e.target.value || undefined,
                  })
                }
                rows={3}
              />
            </div>

            <div className="form-group">
              <label htmlFor="sl_account_key">Account *</label>
              <select
                id="sl_account_key"
                value={stopLimitForm.account_key}
                onChange={(e) =>
                  setStopLimitForm({
                    ...stopLimitForm,
                    account_key: e.target.value,
                  })
                }
                required
              >
                {accounts.map((account) => (
                  <option key={account.account_id} value={account.account_key}>
                    {account.account_name} ({account.account_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Creating Stop-Limit Order...' : 'Create Stop-Limit Order'}
          </button>
        </form>
      )}
    </div>
  );
}
