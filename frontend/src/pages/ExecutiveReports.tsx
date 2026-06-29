import React, { useState, useEffect } from 'react';
import http from '../services/http';

export const ExecutiveReports: React.FC = () => {
  const [reports, setReports] = useState<any[]>([]);
  const [selectedRep, setSelectedRep] = useState<any>(null);

  useEffect(() => {
    http.get('/api/v1/reports')
      .then(res => setReports(res.data))
      .catch(() => {});
  }, []);

  const loadDetails = (id: string) => {
    http.get(`/api/v1/reports/${id}`)
      .then(res => setSelectedRep(res.data))
      .catch(() => {});
  };

  const generateReport = () => {
    http.post('/api/v1/reports/generate', { report_name: 'Monthly Briefing' })
      .then(() => {
        http.get('/api/v1/reports')
          .then(res => setReports(res.data));
      })
      .catch(() => {});
  };

  return (
    <div style={{ display: 'flex', gap: '1.5rem' }}>
      <div className="glass-card" style={{ width: '40%', padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>Reports</h3>
          <button onClick={generateReport} className="glow-btn" style={{ padding: '0.4rem 0.8rem', borderRadius: '6px', backgroundColor: 'hsl(var(--primary))', color: '#fff', border: 'none', cursor: 'pointer' }}>
            Generate
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '1rem' }}>
          {reports.map(r => (
            <div key={r.id} onClick={() => loadDetails(r.id)} style={{ padding: '1rem', border: '1px solid hsl(var(--border))', borderRadius: '8px', cursor: 'pointer' }}>
              <strong>{r.report_name}</strong>
              <div style={{ fontSize: '0.8rem', opacity: 0.6, marginTop: '0.2rem' }}>Generated: {r.generated_at}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card" style={{ flexGrow: 1, padding: '1.5rem' }}>
        {selectedRep ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <h2>{selectedRep.report_name}</h2>
              <div style={{ fontSize: '0.9rem', opacity: 0.7, marginTop: '0.5rem' }}>
                Quality Score: <strong style={{ color: 'hsl(var(--primary))' }}>{selectedRep.report_quality_score}%</strong>
              </div>
            </div>
            <div>
              <h4>Sections Content</h4>
              {selectedRep.sections.map((s: any) => (
                <div key={s.id} style={{ padding: '1rem', border: '1px solid hsl(var(--border))', borderRadius: '8px', marginTop: '0.8rem' }}>
                  <strong>{s.name}</strong>
                  <div style={{ fontSize: '0.9rem', opacity: 0.8, marginTop: '0.3rem' }}>Grounded metrics logs</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ opacity: 0.5, textAlign: 'center', marginTop: '4rem' }}>Select a report to view sections content and score metrics</div>
        )}
      </div>
    </div>
  );
};
export default ExecutiveReports;
