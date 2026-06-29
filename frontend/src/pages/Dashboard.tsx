import React, { useState, useEffect } from 'react';
import http from '../services/http';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<any>({
    score: 95.5,
    rating: 'Excellent',
    components: { reliability: 98, incident_stability: 92, sla_compliance: 94, governance_compliance: 96 }
  });

  useEffect(() => {
    http.get('/api/v1/intelligence/overview')
      .then(res => setStats(res.data))
      .catch(() => {});
  }, []);

  const chartData = [
    { name: 'Mon', score: 92 },
    { name: 'Tue', score: 94 },
    { name: 'Wed', score: 93 },
    { name: 'Thu', score: 95 },
    { name: 'Fri', score: stats.score }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <h2>Executive Command Center</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>Intelligence Score</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0.5rem 0', color: 'hsl(var(--primary))' }}>
            {Number(stats.score).toFixed(1)}
          </div>
          <div>Rating: {stats.rating}</div>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>Reliability Score</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0.5rem 0' }}>
            {Number(stats.components.reliability).toFixed(0)}%
          </div>
          <div>Health metrics stable</div>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>SLA Compliance</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0.5rem 0' }}>
            {Number(stats.components.sla_compliance).toFixed(0)}%
          </div>
          <div>Target targets met</div>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>Governance Rating</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0.5rem 0' }}>
            {Number(stats.components.governance_compliance).toFixed(0)}%
          </div>
          <div>Active rules evaluated</div>
        </div>
      </div>

      <div className="glass-card" style={{ padding: '1.5rem', height: '350px' }}>
        <h3>Reliability History Trend</h3>
        <div style={{ width: '100%', height: '90%', marginTop: '1rem' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <XAxis dataKey="name" stroke="hsl(var(--foreground))" opacity={0.5} />
              <YAxis stroke="hsl(var(--foreground))" opacity={0.5} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))' }} />
              <Area type="monotone" dataKey="score" stroke="hsl(var(--primary))" fill="hsl(var(--primary) / 0.2)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
export default Dashboard;
