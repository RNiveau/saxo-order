import { useState, useEffect } from 'react';
import type { WorkflowDetail, WorkflowCreateRequest } from '../services/api';
import { workflowService } from '../services/api';
import './WorkflowCreateModal.css';

interface WorkflowCreateModalProps {
  onClose: () => void;
  onSuccess: (workflow: WorkflowDetail) => void;
  prefill?: { index: string; cfd: string };
}

const INDICATOR_OPTIONS = [
  { value: 'bbb', label: 'BBB' },
  { value: 'bbh', label: 'BBH' },
  { value: 'ma50', label: 'MA50' },
  { value: 'combo', label: 'COMBO' },
  { value: 'polarite', label: 'POL (Polarité)' },
  { value: 'zone', label: 'ZONE' },
];

const UT_OPTIONS = [
  { value: '15m', label: '15m' },
  { value: 'h1', label: 'H1' },
  { value: 'h4', label: 'H4' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

const DIRECTION_OPTIONS = [
  { value: 'above', label: 'Above' },
  { value: 'below', label: 'Below' },
];

const LOCATION_OPTIONS = [
  { value: 'higher', label: 'Higher' },
  { value: 'lower', label: 'Lower' },
];

const ORDER_DIRECTION_OPTIONS = [
  { value: 'buy', label: 'Buy' },
  { value: 'sell', label: 'Sell' },
];

const ELEMENT_OPTIONS = [
  { value: '', label: 'None' },
  { value: 'close', label: 'Close' },
  { value: 'high', label: 'High' },
  { value: 'low', label: 'Low' },
];

export function WorkflowCreateModal({ onClose, onSuccess, prefill }: WorkflowCreateModalProps) {
  const [name, setName] = useState('');
  const [nameDirty, setNameDirty] = useState(false);
  const [index, setIndex] = useState(prefill?.index ?? '');
  const [cfd, setCfd] = useState(prefill?.cfd ?? '');
  const [enable, setEnable] = useState(true);
  const [dryRun, setDryRun] = useState(true);
  const [isUs, setIsUs] = useState(false);
  const [endDate, setEndDate] = useState('');
  const [indicatorName, setIndicatorName] = useState('bbb');
  const [indicatorUt, setIndicatorUt] = useState('h1');
  const [indicatorValue, setIndicatorValue] = useState('');
  const [indicatorZoneValue, setIndicatorZoneValue] = useState('');
  const [closeDirection, setCloseDirection] = useState('above');
  const [closeUt, setCloseUt] = useState('h1');
  const [spread, setSpread] = useState('');
  const [element, setElement] = useState('');
  const [triggerUt, setTriggerUt] = useState('h1');
  const [triggerLocation, setTriggerLocation] = useState('higher');
  const [orderDirection, setOrderDirection] = useState('buy');
  const [quantity, setQuantity] = useState('');

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);

  const suggestedName = `${orderDirection.toUpperCase()} ${indicatorName.toUpperCase()} ${indicatorUt.toUpperCase()}${cfd ? ' ' + cfd : ''}`;

  useEffect(() => {
    if (!nameDirty) {
      setName(suggestedName);
    }
  }, [suggestedName, nameDirty]);

  const handleNameChange = (v: string) => {
    setName(v);
    setNameDirty(true);
  };

  const needsValue = indicatorName === 'polarite' || indicatorName === 'zone';
  const needsZoneValue = indicatorName === 'zone';

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!name.trim()) errs.name = 'Name is required';
    if (!index.trim()) errs.index = 'Index is required';
    if (!cfd.trim()) errs.cfd = 'CFD is required';
    if (!spread || parseFloat(spread) <= 0) errs.spread = 'Spread must be greater than 0';
    if (!quantity || parseFloat(quantity) <= 0) errs.quantity = 'Quantity must be greater than 0';

    if (needsValue && !indicatorValue) errs.indicatorValue = 'Value is required for this indicator';
    if (needsZoneValue && !indicatorZoneValue) errs.indicatorZoneValue = 'Zone value is required';

    if (endDate) {
      const d = new Date(endDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (isNaN(d.getTime())) {
        errs.endDate = 'Invalid date';
      } else if (d < today) {
        errs.endDate = 'End date must be a future date';
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSaving(true);
    setSaveError('');

    const payload: WorkflowCreateRequest = {
      name: name.trim(),
      index: index.trim(),
      cfd: cfd.trim(),
      enable,
      dry_run: dryRun,
      is_us: isUs,
      end_date: endDate || null,
      conditions: [
        {
          indicator: {
            name: indicatorName,
            ut: indicatorUt,
            value: needsValue && indicatorValue ? parseFloat(indicatorValue) : null,
            zone_value: needsZoneValue && indicatorZoneValue ? parseFloat(indicatorZoneValue) : null,
          },
          close: {
            direction: closeDirection,
            ut: closeUt,
            spread: parseFloat(spread),
          },
          element: element || null,
        },
      ],
      trigger: {
        ut: triggerUt,
        location: triggerLocation,
        order_direction: orderDirection,
        quantity: parseFloat(quantity),
      },
    };

    try {
      const result = await workflowService.createWorkflow(payload);
      onSuccess(result);
      onClose();
    } catch (err) {
      console.error('Error creating workflow:', err);
      setSaveError('Failed to create workflow. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>New Workflow</h2>
          <button className="modal-close-button" onClick={onClose}>✕</button>
        </div>
        <form className="create-workflow-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
            />
            {errors.name && <span className="form-error">{errors.name}</span>}
          </div>

          <div className="form-row">
            <label>Index</label>
            <input
              type="text"
              value={index}
              onChange={(e) => setIndex(e.target.value)}
              placeholder="e.g. DAX.I"
            />
            {errors.index && <span className="form-error">{errors.index}</span>}
          </div>

          <div className="form-row">
            <label>CFD</label>
            <input
              type="text"
              value={cfd}
              onChange={(e) => setCfd(e.target.value)}
              placeholder="e.g. GER40.I"
            />
            {errors.cfd && <span className="form-error">{errors.cfd}</span>}
          </div>

          <div className="form-toggles">
            <label>
              <input type="checkbox" checked={enable} onChange={(e) => setEnable(e.target.checked)} />
              Enabled
            </label>
            <label>
              <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
              Dry Run
            </label>
            <label>
              <input type="checkbox" checked={isUs} onChange={(e) => setIsUs(e.target.checked)} />
              US Market
            </label>
          </div>

          <div className="form-row">
            <label>End Date (optional)</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
            {errors.endDate && <span className="form-error">{errors.endDate}</span>}
          </div>

          <div className="form-section-title">Indicator</div>

          <div className="form-row">
            <label>Indicator Type</label>
            <select value={indicatorName} onChange={(e) => setIndicatorName(e.target.value)}>
              {INDICATOR_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Indicator Timeframe</label>
            <select value={indicatorUt} onChange={(e) => setIndicatorUt(e.target.value)}>
              {UT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {needsValue && (
            <div className="form-row">
              <label>Value {needsZoneValue ? '(lower bound)' : ''}</label>
              <input
                type="number"
                value={indicatorValue}
                onChange={(e) => setIndicatorValue(e.target.value)}
                step="any"
              />
              {errors.indicatorValue && <span className="form-error">{errors.indicatorValue}</span>}
            </div>
          )}

          {needsZoneValue && (
            <div className="form-row">
              <label>Zone Value (upper bound)</label>
              <input
                type="number"
                value={indicatorZoneValue}
                onChange={(e) => setIndicatorZoneValue(e.target.value)}
                step="any"
              />
              {errors.indicatorZoneValue && <span className="form-error">{errors.indicatorZoneValue}</span>}
            </div>
          )}

          <div className="form-section-title">Close Condition</div>

          <div className="form-row">
            <label>Direction</label>
            <select value={closeDirection} onChange={(e) => setCloseDirection(e.target.value)}>
              {DIRECTION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Close Timeframe</label>
            <select value={closeUt} onChange={(e) => setCloseUt(e.target.value)}>
              {UT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Spread</label>
            <input
              type="number"
              value={spread}
              onChange={(e) => setSpread(e.target.value)}
              step="any"
              min="0"
            />
            {errors.spread && <span className="form-error">{errors.spread}</span>}
          </div>

          <div className="form-row">
            <label>Element (optional)</label>
            <select value={element} onChange={(e) => setElement(e.target.value)}>
              {ELEMENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-section-title">Trigger</div>

          <div className="form-row">
            <label>Trigger Timeframe</label>
            <select value={triggerUt} onChange={(e) => setTriggerUt(e.target.value)}>
              {UT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Order Location</label>
            <select value={triggerLocation} onChange={(e) => setTriggerLocation(e.target.value)}>
              {LOCATION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Order Direction</label>
            <select value={orderDirection} onChange={(e) => setOrderDirection(e.target.value)}>
              {ORDER_DIRECTION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Quantity</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              step="any"
              min="0"
            />
            {errors.quantity && <span className="form-error">{errors.quantity}</span>}
          </div>

          {saveError && <div className="save-error-banner">{saveError}</div>}

          <div className="form-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-save" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
