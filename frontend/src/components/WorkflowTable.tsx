import { useState } from 'react';
import type { WorkflowListItem } from '../services/api';
import './WorkflowTable.css';

interface WorkflowTableProps {
  workflows: WorkflowListItem[];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSortChange?: (sortBy: string) => void;
  onRowClick?: (workflowId: string) => void;
}

function WorkflowTable({ workflows, sortBy, sortOrder, onSortChange, onRowClick }: WorkflowTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const totalPages = Math.ceil(workflows.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedWorkflows = workflows.slice(startIndex, endIndex);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

  const formatRelativeTime = (timestamp: number | null | undefined) => {
    if (!timestamp) return '-';

    const now = Date.now();
    const orderTime = timestamp * 1000; // Convert Unix timestamp to milliseconds
    const diffMs = now - orderTime;
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    // For older than 7 days, show the actual date
    return new Date(orderTime).toLocaleDateString();
  };

  const getSortIcon = (column: string) => {
    if (sortBy !== column) return null;
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  const handleHeaderClick = (column: string) => {
    if (onSortChange) {
      onSortChange(column);
      setCurrentPage(1); // Reset to first page when sorting changes
    }
  };

  return (
    <div className="workflow-table-container">
      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th
                className={onSortChange ? 'sortable' : ''}
                onClick={() => handleHeaderClick('name')}
              >
                Name{getSortIcon('name')}
              </th>
              <th
                className={onSortChange ? 'sortable' : ''}
                onClick={() => handleHeaderClick('index')}
              >
                Index{getSortIcon('index')}
              </th>
              <th>CFD</th>
              <th>Status</th>
              <th>Dry Run</th>
              <th>Indicator</th>
              <th>Unit Time</th>
              <th
                className={onSortChange ? 'sortable' : ''}
                onClick={() => handleHeaderClick('end_date')}
              >
                End Date{getSortIcon('end_date')}
              </th>
              <th
                className={onSortChange ? 'sortable' : ''}
                onClick={() => handleHeaderClick('last_order_timestamp')}
              >
                Last Order{getSortIcon('last_order_timestamp')}
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedWorkflows.map((workflow) => (
              <tr
                key={workflow.id}
                onClick={() => onRowClick?.(workflow.id)}
                className={onRowClick ? 'clickable-row' : ''}
              >
                <td className="workflow-name">{workflow.name}</td>
                <td>{workflow.index}</td>
                <td>{workflow.cfd}</td>
                <td>
                  {workflow.enable ? (
                    <span className="status-badge status-enabled">
                      ✓ Enabled
                    </span>
                  ) : (
                    <span className="status-badge status-disabled">
                      ✗ Disabled
                    </span>
                  )}
                </td>
                <td>
                  {workflow.dry_run && (
                    <span className="dry-run-badge">DRY RUN</span>
                  )}
                </td>
                <td>
                  {workflow.primary_indicator ? (
                    <span className="indicator-badge">
                      {workflow.primary_indicator.toUpperCase()}
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
                <td>
                  {workflow.primary_unit_time
                    ? workflow.primary_unit_time.toUpperCase()
                    : '-'}
                </td>
                <td>{formatDate(workflow.end_date)}</td>
                <td className="last-order-cell">
                  {formatRelativeTime(workflow.last_order_timestamp)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination-controls">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="pagination-button"
          >
            ← Previous
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="pagination-button"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

export default WorkflowTable;
