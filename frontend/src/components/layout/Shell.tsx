import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, Database, ShieldAlert, Cpu, 
  Workflow, FileText, Network, Settings, Sun, Moon, Search, X 

} from 'lucide-react';
import http from '../../services/http';

export const Shell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [overview, setOverview] = useState<any>({
    score: 95.5,
    rating: 'Excellent',
    components: { reliability: 98, incident_stability: 92, sla_compliance: 94 }
  });

  useEffect(() => {
    // Sync theme
    document.documentElement.className = theme;
  }, [theme]);

  useEffect(() => {
    // Fetch banner stats
    http.get('/api/v1/intelligence/overview')
      .then(res => setOverview(res.data))
      .catch(() => {});

    // Ctrl+K key listener
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchNavigate = (path: string) => {
    setSearchOpen(false);
    setSearchQuery('');
    navigate(path);
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))', color: 'hsl(var(--foreground))' }}>
      {/* Side Navigation */}
      <aside style={{ width: '260px', borderRight: '1px solid hsl(var(--border))', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '2rem' }} className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: 'hsl(var(--primary))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>
            A
          </div>
          <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>Antigravity Engine</span>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flexGrow: 1 }}>
          <Link to="/dashboard" style={linkStyle}><LayoutDashboard size={18} /> Executive Dashboard</Link>
          <Link to="/datasets" style={linkStyle}><Database size={18} /> Datasets Registry</Link>
          <Link to="/copilot" style={linkStyle}><Cpu size={18} /> AI Copilot Workspace</Link>
          <Link to="/investigations" style={linkStyle}><ShieldAlert size={18} /> Investigations Center</Link>
          <Link to="/workflows" style={linkStyle}><Workflow size={18} /> Workflow Studio</Link>
          <Link to="/reports" style={linkStyle}><FileText size={18} /> Executive Reports</Link>
          <Link to="/lineage" style={linkStyle}><Network size={18} /> Lineage Explorer</Link>
          <Link to="/system" style={linkStyle}><Settings size={18} /> System Diagnostics</Link>
        </nav>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
          <button onClick={() => setSearchOpen(true)} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.4rem 0.8rem', borderRadius: '6px', border: '1px solid hsl(var(--border))', cursor: 'pointer', background: 'none', color: 'inherit' }}>
            <Search size={14} /> <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>Ctrl+K</span>
          </button>
        </div>
      </aside>

      {/* Main Content Pane */}
      <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Persistent Global Intelligence Banner */}
        <header style={{ height: '60px', borderBottom: '1px solid hsl(var(--border))', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 2rem' }} className="glass-card">
          <div style={{ display: 'flex', gap: '2rem', fontSize: '0.9rem' }}>
            <div>Intelligence Score: <strong style={{ color: 'hsl(var(--primary))' }}>{Number(overview.score).toFixed(1)} ({overview.rating})</strong></div>
            <div>Reliability: <strong>{Number(overview.components.reliability).toFixed(0)}%</strong></div>
            <div>SLA Compliance: <strong>{Number(overview.components.sla_compliance).toFixed(0)}%</strong></div>
            <div>Incident Stability: <strong>{Number(overview.components.incident_stability).toFixed(0)}%</strong></div>
          </div>
        </header>

        <main style={{ padding: '2rem', flexGrow: 1 }}>
          {children}
        </main>
      </div>

      {/* Ctrl + K Search Overlay Modal */}
      {searchOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ width: '500px', padding: '1.5rem', borderRadius: '12px', border: '1px solid hsl(var(--border))', display: 'flex', flexDirection: 'column', gap: '1rem' }} className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 'bold' }}>Quick Navigation</span>
              <button onClick={() => setSearchOpen(false)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}><X size={16} /></button>
            </div>
            <input
              type="text"
              placeholder="Search sections..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ padding: '0.8rem', borderRadius: '6px', border: '1px solid hsl(var(--border))', backgroundColor: 'transparent', color: 'inherit', outline: 'none' }}
              autoFocus
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <div onClick={() => handleSearchNavigate('/dashboard')} style={searchItemStyle}>Executive Dashboard</div>
              <div onClick={() => handleSearchNavigate('/datasets')} style={searchItemStyle}>Datasets Registry</div>
              <div onClick={() => handleSearchNavigate('/copilot')} style={searchItemStyle}>AI Copilot Workspace</div>
              <div onClick={() => handleSearchNavigate('/investigations')} style={searchItemStyle}>Investigations Center</div>
              <div onClick={() => handleSearchNavigate('/workflows')} style={searchItemStyle}>Workflow Studio</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const linkStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.8rem',
  padding: '0.8rem 1rem',
  borderRadius: '8px',
  color: 'inherit',
  textDecoration: 'none',
  fontSize: '0.95rem',
  transition: 'background 0.2s',
};

const searchItemStyle = {
  padding: '0.8rem',
  borderRadius: '6px',
  cursor: 'pointer',
  transition: 'background 0.2s',
  backgroundColor: 'hsl(var(--secondary) / 0.3)'
};
export default Shell;
