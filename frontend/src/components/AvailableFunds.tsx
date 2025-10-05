import { useEffect, useState } from 'react';
import type { AccountInfo, AvailableFundResponse } from '../services/api';
import { fundService } from '../services/api';
import './AvailableFunds.css';

export function AvailableFunds() {
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [fundData, setFundData] = useState<AvailableFundResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const response = await fundService.getAccounts();
      setAccounts(response.accounts);
      if (response.accounts.length > 0 && !selectedAccountId) {
        setSelectedAccountId(response.accounts[0].account_id);
        fetchFundData(response.accounts[0].account_id);
      }
    } catch (err) {
      setError('Failed to fetch accounts');
      console.error('Error fetching accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFundData = async (accountId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await fundService.getAvailableFund(accountId);
      setFundData(data);
    } catch (err) {
      setError('Failed to fetch fund data');
      console.error('Error fetching fund data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAccountChange = (accountId: string) => {
    setSelectedAccountId(accountId);
    fetchFundData(accountId);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  return (
    <div className="available-funds-container">
      <h2>Available Funds</h2>

      {accounts.length > 0 && (
        <div className="account-selector">
          <label htmlFor="account-select">Select Account: </label>
          <select
            id="account-select"
            value={selectedAccountId}
            onChange={(e) => handleAccountChange(e.target.value)}
          >
            {accounts.map((account) => (
              <option key={account.account_id} value={account.account_id}>
                {account.account_name} ({account.account_id})
              </option>
            ))}
          </select>
        </div>
      )}

      {loading && <div className="loading">Loading...</div>}

      {error && <div className="error">{error}</div>}

      {fundData && !loading && (
        <div className="fund-details">
          <div className="fund-card">
            <h3>{fundData.account_name}</h3>
            <div className="fund-info">
              <div className="fund-item">
                <span className="label">Account ID:</span>
                <span className="value">{fundData.account_id}</span>
              </div>
              <div className="fund-item">
                <span className="label">Total Fund:</span>
                <span className="value">{formatCurrency(fundData.total_fund)}</span>
              </div>
              <div className="fund-item">
                <span className="label">Available Fund (from Saxo):</span>
                <span className="value">{formatCurrency(fundData.available_fund)}</span>
              </div>
              <div className="fund-item">
                <span className="label">Open Buy Orders Value:</span>
                <span className="value negative">
                  -{formatCurrency(fundData.open_orders_commitment)}
                </span>
              </div>
              <div className="fund-item highlight">
                <span className="label">Actual Available Fund:</span>
                <span className="value">{formatCurrency(fundData.actual_available_fund)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}