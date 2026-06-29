import React, { useState, useEffect } from 'react';
import http from '../services/http';

export const WorkflowStudio: React.FC = () => {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [executions, setExecutions] = useState<any[]>([]);

  useEffect(() => {
    http.get('/api/v1/workflows')
      .then(res => setWorkflows(res.data))
      .catch(() => {});

    http.get('/api/v1/workflows/executions')
      .then(res => setExecutions(res.data))
      .catch(() => {});
  }, []);

  const triggerExecution = (id: string) => {
    http.post(`/api/v1/workflows/${id}/execute`)
      .then(() => {
        // reload
        http.get('/api/v1/workflows/executions')
          .then(res => setExecutions(res.data));
      })
      .catch(() => {});
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <h2>Workflow Studio</h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3>Definitions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '1rem' }}>
            {workflows.map(w => (
              <div key={w.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}>
                <div>
                  <strong>{w.name}</strong>
                  <div style={{ fontSize: '0.8rem', opacity: 0.6 }}>Trigger: {w.trigger_type}</div>
                </div>
                <button onClick={() => triggerExecution(w.id)} className="glow-btn" style={{ padding: '0.5rem 1rem', borderRadius: '6px', backgroundColor: 'hsl(var(--primary))', color: '#fff', border: 'none', cursor: 'pointer' }}>
                  Run
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3>Execution History</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '1rem', maxHeight: '400px', overflowY: 'auto' }}>
            {executions.map(e => (
              <div key={e.id} style={{ padding: '0.8rem', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>ID: {e.id.slice(0, 8)}...</span>
                  <strong style={{ color: e.status === 'SUCCESS' ? '#22c55e' : '#ef4444' }}>{e.status}</strong>
                </div>
                <div style={{ fontSize: '0.8rem', opacity: 0.6, marginTop: '0.2rem' }}>
                  Retries: {e.retry_count} | Validation: {e.validation_status}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
export default WorkflowStudio;
