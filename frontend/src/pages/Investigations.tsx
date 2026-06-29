import React, { useState, useEffect } from 'react';
import http from '../services/http';

export const Investigations: React.FC = () => {
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [selectedInv, setSelectedInv] = useState<any>(null);

  useEffect(() => {
    http.get('/api/v1/investigations')
      .then(res => setInvestigations(res.data))
      .catch(() => {});
  }, []);

  const loadDetails = (id: string) => {
    http.get(`/api/v1/investigations/${id}`)
      .then(res => setSelectedInv(res.data))
      .catch(() => {});
  };

  return (
    <div style={{ display: 'flex', gap: '1.5rem' }}>
      <div className="glass-card" style={{ width: '40%', padding: '1.5rem' }}>
        <h3>Investigations</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '1rem' }}>
          {investigations.map(i => (
            <div key={i.id} onClick={() => loadDetails(i.id)} style={{ padding: '1rem', border: '1px solid hsl(var(--border))', borderRadius: '8px', cursor: 'pointer' }}>
              <strong>{i.title}</strong>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', opacity: 0.6, marginTop: '0.4rem' }}>
                <span>Priority: {i.priority}</span>
                <span>Status: {i.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card" style={{ flexGrow: 1, padding: '1.5rem' }}>
        {selectedInv ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <h2>{selectedInv.title}</h2>
              <p style={{ opacity: 0.8, marginTop: '0.5rem' }}>{selectedInv.description}</p>
            </div>
            <div>
              <h4>Timeline & Status Details</h4>
              <div style={{ borderLeft: '2px solid hsl(var(--primary))', paddingLeft: '1rem', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                <div>Status: <strong>{selectedInv.status}</strong></div>
                <div>Priority: <strong>{selectedInv.priority}</strong></div>
              </div>
            </div>
            <div>
              <h4>Automated Findings</h4>
              {selectedInv.findings.length > 0 ? (
                selectedInv.findings.map((f: any) => (
                  <div key={f.id} style={{ padding: '0.8rem', border: '1px solid hsl(var(--border))', borderRadius: '8px', marginTop: '0.5rem' }}>
                    <strong>Type: {f.type}</strong> (Confidence: {f.confidence}%)
                  </div>
                ))
              ) : (
                <p style={{ opacity: 0.5 }}>No automation findings linked.</p>
              )}
            </div>
          </div>
        ) : (
          <div style={{ opacity: 0.5, textAlign: 'center', marginTop: '4rem' }}>Select an investigation to view timeline and findings</div>
        )}
      </div>
    </div>
  );
};
export default Investigations;
