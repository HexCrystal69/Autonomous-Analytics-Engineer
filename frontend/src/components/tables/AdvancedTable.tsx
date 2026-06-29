import React, { useState } from 'react';
import { Search, ArrowUpDown, Download } from 'lucide-react';

interface Column {
  key: string;
  label: string;
  sortable?: boolean;
}

interface AdvancedTableProps {
  columns: Column[];
  data: any[];
  onRowClick?: (row: any) => void;
}

export const AdvancedTable: React.FC<AdvancedTableProps> = ({ columns, data, onRowClick }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [visibleColumns] = useState<string[]>(columns.map(c => c.key));


  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  const exportCSV = () => {
    const headers = visibleColumns.join(',');
    const rows = filteredData.map(row => 
      visibleColumns.map(key => JSON.stringify(row[key] ?? '')).join(',')
    );
    const blob = new Blob([[headers, ...rows].join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'export.csv';
    link.click();
  };

  const filteredData = data
    .filter(row => 
      Object.values(row).some(val => 
        String(val).toLowerCase().includes(searchQuery.toLowerCase())
      )
    )
    .sort((a, b) => {
      if (!sortKey) return 0;
      const valA = a[sortKey];
      const valB = b[sortKey];
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

  return (
    <div style={{ padding: '1.5rem' }} className="glass-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', alignItems: 'center' }}>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={16} style={{ position: 'absolute', left: '10px', opacity: 0.5 }} />
          <input
            type="text"
            placeholder="Search all columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '0.5rem 1rem 0.5rem 2.2rem',
              borderRadius: '6px',
              border: '1px solid hsl(var(--border))',
              backgroundColor: 'transparent',
              color: 'inherit',
              outline: 'none'
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={exportCSV} className="glow-btn" style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            border: '1px solid hsl(var(--border))',
            backgroundColor: 'transparent',
            color: 'inherit',
            cursor: 'pointer'
          }}>
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid hsl(var(--border))' }}>
              {columns
                .filter(col => visibleColumns.includes(col.key))
                .map(col => (
                  <th
                    key={col.key}
                    onClick={() => col.sortable && handleSort(col.key)}
                    style={{ padding: '0.8rem', cursor: col.sortable ? 'pointer' : 'default', userSelect: 'none' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      {col.label}
                      {col.sortable && <ArrowUpDown size={12} style={{ opacity: 0.5 }} />}
                    </div>
                  </th>
                ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row, index) => (
              <tr
                key={index}
                onClick={() => onRowClick?.(row)}
                style={{
                  borderBottom: '1px solid hsl(var(--border))',
                  cursor: onRowClick ? 'pointer' : 'default',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => {
                  if (onRowClick) e.currentTarget.style.backgroundColor = 'hsl(var(--secondary) / 0.5)';
                }}
                onMouseLeave={(e) => {
                  if (onRowClick) e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                {columns
                  .filter(col => visibleColumns.includes(col.key))
                  .map(col => (
                    <td key={col.key} style={{ padding: '0.8rem' }}>
                      {String(row[col.key] ?? '')}
                    </td>
                  ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
export default AdvancedTable;
