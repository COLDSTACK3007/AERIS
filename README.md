# AERIS — Physics-Constrained Telemetry Processing & Data Imputation Framework

**Smart India Hackathon (SIH2026170) | Indian Space Research Organisation (ISRO)**

AERIS (Anomaly Engine for Real-time Imputation & Surveillance) is a full-stack platform designed to process real-time launch vehicle telemetry, detect and classify sensor anomalies (gaps, drift, noise, stuck values, spikes), perform physics-constrained data imputation using Physics-Informed Neural Networks (PINNs) & conservation laws, and visualize health status via an interactive dashboard.

---

## 🚀 Key Features & Modules

### Module 1: Data Ingestion & Preprocessing Engine
- Handles CSV upload & multi-rate telemetry streams (1 Hz to 1000 Hz)
- Adaptive resampling on unified timestamp grid
- Circular ring buffer management for real-time streaming
- Synthetic 600-second launch mission profile generator (16 ISRO parameters)

### Module 2: Anomaly Detection System
- Multi-strategy anomaly detection: Z-Score (3σ), Moving Average Deviation, Isolation Forest
- Anomaly Classification: `GAP`, `DRIFT`, `NOISE`, `STUCK`, `SPIKE`, `PHYSICS_VIOLATION`
- Contextual anomaly evaluation based on flight phase (PRE_LAUNCH, LIFTOFF, MAX_Q, STAGE_SEPARATION, COAST)
- Cross-parameter correlation breakdown detection

### Module 3: Physics-Constrained Data Imputation
- Physics-Informed Neural Networks (PINNs) in PyTorch
- Enforces Rocket Thrust Equation `F_thrust = (m_ox + m_fuel) * Isp * g0 / 1000`, Chamber Pressure Relationship `P_chamber = k * (m_ox + m_fuel)`, and O/F Mixture Ratio Consistency
- Duration-based Imputation Strategy:
  - **Short Gaps (<1s)**: Physics-weighted Cubic Spline
  - **Medium Gaps (1-5s)**: PINN prediction with boundary conditions
  - **Long Gaps (>5s)**: Ensemble of PINN + Extended Kalman Filter + Simulation
- Confidence scoring (0.0 to 1.0) with confidence bands

### Module 4: Interactive Visualization Dashboard
- Dark aerospace theme (ISRO inspired: deep navy, orange accents, cyan glows)
- 7 Core Visual Panels:
  1. Real-Time Telemetry Multi-Parameter Feed (Recharts with pan/zoom & parameter toggles)
  2. Subsystem Health Index Circular Gauge (0 to 100)
  3. Anomaly Classifier Catalog
  4. Physics Imputation Engine View
  5. Inter-Parameter Physics Correlation Heatmap Matrix
  6. Live Priority Alert Feed (INFO, WARNING, CRITICAL)
  7. Mission Flight Phase Timeline Overlay
- Sub-second data updates via WebSocket / REST APIs

### Module 5: Alert & Reporting System
- Priority-based alert generation
- Configurable thresholds
- Automated PDF/JSON Flight Summary Report generation

---

## 📁 Repository Structure

```
d:\SIH PS2\
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI Application Entrypoint
│   │   ├── config.py            # Environment & Settings
│   │   ├── database.py          # SQLAlchemy Engine & Session
│   │   ├── models/              # Telemetry, Anomaly, Alert DB Schema
│   │   ├── routers/             # Telemetry, Synthetic, Anomaly, Imputation, Alerts, Dashboard APIs
│   │   ├── services/            # Ingestion, Synthetic Data, Anomaly Detector, Physics Imputer, Alert Manager
│   │   ├── ml/                  # PINN PyTorch Model, Feature Engine, ML Classifiers
│   │   └── websocket/           # Connection Manager for Streaming
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main Dashboard App Component
│   │   ├── components/          # Dashboard, Charts, Common UI Components
│   │   ├── services/            # Axios API Client
│   │   ├── types/               # TypeScript Definitions
│   │   ├── index.css            # ISRO Design System
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

---

## 🛠️ How to Run Locally

### 1. Start Backend (FastAPI Server)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend API will be running at `http://localhost:8000`. API Documentation available at `http://localhost:8000/docs`.

### 2. Start Frontend (React + Vite Dashboard)
```bash
cd frontend
npm install
npm run dev
```
Dashboard will open at `http://localhost:5173`.

---

## 🐳 Docker Deployment
```bash
docker-compose up --build
```
