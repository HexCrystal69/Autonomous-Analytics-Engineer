import React from 'react';
import { X } from 'lucide-react';

interface EntityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  data: any;
}

export const EntityDrawer: React.FC<EntityDrawerProps> = ({ isOpen, onClose, title, data }) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '450px',
      height: '100vh',
      borderLeft: '1px solid hsl(var(--border))',
      padding: '2.5rem 1.5rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '1.5rem',
      zIndex: 999,
      boxShadow: '-10px 0 30px rgba(0,0,0,0.1)'
    }} className="glass-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{title}</h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
          <X size={20} />
        </button>
      </div>

      <div style={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {data ? (
          Object.entries(data).map(([key, value]) => (
            <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', opacity: 0.6, textTransform: 'uppercase' }}>{key.replace(/_/g, ' ')}</span>
              <span style={{ fontSize: '0.95rem' }}>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
            </div>
          ))
        ) : (
          <p style={{ opacity: 0.5 }}>No detailed information available.</p>
        )}
      </div>
    </div>
  );
};
export default EntityDrawer;
