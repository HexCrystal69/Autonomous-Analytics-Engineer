import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryDefaults';
import Shell from './components/layout/Shell';

// Lazy loading page views to maintain small initial bundle sizes
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Datasets = lazy(() => import('./pages/Datasets'));
const AIWorkspace = lazy(() => import('./pages/AIWorkspace'));
const WorkflowStudio = lazy(() => import('./pages/WorkflowStudio'));
const Investigations = lazy(() => import('./pages/Investigations'));
const ExecutiveReports = lazy(() => import('./pages/ExecutiveReports'));

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Suspense fallback={<div style={{ padding: '2rem', opacity: 0.5 }}>Loading console...</div>}>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/datasets" element={<Datasets />} />
              <Route path="/copilot" element={<AIWorkspace />} />
              <Route path="/workflows" element={<WorkflowStudio />} />
              <Route path="/investigations" element={<Investigations />} />
              <Route path="/reports" element={<ExecutiveReports />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Suspense>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
