# Autonomous Analytics Engineer

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](#)
[![Coverage](https://img.shields.io/badge/coverage-%3E95%25-blue)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#)

An enterprise-grade Data Reliability, Governance, and AI-Copilot Platform. It monitors database schema evolution, executes contracts, detects distribution anomalies, and runs automated remediation workflows.

---

## 1. Overview
In modern data platform operations, unexpected schema mutations, column distribution drift, and silent SLA failures result in cascading downstream dashboard outages. **Autonomous Analytics Engineer** solves this by establishing a self-healing reliability layer that detects data quality anomalies, resolves issues automatically via workflow dependencies, and generates explainable, validation-grounded AI incident summaries.

---

## 2. Platform Architecture

```
                       +---------------------------+
                       |   Executive Dashboard     |
                       +-------------+-------------+
                                     |
                                     v
                       +-------------+-------------+
                       |    AI Copilot Workspace   |
                       +-------------+-------------+
                                     |
                                     v
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+--------+--------+                                     +--------+--------+
| Quality Engines |                                     | Workflow Studio |
+--------+--------+                                     +--------+--------+
         |                                                       |
         v                                                       v
+--------+--------+                                     +--------+--------+
| Data Contracts  |                                     | Remediation Ops |
+-----------------+                                     +-----------------+
```

---

## 3. Technology Stack

### Backend Stack
* **Framework**: FastAPI (Python 3.10)
* **ORM & Database**: SQLAlchemy (SQLite for development, PostgreSQL-ready)
* **Background Worker Tasks**: Celery + Redis
* **Test Suite**: Pytest (300+ tests, >95% coverage)

### Frontend Stack
* **Core**: React 19 + TypeScript + Vite
* **Routing**: React Router v7
* **State Management**: TanStack Query (React Query v5) + Axios
* **Graph Editors**: React Flow (`reactflow`)
* **Tables & Grid**: TanStack Table + `@tanstack/react-virtual`
* **Test Suite**: Vitest + React Testing Library (150+ tests, >93% coverage)

---

## 4. Key Capabilities & Features
1. **Data Profiling & Quality Validation**: Computes statistical summaries and checks column Null rates and semantic type compliance.
2. **Anomaly & Drift Scanners**: Detects outliers using IQR, Z-Score, LOF, and Isolation Forest algorithms.
3. **Data Contracts Verification**: Enforces schema contracts rules versioning.
4. **AI Copilot incident summaries**: Explains incident causes with deterministic validation scores and evidence grounding.
5. **Workflow Orchestration**: Implements DAG executions with DFS loop validation cycle protection and auto-retries.
6. **Multi-Tenant Partitioning**: Mapped client Tenant isolation bounds and RBAC guards.
7. **Cloud Cost Intelligence**: Tracks estimate compute CPU milliseconds costs per dataset run.

---

## 5. Running the Application

### Backend Setup
1. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Start API service:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

### Frontend Setup
1. Install node packages:
   ```bash
   cd frontend
   npm install
   ```
2. Start hot-reload dev server:
   ```bash
   npm run dev
   ```

### Running Tests
* Backend Pytest:
  ```bash
  .venv\Scripts\python -m pytest --cov=src --cov-report=term-missing
  ```
* Frontend Vitest:
  ```bash
  cd frontend
  npm run test
  ```

---

