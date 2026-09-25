FINAL AERIS — PRODUCTION & CORRECTNESS FIX
============================================

You are working on the FINAL AERIS project currently present in this workspace.

This is NOT a rebuild.

The project is already substantially implemented and functional. Your task is to
perform a FINAL correctness, data-integrity, ML/PINN, analytics, and production
readiness pass.

============================================================
ABSOLUTE RULES
============================================================

1. DO NOT rebuild the project.
2. DO NOT replace the existing architecture.
3. DO NOT remove working functionality.
4. DO NOT change working APIs unnecessarily.
5. DO NOT change existing routes unnecessarily.
6. DO NOT replace real calculations with mock values.
7. DO NOT add fake/random data.
8. DO NOT add artificial noise to charts.
9. DO NOT fabricate ML metrics.
10. DO NOT fabricate anomaly scores.
11. DO NOT fabricate health scores.
12. DO NOT fabricate subsystem scores.
13. DO NOT claim a model is more accurate than its measured results.
14. DO NOT retrain the PINN automatically unless a genuine training/evaluation
    problem requires it and the available data supports retraining.
15. Preserve the current UI structure and existing functionality unless a
    change below specifically requires modification.
16. If something cannot be calculated reliably from the available data,
    display "N/A", "Insufficient data", or an equivalent honest state instead
    of inventing a value.
17. After every change, run the existing tests and verify there are no
    regressions.

The objective is:

EXISTING WORKING AERIS
        +
FINAL CORRECTNESS FIXES
        +
DATA INTEGRITY
        +
HONEST ML/PINN REPORTING
        +
PRODUCTION READINESS

============================================================
PHASE 1 — FULL PROJECT AUDIT
============================================================

Before modifying anything, inspect the entire project.

Understand:

- frontend
- backend
- API routes
- telemetry pipeline
- synthetic telemetry generator
- experimental datasets
- anomaly detection
- phase detection
- physics calculations
- health calculation
- PINN training
- PINN checkpoint loading
- PINN inference
- EKF recovery
- physics recovery
- interpolation
- reports
- Parametric Scatter
- anomaly Deep-Dive
- Evaluation Summary
- tests
- configuration/constants.

Do not assume that documentation is correct.

Use the actual implementation as the source of truth.

Create an internal dependency map:

DATA
 ↓
PREPROCESSING
 ↓
PHASE DETECTION
 ↓
ANOMALY DETECTION
 ↓
PHYSICS VALIDATION
 ↓
ML/PINN
 ↓
RECOVERY
 ↓
HEALTH
 ↓
FRONTEND
 ↓
REPORT

Do not modify anything until this flow is understood.

============================================================
PHASE 2 — SYSTEM HEALTH INDEX
============================================================

IMPORTANT:

The current System Health Index has a correctness problem.

The backend provides the overall health information, but the frontend currently
derives subsystem percentages from the overall score using offsets/formulas.

For example, values such as:

PROPULSION = overall + X
THERMAL = overall - X
POWER = overall - X
GUIDANCE = overall

must NOT be presented as independently calculated subsystem health.

REMOVE this artificial derivation.

------------------------------------------------------------
OPTION A — PREFERRED
------------------------------------------------------------

Implement genuine subsystem health calculations using actual anomaly/telemetry
data belonging to each subsystem.

Use the project's actual telemetry schema.

Possible subsystem mapping should be based ONLY on parameters that genuinely
belong to the subsystem.

For example, if supported by the existing telemetry:

PROPULSION:
- P_chamber
- T_chamber
- m_ox
- m_fuel
- F_thrust
- N_pump

THERMAL:
- actual thermal parameters present in the dataset

POWER / ELECTRICAL:
- actual electrical parameters present in the dataset

GUIDANCE / NAV:
- actual guidance/navigation parameters present in the dataset

DO NOT invent sensors that do not exist.

Calculate each subsystem score from actual data/anomaly severity.

The exact scoring formula should reuse the project's existing health/anomaly
logic wherever possible.

------------------------------------------------------------
OPTION B — IF INSUFFICIENT DATA
------------------------------------------------------------

If the available dataset does not contain enough information to calculate
legitimate subsystem health:

DO NOT fabricate subsystem percentages.

Instead display:

SUBSYSTEM HEALTH

PROPULSION    DATA AVAILABLE
THERMAL       INSUFFICIENT DATA
POWER         INSUFFICIENT DATA
GUIDANCE      INSUFFICIENT DATA

or another professional equivalent.

The UI must never imply a measurement that the backend cannot support.

------------------------------------------------------------
STATUS CONSISTENCY
------------------------------------------------------------

Ensure:

score → status

uses one authoritative threshold configuration.

Do not allow situations where a percentage and status contradict the actual
configured thresholds.

Do not change thresholds simply to make the UI look better.

============================================================
PHASE 3 — HEALTH SCORE CONSISTENCY
============================================================

Keep the existing overall health calculation if it is already correct.

Verify:

- critical penalties
- warning penalties
- info penalties
- duration weighting
- confidence weighting
- grouping
- final normalization
- minimum/maximum bounds.

Ensure:

0 <= health <= 100

Ensure the frontend displays the actual backend value.

No frontend recalculation of the overall score.

The frontend should render backend truth.

============================================================
PHASE 4 — PHYSICS TOLERANCE UNIFICATION
============================================================

Inspect every location where physics tolerances are defined.

Currently different modules may use different tolerances for the same quantity.

Create one authoritative configuration.

For example:

THRUST_TOLERANCE_KN
PRESSURE_TOLERANCE_MPA
TEMPERATURE_TOLERANCE_K
etc.

Use the actual existing tolerances as the starting point.

DO NOT arbitrarily change them.

All relevant modules must import/use the same authoritative values:

- physics validation
- anomaly validation
- PINN physics residual
- recovery
- alerts
- reports
- UI status.

This prevents one module from saying:

VALID

while another says:

VIOLATION

for the same measurement.

============================================================
PHASE 5 — PHASE-RELATIVE ANOMALY DETECTION
============================================================

Inspect the existing phase-relative anomaly implementation.

The current implementation can calculate phase statistics from the same dataset
that it evaluates.

This creates reference-data leakage.

Correct this methodology.

------------------------------------------------------------
REFERENCE DATA
------------------------------------------------------------

Create a clear separation between:

REFERENCE / BASELINE DATA

and

EVALUATION DATA.

The baseline must be calculated from appropriate reference observations.

Where available, use:

- healthy/reference telemetry
- training/reference data
- historical baseline
- explicitly designated baseline dataset.

Do NOT use the target observation itself to define the baseline against which
it is evaluated.

------------------------------------------------------------
STATISTICS
------------------------------------------------------------

For each:

parameter
+
flight phase

calculate appropriate statistics:

- mean
- standard deviation
- median
- MAD
- robust limits

depending on what is appropriate for the data.

Then calculate:

phase-relative deviation

or

z-score

for the evaluation observation.

Use robust statistics if the reference distribution contains outliers.

Do not fabricate a reference distribution.

============================================================
PHASE 6 — PARAMETRIC SCATTER
============================================================

Preserve the existing Parametric Scatter functionality.

The current scatter is a real scatter implementation.

Do NOT add artificial noise.

Do NOT modify points simply to make the chart visually resemble another
team's project.

If:

m_ox → F_thrust

naturally produces a strong linear relationship because of the implemented
physics equation, preserve that relationship.

Verify:

- X mapping
- Y mapping
- units
- phase assignment
- anomaly assignment
- tooltips
- click behavior
- filters
- downsampling.

Ensure downsampling never removes anomaly points.

Keep:

- phase colors
- anomaly highlighting
- hover information
- click → Deep-Dive.

Calculate and display correlation only when mathematically appropriate.

Do not call correlation causation.

============================================================
PHASE 7 — ANOMALY DEEP-DIVE
============================================================

Ensure every anomaly displayed in the UI can be traced back to an actual
backend anomaly record.

Deep-Dive must use real:

- anomaly ID
- timestamp
- parameter
- phase
- observed value
- anomaly type
- severity
- score, if available
- physics residual, if available
- recovery information, if available.

Do NOT create an explanation that invents causality.

Use language such as:

"Contributing evidence"

rather than:

"Root cause"

unless the system genuinely proves causality.

============================================================
PHASE 8 — PINN INTEGRITY
============================================================

IMPORTANT:

The project contains a genuinely trained PINN checkpoint.

DO NOT replace it with a fake model.

DO NOT claim better performance than the actual evaluation.

Verify:

- checkpoint exists
- checkpoint loads
- architecture matches
- feature order matches
- normalization matches
- metadata matches
- inference works
- model version is correctly reported.

The application should clearly identify the loaded model.

Example:

PINN v3
TRAINED
CHECKPOINT LOADED

Only show this if actually true.

============================================================
PHASE 9 — PINN PERFORMANCE REPORTING
============================================================

The current PINN is trained, but its measured reconstruction performance is
not uniformly strong.

DO NOT hide this.

Do NOT change MAE/RMSE values.

Do NOT replace them with better-looking values.

Do NOT claim:

"PINN is the most accurate method"

unless the actual evaluation proves this.

Instead show actual metrics.

For example:

PINN
MAE
RMSE

and compare against:

Interpolation
Physics
EKF

using the real measured values.

If PINN is worse for a particular parameter, show that honestly.

This is acceptable.

The project should demonstrate:

MODEL TRAINED

rather than falsely claiming:

MODEL PERFECT.

============================================================
PHASE 10 — PINN EVALUATION
============================================================

Verify evaluation uses a proper separation:

TRAIN
VALIDATION
TEST

Do not evaluate using training samples.

Check for:

- data leakage
- normalization leakage
- target leakage
- duplicate samples
- incorrect masks
- incorrect feature ordering.

Test reconstruction for relevant missing-data patterns.

For example:

5%
10%
20%
30%

only if the current project supports those evaluation scenarios.

Report:

MAE
RMSE
physics residual

using actual values.

============================================================
PHASE 11 — RECOVERY COMPARISON
============================================================

Keep the existing recovery methods.

Display actual results:

PINN
Physics
EKF
Interpolation

Do not automatically declare a winner.

Instead show:

METHOD
MAE
RMSE
PHYSICS RESIDUAL
STATUS

If one method performs better, let the data demonstrate that.

============================================================
PHASE 12 — DOCUMENTATION CORRECTION
============================================================

Inspect README and technical documentation against the actual implementation.

Remove or correct claims that the implementation does not actually perform.

For example:

If documentation claims an "isentropic thermodynamic law" is explicitly
implemented as a physics residual, verify that it actually is.

If it is not actually implemented:

DO NOT add fake code merely to satisfy documentation.

Instead correct the documentation to describe the physics constraints that
really exist.

Documentation must match code.

============================================================
PHASE 13 — DATASET TRANSPARENCY
============================================================

Clearly distinguish:

SYNTHETIC DATA
EXPERIMENTAL DATA
REFERENCE DATA
TRAINING DATA
VALIDATION DATA
TEST DATA
DEMO DATA

Do not call synthetic telemetry "real flight telemetry."

Do not call training data "test data."

Do not use test data during training.

Do not mix evaluation results into training.

If synthetic telemetry is used for demonstration, clearly label it as:

SYNTHETIC / SIMULATION DATA

This is especially important for the SIH presentation.

============================================================
PHASE 14 — REPORT CONSISTENCY
============================================================

Reports must use the same underlying data as the dashboard.

Verify:

Dashboard health
=
API health
=
JSON report health
=
PDF report health

Likewise:

anomaly counts
physics compliance
recovery metrics
PINN metrics

must come from the same source.

No hardcoded report values.

============================================================
PHASE 15 — UI FINAL POLISH
============================================================

Preserve the current visual direction.

Apply ONLY production-quality refinements.

The UI should feel like:

AEROSPACE ENGINEERING
+
MISSION CONTROL
+
TELEMETRY ANALYSIS

Avoid:

- excessive glassmorphism
- excessive gradients
- excessive neon
- excessive rounded cards
- card-within-card layouts
- giant typography
- unnecessary animations
- fake futuristic decoration.

For the System Health Index specifically:

DO NOT display artificially derived subsystem scores.

Use:

SYSTEM HEALTH INDEX

OVERALL HEALTH
50%
● CRITICAL

SUBSYSTEM HEALTH

PROPULSION       actual score/status
THERMAL          actual score/status
POWER / ELECT    actual score/status
GUIDANCE / NAV   actual score/status

ALERT SUMMARY

● 6 CRITICAL
● 1 WARNING
● 0 INFO

Use subtle dividers instead of many nested cards.

============================================================
PHASE 16 — FRONTEND BUILD
============================================================

Perform a clean frontend dependency installation.

Do NOT modify application code merely to work around a broken node_modules
installation.

Clean:

node_modules
package-lock if appropriate

then:

npm install

then:

npm run build

Fix genuine source-code errors if any appear.

Do not suppress errors.

The final production build must succeed.

============================================================
PHASE 17 — BACKEND TESTS
============================================================

Run the entire existing backend test suite.

Do not delete failing tests.

Do not weaken assertions.

Do not modify expected values simply to make tests pass.

If a test fails because the implementation is wrong:

FIX THE IMPLEMENTATION.

If a test is genuinely outdated because the documented intended behavior
changed:

update the test only after verifying the intended behavior.

============================================================
PHASE 18 — END-TO-END TEST
============================================================

Run the complete flow:

DATASET
 ↓
INGESTION
 ↓
PREPROCESSING
 ↓
PHASE DETECTION
 ↓
ANOMALY DETECTION
 ↓
PHASE-RELATIVE ANALYSIS
 ↓
PHYSICS VALIDATION
 ↓
PINN / RECOVERY
 ↓
HEALTH
 ↓
SCATTER
 ↓
DEEP-DIVE
 ↓
EVALUATION
 ↓
REPORT

Verify that the same anomaly/data record can be traced through the entire
system.

============================================================
PHASE 19 — NO REGRESSION CHECK
============================================================

Verify all existing functionality:

- dashboard
- telemetry
- live telemetry
- synthetic telemetry
- CSV upload
- anomaly detection
- anomaly timeline
- Parametric Scatter
- Deep-Dive
- physics
- PINN
- EKF
- interpolation
- recovery
- health
- alerts
- correlation
- reports
- JSON export
- PDF/report functionality
- navigation
- responsive UI.

Nothing that previously worked should be silently removed.

============================================================
PHASE 20 — FINAL VALIDATION
============================================================

Before declaring completion, verify:

[ ] Overall health is genuinely calculated.
[ ] Subsystem health is genuinely calculated OR explicitly marked unavailable.
[ ] No frontend health fabrication remains.
[ ] Physics tolerances are centralized.
[ ] Phase-relative baseline does not use evaluation data improperly.
[ ] Scatter uses real telemetry.
[ ] No artificial jitter exists.
[ ] Anomalies are real.
[ ] Deep-Dive uses real anomaly records.
[ ] PINN checkpoint loads.
[ ] PINN metrics are real.
[ ] PINN is not falsely presented as superior.
[ ] Training/validation/test separation is correct.
[ ] Synthetic and experimental data are clearly distinguished.
[ ] Reports match dashboard/API values.
[ ] Documentation matches implementation.
[ ] Backend tests pass.
[ ] E2E tests pass.
[ ] Frontend production build succeeds.
[ ] No existing feature is broken.

============================================================
FINAL REPORT TO ME
============================================================

When finished, provide a concise but detailed report with EXACTLY these
sections:

1. FIXES COMPLETED

List every actual issue fixed.

2. DATA / COMPUTATION CHANGES

Explain any change to calculations or data flow.

3. ML / PINN STATUS

State:
- checkpoint used
- training status
- actual evaluation metrics
- whether retraining was performed
- remaining model limitations

4. HEALTH SYSTEM

Explain:
- overall health calculation
- subsystem health calculation
- anomaly severity relationship

5. ANOMALY SYSTEM

Explain:
- standard anomaly detection
- phase-relative detection
- baseline/reference data
- Deep-Dive

6. PHYSICS

Explain:
- implemented physics constraints
- centralized tolerances
- residual calculations

7. TEST RESULTS

Report actual results for:

- backend tests
- E2E tests
- frontend build

8. REMAINING LIMITATIONS

Do NOT hide limitations.

If a feature cannot be scientifically supported by the available dataset,
say so.

9. FILES CHANGED

List all changed files and briefly explain why.

============================================================
FINAL PRINCIPLE
============================================================

AERIS must be:

CORRECT > IMPRESSIVE

REAL DATA > FAKE DATA

MEASURED METRICS > CLAIMS

ACTUAL MODEL PERFORMANCE > MARKETING

ENGINEERING VALIDITY > VISUAL APPEARANCE

Do not change numbers merely because they look bad.

Do not hide weak ML performance.

Do not fabricate subsystem scores.

Do not fabricate root causes.

Do not fabricate experimental results.

Make the final project technically defensible and presentation-ready while
preserving all existing working functionality.