import { useEffect, useState } from 'react';
import { WorkflowListItem, workflowService } from '../services/api';
import WorkflowTable from '../components/WorkflowTable';
import './Workflows.css';

function Workflows() {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        <p className="workflows-count">{workflows.length} workflow(s)</p>
      </div>
      <WorkflowTable workflows={workflows} />
    </div>
  );
}

export default Workflows;
