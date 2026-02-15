import { useEffect, useState } from 'react';
import { WorkflowDetail, workflowService } from '../services/api';
import './WorkflowDetailModal.css';

interface WorkflowDetailModalProps {
  workflowId: string;
  onClose: () => void;
}

export function WorkflowDetailModal({ workflowId, onClose }: WorkflowDetailModalProps) {
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadWorkflowDetail = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await workflowService.getWorkflowDetail(workflowId);
        setWorkflow(data);
      } catch (err) {
        console.error('Error loading workflow detail:', err);
        setError('Failed to load workflow details. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadWorkflowDetail();
  }, [workflowId]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'No end date';
    return new Date(dateString).toLocaleString();
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>Workflow Details</h2>
          <button className="modal-close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {loading && (
          <div className="modal-loading">
            <div className="spinner"></div>
            <p>Loading workflow details...</p>
          </div>
        )}

        {error && (
          <div className="modal-error">
            <p className="error-message">{error}</p>
            <button onClick={onClose} className="error-close-button">
              Close
            </button>
          </div>
        )}

        {!loading && !error && workflow && (
          <div className="modal-body">
            <section className="detail-section">
              <h3>Basic Information</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Name:</span>
                  <span className="detail-value">{workflow.name}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Index:</span>
                  <span className="detail-value">{workflow.index}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">CFD:</span>
                  <span className="detail-value">{workflow.cfd}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Status:</span>
                  <span className="detail-value">
                    {workflow.enable ? (
                      <span className="status-badge status-enabled">✓ Enabled</span>
                    ) : (
                      <span className="status-badge status-disabled">✗ Disabled</span>
                    )}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Mode:</span>
                  <span className="detail-value">
                    {workflow.dry_run ? (
                      <span className="dry-run-badge">DRY RUN</span>
                    ) : (
                      'Live'
                    )}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">US Market:</span>
                  <span className="detail-value">{workflow.is_us ? 'Yes' : 'No'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">End Date:</span>
                  <span className="detail-value">{formatDate(workflow.end_date)}</span>
                </div>
              </div>
            </section>

            <section className="detail-section">
              <h3>Conditions</h3>
              {workflow.conditions.map((condition, index) => (
                <div key={index} className="condition-card">
                  <h4>Condition {index + 1}</h4>

                  <div className="condition-subsection">
                    <h5>Indicator</h5>
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="detail-label">Name:</span>
                        <span className="detail-value">
                          <span className="indicator-badge">{condition.indicator.name.toUpperCase()}</span>
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Unit Time:</span>
                        <span className="detail-value">{condition.indicator.ut.toUpperCase()}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Value:</span>
                        <span className="detail-value">
                          {condition.indicator.value !== null ? condition.indicator.value : 'N/A'}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Zone Value:</span>
                        <span className="detail-value">
                          {condition.indicator.zone_value !== null ? condition.indicator.zone_value : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="condition-subsection">
                    <h5>Close</h5>
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="detail-label">Direction:</span>
                        <span className="detail-value">{condition.close.direction.toUpperCase()}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Unit Time:</span>
                        <span className="detail-value">{condition.close.ut.toUpperCase()}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Spread:</span>
                        <span className="detail-value">{condition.close.spread}</span>
                      </div>
                    </div>
                  </div>

                  {condition.element && (
                    <div className="detail-item">
                      <span className="detail-label">Element:</span>
                      <span className="detail-value">{condition.element}</span>
                    </div>
                  )}
                </div>
              ))}
            </section>

            <section className="detail-section">
              <h3>Trigger</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Unit Time:</span>
                  <span className="detail-value">{workflow.trigger.ut.toUpperCase()}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Signal:</span>
                  <span className="detail-value">{workflow.trigger.signal.toUpperCase()}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Location:</span>
                  <span className="detail-value">{workflow.trigger.location.toUpperCase()}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Order Direction:</span>
                  <span className="detail-value">{workflow.trigger.order_direction.toUpperCase()}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Quantity:</span>
                  <span className="detail-value">{workflow.trigger.quantity}</span>
                </div>
              </div>
            </section>

            <section className="detail-section metadata-section">
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Created:</span>
                  <span className="detail-value">{formatDate(workflow.created_at)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Updated:</span>
                  <span className="detail-value">{formatDate(workflow.updated_at)}</span>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
