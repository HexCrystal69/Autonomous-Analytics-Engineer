import React, { useState, useEffect } from 'react';
import http from '../services/http';

export const AIWorkspace: React.FC = () => {
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<any>(null);
  const [inputVal, setInputVal] = useState('');

  useEffect(() => {
    http.get('/api/v1/ai/analyses')
      .then(res => {
        setAnalyses(res.data);
        if (res.data.length > 0) {
          fetchDetails(res.data[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const fetchDetails = (id: string) => {
    http.get(`/api/v1/ai/analysis/${id}`)
      .then(res => setActiveAnalysis(res.data))
      .catch(() => {});
  };

  const handleSend = () => {
    if (!inputVal) return;
    // Simulate generating explanation on demand
    setInputVal('');
  };

  return (
    <div style={{ display: 'flex', gap: '1.5rem', height: 'calc(100vh - 120px)' }}>
      {/* Left Pane: Prompt History */}
      <div className="glass-card" style={{ width: '250px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3>History</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflowY: 'auto' }}>
          {analyses.map(a => (
            <div
              key={a.id}
              onClick={() => fetchDetails(a.id)}
              style={{
                padding: '0.8rem',
                borderRadius: '6px',
                cursor: 'pointer',
                backgroundColor: activeAnalysis?.id === a.id ? 'hsl(var(--primary) / 0.15)' : 'hsl(var(--secondary) / 0.3)',
                border: activeAnalysis?.id === a.id ? '1px solid hsl(var(--primary))' : '1px solid transparent'
              }}
            >
              <div style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{a.analysis_type}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Confidence: {Number(a.confidence_score).toFixed(0)}%</div>
            </div>
          ))}
        </div>
      </div>

      {/* Center Pane: Chat Workspace */}
      <div className="glass-card" style={{ flexGrow: 1, padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <h3>Chat Workspace</h3>
        <div style={{ flexGrow: 1, margin: '1rem 0', padding: '1rem', border: '1px solid hsl(var(--border))', borderRadius: '8px', overflowY: 'auto', backgroundColor: 'hsl(var(--secondary) / 0.1)' }}>
          {activeAnalysis ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ alignSelf: 'flex-start', padding: '0.8rem 1.2rem', borderRadius: '12px 12px 12px 0', backgroundColor: 'hsl(var(--secondary) / 0.5)' }}>
                <strong>Prompt:</strong> {activeAnalysis.prompt_used || "No prompt details"}
              </div>
              <div style={{ alignSelf: 'flex-start', padding: '0.8rem 1.2rem', borderRadius: '12px 12px 12px 0', backgroundColor: 'hsl(var(--primary) / 0.15)', border: '1px solid hsl(var(--primary))' }}>
                <strong>Analysis:</strong> {activeAnalysis.response_text}
              </div>
            </div>
          ) : (
            <div style={{ opacity: 0.5, textAlign: 'center', marginTop: '4rem' }}>Select an analysis from prompt history</div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="Ask Copilot..."
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            style={{ flexGrow: 1, padding: '0.8rem', borderRadius: '6px', border: '1px solid hsl(var(--border))', backgroundColor: 'transparent', color: 'inherit', outline: 'none' }}
          />
          <button onClick={handleSend} className="glow-btn" style={{ padding: '0.8rem 1.5rem', borderRadius: '6px', backgroundColor: 'hsl(var(--primary))', color: '#fff', border: 'none', cursor: 'pointer' }}>
            Send
          </button>
        </div>
      </div>

      {/* Right Pane: Validation Panel */}
      <div className="glass-card" style={{ width: '300px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3>Validation & Evidence</h3>
        {activeAnalysis ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            <div>
              <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>Confidence Score</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'hsl(var(--primary))' }}>{Number(activeAnalysis.confidence_score).toFixed(1)}%</div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>Validation Status</div>
              <div style={{
                fontSize: '1rem',
                fontWeight: 'bold',
                color: activeAnalysis.status === 'COMPLETED' ? '#22c55e' : '#ef4444'
              }}>
                {activeAnalysis.status}
              </div>
            </div>
          </div>
        ) : (
          <p style={{ opacity: 0.5 }}>No validation metadata loaded.</p>
        )}
      </div>
    </div>
  );
};
export default AIWorkspace;
