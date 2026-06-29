import React, { useState, useEffect } from 'react';
import AdvancedTable from '../components/tables/AdvancedTable';
import EntityDrawer from '../components/layout/EntityDrawer';
import http from '../services/http';

export const Datasets: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [selectedRow, setSelectedRow] = useState<any>(null);

  useEffect(() => {
    http.get('/api/v1/intelligence/top-datasets')
      .then(res => setData(res.data))
      .catch(() => {});
  }, []);

  const columns = [
    { key: 'id', label: 'Dataset ID', sortable: true },
    { key: 'name', label: 'Dataset Name', sortable: true }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <h2>Datasets Registry</h2>
      <AdvancedTable
        columns={columns}
        data={data}
        onRowClick={(row) => setSelectedRow(row)}
      />
      <EntityDrawer
        isOpen={!!selectedRow}
        onClose={() => setSelectedRow(null)}
        title="Dataset Details"
        data={selectedRow}
      />
    </div>
  );
};
export default Datasets;
