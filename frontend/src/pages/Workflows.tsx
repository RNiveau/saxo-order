import { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { WorkflowListItem, workflowService } from '../services/api';
import WorkflowTable from '../components/WorkflowTable';
import './Workflows.css';

function Workflows() {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  // Filter state from URL
  const filterEnabled = searchParams.get('status') || 'all';
  const filterIndex = searchParams.get('index') || '';
  const filterIndicator = searchParams.get('indicator') || '';
  const filterDryRun = searchParams.get('dry_run') || 'all';

  // Sort state from URL
  const sortBy = (searchParams.get('sort_by') || 'name') as 'name' | 'index' | 'end_date';
  const sortOrder = (searchParams.get('sort_order') || 'asc') as 'asc' | 'desc';

  const loadWorkflows = async () => {
    try {
      setError(null);
      const response = await workflowService.listWorkflows({
        page: 1,
        per_page: 1000,
      });
      setWorkflows(response.workflows);
    } catch (err) {
      console.error('Error loading workflows:', err);
      setError('Failed to load workflows. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflows();

    let intervalId: NodeJS.Timeout | null = null;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        loadWorkflows();
        if (!intervalId) {
          intervalId = setInterval(loadWorkflows, 60000);
        }
      } else {
        if (intervalId) {
          clearInterval(intervalId);
          intervalId = null;
        }
      }
    };

    handleVisibilityChange();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (intervalId) clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // Client-side filtering
  const filteredWorkflows = useMemo(() => {
    return workflows.filter((workflow) => {
      // Filter by enabled status
      if (filterEnabled === 'enabled' && !workflow.enable) return false;
      if (filterEnabled === 'disabled' && workflow.enable) return false;

      // Filter by index
      if (filterIndex && !workflow.index.toLowerCase().includes(filterIndex.toLowerCase())) {
        return false;
      }

      // Filter by indicator type
      if (filterIndicator && workflow.primary_indicator !== filterIndicator) {
        return false;
      }

      // Filter by dry run
      if (filterDryRun === 'dry_run' && !workflow.dry_run) return false;
      if (filterDryRun === 'live' && workflow.dry_run) return false;

      return true;
    });
  }, [workflows, filterEnabled, filterIndex, filterIndicator, filterDryRun]);

  // Client-side sorting
  const sortedWorkflows = useMemo(() => {
    const sorted = [...filteredWorkflows];
    sorted.sort((a, b) => {
      let aVal: string | null = '';
      let bVal: string | null = '';

      if (sortBy === 'name') {
        aVal = a.name;
        bVal = b.name;
      } else if (sortBy === 'index') {
        aVal = a.index;
        bVal = b.index;
      } else if (sortBy === 'end_date') {
        aVal = a.end_date || '';
        bVal = b.end_date || '';
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [filteredWorkflows, sortBy, sortOrder]);

  const handleFilterChange = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    // Reset to page 1 when filters change
    newParams.delete('page');
    setSearchParams(newParams);
  };

  const handleSortChange = (newSortBy: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (newSortBy === sortBy) {
      // Toggle sort order
      newParams.set('sort_order', sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      newParams.set('sort_by', newSortBy);
      newParams.set('sort_order', 'asc');
    }
    setSearchParams(newParams);
  };

  if (loading) {
    return (
      <div className="workflows-container">
        <div className="workflows-header">
          <h1>Workflows</h1>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading workflows...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="workflows-container">
        <div className="workflows-header">
          <h1>Workflows</h1>
        </div>
        <div className="error-state">
          <p className="error-message">{error}</p>
          <button onClick={loadWorkflows} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (workflows.length === 0) {
    return (
      <div className="workflows-container">
        <div className="workflows-header">
          <h1>Workflows</h1>
        </div>
        <div className="empty-state">
          <p>No workflows found</p>
          <p className="empty-hint">
            Workflows will appear here after running the migration script.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="workflows-container">
      <div className="workflows-header">
        <h1>Workflows</h1>
        <p className="workflows-count">
          {sortedWorkflows.length} of {workflows.length} workflow(s)
        </p>
      </div>

      <div className="filters-section">
        <div className="filter-group">
          <label>Status:</label>
          <select
            value={filterEnabled}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="all">All</option>
            <option value="enabled">Enabled Only</option>
            <option value="disabled">Disabled Only</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Index:</label>
          <input
            type="text"
            placeholder="Filter by index..."
            value={filterIndex}
            onChange={(e) => handleFilterChange('index', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Indicator:</label>
          <select
            value={filterIndicator}
            onChange={(e) => handleFilterChange('indicator', e.target.value)}
          >
            <option value="">All</option>
            <option value="ma50">MA50</option>
            <option value="combo">Combo</option>
            <option value="bbb">BBB</option>
            <option value="bbh">BBH</option>
            <option value="polarite">Polarite</option>
            <option value="zone">Zone</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Mode:</label>
          <select
            value={filterDryRun}
            onChange={(e) => handleFilterChange('dry_run', e.target.value)}
          >
            <option value="all">All</option>
            <option value="dry_run">Dry Run Only</option>
            <option value="live">Live Only</option>
          </select>
        </div>
      </div>

      <WorkflowTable
        workflows={sortedWorkflows}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSortChange={handleSortChange}
      />
    </div>
  );
}

export default Workflows;
