import { useRef, useState } from 'react';
import type { TradeRepublicTransaction } from '../services/api';
import { tradeRepublicService } from '../services/api';
import './TradeRepublicReport.css';

export function TradeRepublicReport() {
  const [transactions, setTransactions] = useState<TradeRepublicTransaction[]>([]);
  const [errorCount, setErrorCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setExportError(null);
    setExportSuccess(null);

    try {
      const response = await tradeRepublicService.upload(file);
      setTransactions(response.transactions);
      setErrorCount(response.errors.length);
      setSelectedIds(new Set());
    } catch (err) {
      setError('Failed to upload or parse the CSV file');
      setTransactions([]);
      setErrorCount(0);
      setSelectedIds(new Set());
      console.error('Trade Republic upload error:', err);
    } finally {
      setLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const toggleSelected = (transactionId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(transactionId)) {
        next.delete(transactionId);
      } else {
        next.add(transactionId);
      }
      return next;
    });
  };

  const handleExport = async () => {
    const selected = transactions.filter((t) =>
      selectedIds.has(t.transaction_id)
    );
    if (selected.length === 0) return;

    setExporting(true);
    setExportError(null);
    setExportSuccess(null);

    try {
      const response = await tradeRepublicService.export(selected);
      setExportSuccess(
        `Exported ${response.exported_count} transaction${
          response.exported_count > 1 ? 's' : ''
        } to the ETF / DCA sheet.`
      );
      setSelectedIds(new Set());
    } catch (err) {
      setExportError('Failed to export the selected transactions');
      console.error('Trade Republic export error:', err);
    } finally {
      setExporting(false);
    }
  };

  const formatValue = (value: string | number | null): string => {
    return value === null || value === '' ? '–' : String(value);
  };

  return (
    <div className="trade-republic-report">
      <h1>Trade Republic Report</h1>

      <p className="info-text">
        Upload a Trade Republic CSV export to review its transactions.
      </p>

      <div className="upload-box">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          disabled={loading}
          className="upload-input"
        />
        {loading && <span className="loading">Uploading…</span>}
      </div>

      {error && <div className="error-message">{error}</div>}
      {errorCount > 0 && (
        <div className="warning-message">
          {errorCount} row{errorCount > 1 ? 's' : ''} could not be parsed.
        </div>
      )}
      {exportError && <div className="error-message">{exportError}</div>}
      {exportSuccess && (
        <div className="success-message">{exportSuccess}</div>
      )}

      {transactions.length > 0 && (
        <>
          <div className="export-box">
            <button
              className="export-button"
              onClick={handleExport}
              disabled={selectedIds.size === 0 || exporting}
            >
              {exporting
                ? 'Exporting…'
                : `Export selected (${selectedIds.size})`}
            </button>
          </div>

          <div className="table-wrapper">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Date</th>
                  <th>Category</th>
                  <th>Type</th>
                  <th>Name</th>
                  <th>Symbol</th>
                  <th>Shares</th>
                  <th>Price</th>
                  <th>Amount</th>
                  <th>Currency</th>
                  <th>Original Amount</th>
                  <th>Original Currency</th>
                  <th>Fee</th>
                  <th>Tax</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.transaction_id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(t.transaction_id)}
                        onChange={() => toggleSelected(t.transaction_id)}
                      />
                    </td>
                    <td>{formatValue(t.date)}</td>
                    <td>{formatValue(t.category)}</td>
                    <td>{formatValue(t.type)}</td>
                    <td>{formatValue(t.name)}</td>
                    <td>{formatValue(t.symbol)}</td>
                    <td>{formatValue(t.shares)}</td>
                    <td>{formatValue(t.price)}</td>
                    <td>{formatValue(t.amount)}</td>
                    <td>{formatValue(t.currency)}</td>
                    <td>{formatValue(t.original_amount)}</td>
                    <td>{formatValue(t.original_currency)}</td>
                    <td>{formatValue(t.fee)}</td>
                    <td>{formatValue(t.tax)}</td>
                    <td>{formatValue(t.description)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
