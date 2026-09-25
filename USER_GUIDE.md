# ISRO AERIS — User Guide & Architecture Documentation
**Automated Evaluation, Anomaly Detection & Re-Imputation System for Launch Vehicle Flight Telemetry**

> [!NOTE]
> AERIS is a real-time flight telemetry surveillance and physics compliance platform engineered for ISRO launch vehicles (such as LVM3 / PSLV / SSLV). It detects multi-sensor anomalies, computes real-time subsystem health scores, enforces governing physics laws (combustion & mass-conservation), and restores corrupted sensor data using Physics-Informed Neural Networks (PINN).

---

## 📑 Table of Contents
1. [Quick Start & System Launch](#1-quick-start--system-launch)
2. [Step-by-Step Dashboard Tutorial](#2-step-by-step-dashboard-tutorial)
   - [2.1 Live Mission Flight Control & Timeline Scrubbing](#21-live-mission-flight-control--timeline-scrubbing)
   - [2.2 Generating & Ingesting Flight Datasets](#22-generating--ingesting-flight-datasets)
   - [2.3 Uploading Custom Telemetry CSV Files](#23-uploading-custom-telemetry-csv-files)
   - [2.4 Subsystem Health Scoring & Diagnostics](#24-subsystem-health-scoring--diagnostics)
   - [2.5 Physics-Informed Neural Network (PINN) Data Recovery](#25-physics-informed-neural-network-pinn-data-recovery)
   - [2.6 Flight Surveillance Reports & Exports](#26-flight-surveillance-reports--exports)
3. [Under the Hood: System Architecture](#3-under-the-hood-system-architecture)
   - [3.1 Data Processing & Ingestion Pipeline](#31-data-processing--ingestion-pipeline)
   - [3.2 Anomaly Detection Engine](#32-anomaly-detection-engine)
   - [3.3 PINN Imputation Engine](#33-pinn-imputation-engine)
   - [3.4 Subsystem Health Calculation Formula](#34-subsystem-health-calculation-formula)
4. [Flight Telemetry CSV Format Specification](#4-flight-telemetry-csv-format-specification)
5. [Automated Verification & Unit Testing](#5-automated-verification--unit-testing)
6. [Converting / Exporting to PDF](#6-converting--exporting-to-pdf)

---

## 1. Quick Start & System Launch

AERIS runs on a dual-service architecture: a **FastAPI backend** managing physics calculations and database storage, and a **React + TypeScript frontend** for real-time visualization.

### Prerequisites
* **Python 3.10+** (with `pip`, `fastapi`, `uvicorn`, `sqlalchemy`, `pandas`, `numpy`, `scipy`)
* **Node.js 18+** & `npm`

### Starting the Backend Server
Open a terminal in the project directory and run:
```bash
cd "d:\SIH PS2\backend"
py -m uvicorn app.main:app --reload --port 8000
```
* **API Documentation**: `http://localhost:8000/docs`

### Starting the Frontend UI
Open a second terminal window and run:
```bash
cd "d:\SIH PS2\frontend"
npm run dev
```
* **Web Dashboard URL**: `http://localhost:5173`

---

## 2. Step-by-Step Dashboard Tutorial

```
[1. Ingest Data (Synthetic/CSV)] ──► [2. Anomaly Detection Engine] ──► [3. Health Scoring]
                                                                               │
[6. Export JSON / Print PDF Report] ◄── [5. PINN Physics Imputation] ◄─────────┘
```

---

### 2.1 Live Mission Flight Control & Timeline Scrubbing
At the top of the main dashboard, you will find the **Mission Flight Control Bar**.

1. **Flight Phase Tracker**: Visualizes the 7 distinct launch phases:
   - `PRE_LAUNCH` ($T \le 10\text{s}$): Pre-ignition setup & ground checkouts.
   - `LIFTOFF` ($10\text{s} < T \le 60\text{s}$): Solid/Liquid booster ignition and ascent ramping.
   - `MAX_Q` ($60\text{s} < T \le 90\text{s}$): Dynamic pressure peak; structural vibration envelope maximum.
   - `STAGE_1_FLIGHT` ($90\text{s} < T \le 150\text{s}$): Core propulsion steady-state burn.
   - `STAGE_SEPARATION` ($150\text{s} < T \le 160\text{s}$): Stage 1 jettison & Stage 2 ignition transient.
   - `STAGE_2_FLIGHT` ($160\text{s} < T \le 450\text{s}$): Cryogenic/upper-stage orbital insertion burn.
   - `COAST_ORBIT` ($T > 450\text{s}$): Payload deployment and coast phase.
2. **PLAY / PAUSE Button**: Toggles live real-time flight simulation playback.
3. **Interactive Scrubbing Track**: Click or drag anywhere along the timeline track to inspect telemetry at any specific timestamp ($T+0.0\text{s}$ to $T+600.0\text{s}$).

---

### 2.2 Generating & Ingesting Flight Datasets
If no data is present, click **"Scan & Ingest"** in the top-right header menu.
- Generates a **600-second flight dataset** at 10 Hz (6,000 data points across 18 sensors).
- Automatically injects realistic flight anomalies (telemetry gaps, sensor drifts, vibration noise spikes, and stuck sensors).
- Instantly runs anomaly detection and health scoring algorithms across all parameters.

---

### 2.3 Uploading Custom Telemetry CSV Files
To test real flight recordings or custom datasets:
1. Click **"Upload CSV Telemetry"** in the header.
2. Select any compliant `.csv` file (for testing, use the included sample file: `sample_flight_telemetry.csv`).
3. The platform automatically cleans missing values, maps sensor alias names (e.g. `Time` $\rightarrow$ `timestamp`, `p_chamber` $\rightarrow$ `P_chamber`), resamples time steps, and clears out previous database telemetry.

---

### 2.4 Subsystem Health Scoring & Diagnostics
The dashboard evaluates 4 core vehicle subsystems:
* **PROPULSION**: Chamber pressure ($P_{\text{chamber}}$), thrust ($F_{\text{thrust}}$), pump speeds ($N_{\text{pump}}$), propellant flow rates ($\dot{m}_{\text{ox}}, \dot{m}_{\text{fuel}}$).
* **PRESSURIZATION**: LOX and Fuel tank ullage pressures ($P_{\text{tank,lox}}, P_{\text{tank,fuel}}$).
* **STRUCTURAL / THERMAL**: Axial acceleration ($a_{\text{axial}}$), 3-axis vibration accelerometers ($\text{vib}_x, \text{vib}_y, \text{vib}_z$), skin temperature ($T_{\text{skin}}$).
* **AVIONICS & ATTITUDE**: Main bus voltage ($V_{\text{batt}}$), bus current ($I_{\text{bus}}$), angular rates ($\omega_{\text{roll}}, \omega_{\text{pitch}}, \omega_{\text{yaw}}$).

> [!TIP]
> The **Health Score Gauge** indicates overall vehicle integrity (0–100%). Subsystem status displays `NOMINAL` (green) when health is $\ge 85\%$ or `DEGRADED` / `CRITICAL` when sensor faults occur.

---

### 2.5 Physics-Informed Neural Network (PINN) Data Recovery
When sensors fail or drop signal packets (creating data gaps `NaN`), standard statistical interpolation (like linear spline) creates unphysical results.

1. Navigate to the **Imputation & PINN** view.
2. View detected sensor gaps listed in the **Missing Telemetry Log**.
3. Click **"Solve PINN & Restore"**.
4. The backend physics engine calculates lost values by enforcing governing physical laws:
   $$\text{Relationship 1: } P_{\text{chamber}} = k \cdot (\dot{m}_{\text{ox}} + \dot{m}_{\text{fuel}})$$
   $$\text{Relationship 2: } F_{\text{thrust}} = (\dot{m}_{\text{ox}} + \dot{m}_{\text{fuel}}) \cdot I_{\text{sp}} \cdot g_0$$
5. View the side-by-side comparative chart showing **Original Data** vs **PINN Restored Telemetry**.

---

### 2.6 Flight Surveillance Reports & Exports
1. Navigate to the **Report** section from the navigation bar.
2. Click **"Compile Report"**.
3. Generates a summary featuring:
   - Overall health score & physics compliance score.
   - Subsystem operational status matrix.
   - Comprehensive anomaly catalog detailing time, parameter, fault type, and severity.
4. Export options:
   - **JSON Export**: Downloads raw structured JSON containing all anomaly records and health metrics.
   - **Print / PDF**: Opens the native print window styled for formal PDF mission report archival.

---

## 3. Under the Hood: System Architecture

### 3.1 Data Ingestion Pipeline
```
[ Raw CSV Upload / Synthetic Generator ]
                 │
                 ▼
     [ Standard Header Normalization & Alias Mapping ]
                 │
                 ▼
      [ Data Type Cleaning & Resampling (10 Hz) ]
                 │
                 ▼
       [ SQLite Database (aeris.db) Bulk Persistence ]
```

---

### 3.2 Anomaly Detection Engine
Located in `backend/app/services/anomaly_detector.py`, the engine detects 5 categories of anomalies:
1. **GAP**: `timestamp` present, but sensor value is `NaN` or `None`.
2. **SPIKE**: Sudden rate of change exceeding threshold:
   $$|\Delta x_t| = |x_t - x_{t-1}| > \sigma_{\text{threshold}}$$
3. **STUCK**: Sensor variance is zero over a sliding window:
   $$\text{Var}(x_{t..t+w}) < 10^{-6}$$
4. **NOISE**: Standard deviation $\sigma$ exceeds nominal flight phase limits.
5. **DRIFT**: Cumulative baseline departure over extended flight windows.

---

### 3.3 PINN Imputation Engine
Located in `backend/app/services/imputer.py`, the solver uses physics-informed loss constraints:
$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{data}} + \lambda_{\text{physics}} \cdot \mathcal{L}_{\text{physics}}$$

Where $\mathcal{L}_{\text{physics}}$ penalizes violations of mass balance and thrust coefficient equations.

---

### 3.4 Subsystem Health Calculation Formula
Located in `backend/app/services/alert_manager.py`:
$$\text{Health Score} = \max\left(10, 100 - \sum \text{Deductions}\right)$$

Deduction penalties per detected anomaly event:
- **CRITICAL** anomaly event: $-8.0$ points
- **WARNING** anomaly event: $-3.5$ points
- **INFO** anomaly event: $-1.0$ point

---

## 4. Flight Telemetry CSV Format Specification

Custom CSV files should follow standard column headers:

| Header Name | Data Type | Units | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` (or `Time`) | float | s | Flight elapsed time $T+$ in seconds |
| `P_chamber` | float | MPa | Rocket engine combustion chamber pressure |
| `T_chamber` | float | K | Combustion chamber temperature |
| `m_ox` | float | kg/s | Liquid oxidizer mass flow rate |
| `m_fuel` | float | kg/s | Fuel mass flow rate |
| `F_thrust` | float | kN | Total propulsion thrust output |
| `N_pump` | float | RPM | Turbopump rotational speed |
| `P_tank_lox` | float | MPa | LOX tank ullage pressure |
| `P_tank_fuel` | float | MPa | Fuel tank ullage pressure |
| `acc_axial` | float | g | Axial acceleration |
| `vib_x`, `vib_y`, `vib_z` | float | g | Structural vibration acceleration along X/Y/Z axes |
| `v_batt` | float | V | Main avionics battery voltage |
| `i_bus` | float | A | Electrical power bus current |
| `T_skin` | float | K | External vehicle skin temperature |

---

## 5. Automated Verification & Unit Testing

The platform includes an automated 14-point test suite in `backend/test_all.py`:

To run all automated verification tests:
```bash
cd "d:\SIH PS2\backend"
py test_all.py
```

---

## 6. Converting / Exporting to PDF

### Method 1: Save directly from Browser (Recommended)
1. Open this file [`USER_GUIDE.md`](file:///d:/SIH%20PS2/USER_GUIDE.md) in your web browser (or open the AERIS Report tab in the app and click **Print / PDF**).
2. Press `Ctrl + P` (or `Cmd + P` on Mac).
3. Destination: Select **"Save as PDF"**.
4. Click **Save**.

### Method 2: Export via VS Code / IDE Extension
1. Install the **Markdown PDF** or **Markdown Preview Enhanced** extension.
2. Right-click [`USER_GUIDE.md`](file:///d:/SIH%20PS2/USER_GUIDE.md) in VS Code.
3. Select **Markdown PDF: Export (pdf)**.
