import React from 'react';
import type { WorkflowConditionInfo, WorkflowInfo } from '../services/api';
import { isWorkflowExpired } from '../utils/workflowExpiry';
import './WorkflowCard.css';

interface WorkflowCardProps {
  workflow: WorkflowInfo;
}

const isPresent = (value: number | null | undefined): value is number =>
  value !== undefined && value !== null;

const renderStatus = (workflow: WorkflowInfo) => {
  if (!workflow.enabled) {
    return <span className="wf-status wf-status-disabled">Disabled</span>;
  }
  if (isWorkflowExpired(workflow.end_date)) {
    return <span className="wf-status wf-status-expired">Expired</span>;
  }
  if (workflow.dry_run) {
    return <span className="wf-status wf-status-dry-run">Dry run</span>;
  }
  return <span className="wf-status wf-status-enabled">Enabled</span>;
};

const ConditionLine: React.FC<{ condition: WorkflowConditionInfo }> = ({ condition }) => {
  const { indicator, close, element } = condition;
  return (
    <div className="wf-line">
      <div className="wf-sentence">
        <span className="wf-term">{indicator.name}</span>
        {isPresent(indicator.value) && <span className="wf-num">{indicator.value}</span>}
        {isPresent(indicator.zone_value) && (
          <span className="wf-muted">
            → <span className="wf-num">{indicator.zone_value}</span>
          </span>
        )}
        <span className={`wf-direction wf-direction-${close.direction}`}>{close.direction}</span>
        <span className="wf-term">close</span>
        {isPresent(close.value) && <span className="wf-num">{close.value}</span>}
        {close.unit_time !== indicator.unit_time && (
          <span className="wf-ut">{close.unit_time}</span>
        )}
        {element && <span className="wf-chip">{element}</span>}
      </div>
      <div className="wf-sub">
        <span className="wf-ut">{indicator.unit_time}</span>
        {isPresent(indicator.current_value) && (
          <span className="wf-muted">
            today <span className="wf-num">{indicator.current_value.toFixed(2)}</span>
          </span>
        )}
      </div>
    </div>
  );
};

export const WorkflowCard: React.FC<WorkflowCardProps> = ({ workflow }) => {
  const { trigger } = workflow;
  const expired = isWorkflowExpired(workflow.end_date);
  const inactive = !workflow.enabled || expired;

  return (
    <div className={`wf-card${inactive ? ' wf-card-inactive' : ''}`}>
      <div className="wf-card-header">
        <div className="wf-title">
          <span className={`wf-side wf-side-${trigger.order_direction}`}>
            {trigger.order_direction.toUpperCase()}
          </span>
          <h4>{workflow.name}</h4>
        </div>
        <div className="wf-meta">
          {workflow.index !== workflow.cfd && (
            <span className="wf-meta-item">
              Index <span className="wf-code">{workflow.index}</span>
            </span>
          )}
          <span className="wf-meta-item">
            CFD <span className="wf-code">{workflow.cfd}</span>
          </span>
          {workflow.is_us && <span className="wf-chip">US</span>}
          {workflow.end_date && (
            <span className={`wf-meta-item${expired ? ' wf-expired-date' : ''}`}>
              until {workflow.end_date}
            </span>
          )}
          {renderStatus(workflow)}
        </div>
      </div>

      <div className="wf-flow">
        <div className="wf-step">
          <div className="wf-step-label">When</div>
          {workflow.conditions.map((condition, index) => (
            <ConditionLine key={index} condition={condition} />
          ))}
        </div>

        <div className="wf-flow-arrow" aria-hidden="true">→</div>

        <div className="wf-step">
          <div className="wf-step-label">Then</div>
          <div className="wf-line">
            <div className="wf-sentence">
              <span className="wf-term">{trigger.signal}</span>
              <span className="wf-term">{trigger.location}</span>
              <span className="wf-muted">→</span>
              <span className={`wf-order wf-side-text-${trigger.order_direction}`}>
                {trigger.order_direction} {trigger.quantity}
              </span>
            </div>
            <div className="wf-sub">
              <span className="wf-ut">{trigger.unit_time}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
