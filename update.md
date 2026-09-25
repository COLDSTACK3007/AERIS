You are working on the existing AERIS project provided in this workspace.

IMPORTANT:

* This is an EXISTING, WORKING PROJECT.
* DO NOT rebuild it from scratch.
* DO NOT remove existing functionality.
* DO NOT replace working modules unnecessarily.
* DO NOT change existing APIs, data formats, routes, or behavior unless required for a specific fix.
* Preserve the current UI/design wherever possible.
* All existing features must continue working after these changes.
* Do not use fake/mock values for newly added analytical results.
* Do not hardcode model outputs, anomaly explanations, confidence values, accuracy, MAE, RMSE, or physics residuals.
* Every displayed value must come from actual project data, calculations, or an actually trained model.
* If a requested feature cannot be calculated reliably from the available data, clearly expose that limitation rather than inventing a value.

==================================================
PHASE 1 — AUDIT THE EXISTING PROJECT FIRST
==========================================

Before changing anything:

1. Inspect the entire existing project.
2. Identify:

   * frontend structure
   * backend structure
   * APIs
   * database/storage if present
   * telemetry pipeline
   * anomaly detection pipeline
   * ML models
   * PINN training code
   * saved checkpoints
   * physics calculations
   * EKF
   * interpolation/recovery
   * health score
   * flight-phase detection
   * report generation
   * existing tests
3. Understand the actual data flow:

CSV/input
→ preprocessing
→ telemetry
→ phase detection
→ anomaly detection
→ physics validation
→ ML detection
→ recovery/imputation
→ health calculation
→ frontend
→ reports.

4. Do NOT assume that a feature exists simply because a file or function has a similar name.
5. Verify that each feature is actually connected and executed.
6. Create a concise internal map of the existing architecture before modifying it.

==================================================
PHASE 2 — PRESERVE EXISTING FUNCTIONALITY
=========================================

The following existing functionality must remain operational:

* telemetry ingestion
* CSV processing
* synthetic telemetry generation, if currently supported
* live/WebSocket telemetry
* flight-phase detection
* existing anomaly detection
* GAP detection
* SPIKE detection
* DRIFT detection
* STUCK detection
* NOISE detection
* Isolation Forest / existing ML anomaly detection
* physics validation
* physics-based calculations
* PINN recovery
* EKF recovery
* interpolation recovery
* health score
* subsystem health
* anomaly timeline
* alerts
* correlation matrix
* report generation
* JSON export
* PDF/print functionality
* existing API endpoints
* existing frontend navigation
* existing responsive behavior.

Do not remove these features just to implement the new features below.

==================================================
PHASE 3 — FIX PINN CORRECTNESS
==============================

Inspect the current PINN implementation carefully.

Fix the following issues if they are still present:

### A. Synthetic physics loss

If synthetic physics loss is calculated but not actually included in the optimization objective, fix it.

The effective training objective should correctly combine the applicable losses, for example:

total_loss =
data_loss
+ experimental_loss
+ experimental_physics_loss
+ synthetic_physics_loss

Do not blindly use this exact formula if the existing architecture requires a different mathematically correct formulation. Verify the implementation.

The physics loss must actually contribute gradients to the model.

### B. Missing-data masks

Verify that masking is handled independently for every telemetry variable.

If multiple sensors are missing, the model must know which individual variables are missing.

Do not accidentally use only one target mask for multiple variables.

Test:

* 5% missing
* 10% missing
* 20% missing
* 30% missing

and different missing-variable combinations.

### C. Checkpoint consistency

Ensure that:

* the trained checkpoint actually exists
* the metadata corresponds to the checkpoint
* the architecture used during inference matches the architecture used during training
* normalization/scaling parameters are preserved
* feature ordering is identical
* model loading works from a clean process.

Do not claim that a model is trained merely because training code exists.

### D. PINN evaluation

After training, calculate actual:

* MAE
* RMSE
* physics residual
* reconstruction error

for the relevant telemetry variables.

Evaluate multiple missing-data percentages and missing-gap patterns.

Never fabricate or hardcode these values.

==================================================
PHASE 4 — ADD PHASE-RELATIVE ANOMALY DETECTION
==============================================

Keep the existing anomaly detection.

Add an additional statistical layer that evaluates a telemetry value relative to the expected behavior of its current flight phase.

Use the existing flight phases.

For each relevant:

* phase
* sensor/parameter

calculate appropriate baseline statistics from legitimate reference data.

Possible statistics:

* mean
* standard deviation
* median
* MAD
* robust range

Use a statistically appropriate method based on the available data.

Calculate a phase-relative deviation/z-score where appropriate.

Example concept:

Observed P_chamber
vs
expected P_chamber during the same flight phase.

A value can therefore be flagged as statistically abnormal even if it has not crossed an absolute safety threshold.

IMPORTANT:

* Do not invent reference distributions.
* Clearly distinguish reference-derived statistics from hard safety thresholds.
* Do not train on test data when evaluating the detector.

==================================================
PHASE 5 — ADD PARAMETRIC SCATTER ANALYSIS
=========================================

Add a new interactive visualization.

Allow the user to select:

X-axis parameter
Y-axis parameter

Examples:

* P_chamber vs F_thrust
* m_ox vs m_fuel
* T_chamber vs P_chamber

Display:

* normal points
* warning/anomalous points
* relevant phase/filter if applicable.

Use actual telemetry data.

Allow clicking an anomalous point to open the corresponding anomaly deep-dive.

Do not create fake clusters or fake anomaly points.

==================================================
PHASE 6 — BUILD ANOMALY / FAULT DEEP-DIVE
=========================================

This is a major new feature.

When the user clicks an anomaly, open a detailed investigation view.

Display:

### Basic information

* anomaly ID
* parameter/sensor
* subsystem
* timestamp
* flight phase
* anomaly type
* severity
* confidence, only if actually calculated

### Observed values

* observed value
* expected/reference value, if available
* absolute deviation
* percentage deviation
* phase-relative deviation

### Timeline

Show the parameter before, during, and after the anomaly.

Clearly mark:

* anomaly start
* peak/worst point
* recovery/end, if applicable.

### Related parameters

Show relevant related telemetry values.

Examples:

* P_chamber
* m_ox
* m_fuel
* F_thrust
* N_pump

Only display relationships that are actually calculated.

### Physics validation

Show:

* expected value
* observed value
* residual
* physics status

where a valid physics relationship exists.

### ML evidence

If Isolation Forest or another model contributed to the detection, display its actual score or normalized interpretation.

Do not invent a score.

### Recovery

If the anomaly involves missing/corrupted telemetry, show:

* PINN reconstruction
* physics reconstruction
* EKF reconstruction
* interpolation result

where available.

Show actual residual/error metrics.

### Explanation

Generate an evidence-based explanation from actual calculated information.

Example structure:

"Flagged because the parameter deviated Xσ from the phase reference, showed Y% temporal drift, and produced a physics residual of Z."

Do not use an LLM or generic text generator to invent a root cause.

==================================================
PHASE 7 — ADD ANOMALY ATTRIBUTION
=================================

Create an engineering-oriented explanation panel.

Possible contributors:

* phase-relative deviation
* temporal deviation
* physics residual
* Isolation Forest anomaly score
* threshold violation
* related-sensor inconsistency

Display only contributors that are actually available.

Use normalized values only when the normalization method is mathematically valid.

Example:

WHY WAS THIS FLAGGED?

Phase deviation      ███████
Physics residual     █████
Temporal drift       ████
ML anomaly score     ███

The visualization must be derived from actual calculations.

Do NOT claim causal root cause unless the system can establish it.

Use terminology such as:

* evidence
* contributing signal
* consistency check
* possible cause

when causality cannot be proven.

==================================================
PHASE 8 — OBSERVED VS EXPECTED TRAJECTORY
=========================================

For important anomaly investigations, show:

* observed telemetry
* expected/reference trajectory
* safety threshold where applicable.

Do not confuse:

* statistical reference
* physics prediction
* safety threshold
* ML prediction.

Label each line clearly.

==================================================
PHASE 9 — PREDICTIVE DRIFT MONITOR
==================================

Add predictive drift analysis.

For a detected trend:

1. estimate the current trend using actual data
2. determine whether the trend is statistically meaningful
3. project the trend only within a defensible prediction horizon
4. determine whether/when a threshold may be crossed.

Display:

* current value
* trend/slope
* threshold
* estimated crossing time, if calculable
* uncertainty/error information if available.

Do not display a predicted crossing time when the model/data is insufficient.

Do not claim certainty.

==================================================
PHASE 10 — MISSION WHAT-IF SIMULATOR
====================================

Add a controlled simulation feature.

Allow the user to modify a telemetry parameter or relevant input.

Example:

m_ox:
-5%

Then calculate downstream effects using the project's actual physics/model equations.

Display:

* affected parameters
* health impact
* physics consistency
* anomaly impact

IMPORTANT:

Do not simply multiply values using arbitrary percentages.

Use the project's actual validated equations/model.

Clearly label this as a simulation, not real telemetry.

Do not alter the original telemetry dataset.

==================================================
PHASE 11 — IMPROVE LIVE TELEMETRY
=================================

Keep the current live/WebSocket implementation.

Add:

* anomaly markers
* current expected range
* phase-relative status
* threshold markers where applicable
* clickable anomaly markers.

Clicking an anomaly marker should open its Deep-Dive.

Do not break live updates.

==================================================
PHASE 12 — IMPROVE CORRELATION / PHYSICS VIEW
=============================================

Keep the existing correlation/physics matrix.

Make relevant cells interactive where practical.

Clicking a relationship should show:

* parameter pair
* measured relationship
* expected relationship, if defined
* current deviation
* physics consistency status.

Do not call statistical correlation a physical law.

Clearly distinguish:

correlation
vs
physics equation
vs
model-derived relationship.

==================================================
PHASE 13 — IMPROVE PINN RECOVERY VISUALIZATION
==============================================

Create a clear recovery view.

For missing telemetry:

show:

Observed telemetry
Reconstructed telemetry
Missing region
PINN prediction
Alternative recovery methods

Where possible show:

* PINN result
* EKF result
* physics result
* interpolation result
* reconstruction error
* physics residual.

Do not artificially select PINN as the winner.

The system should objectively display the available results.

==================================================
PHASE 14 — RECOVERY COMPARISON
==============================

Create a comparison table:

Method | Prediction | Error | Physics Residual

Methods:

* PINN
* Physics
* EKF
* Interpolation

Only show methods that actually ran.

Use real computed values.

==================================================
PHASE 15 — DEDICATED EVALUATION SUMMARY
=======================================

Add a final Evaluation Summary screen.

Include:

### Mission

* telemetry records
* sensors
* flight phases

### Anomalies

* total
* GAP
* SPIKE
* DRIFT
* STUCK
* NOISE

### Recovery

* PINN
* physics
* EKF
* interpolation

### Model

* MAE
* RMSE
* reconstruction metrics

### Physics

* physics residuals
* physics compliance statistics

### Health

* overall health
* subsystem health
* warning/critical counts

Every value must be dynamically calculated.

No hardcoded numbers.

==================================================
PHASE 16 — REPORT IMPROVEMENT
=============================

Preserve existing report generation.

Add:

1. Mission summary
2. Flight-phase summary
3. Anomaly summary
4. Individual anomaly details
5. Phase-relative statistics
6. Physics violations
7. Telemetry recovery
8. PINN evaluation
9. Predictive drift results
10. Final health assessment

Ensure JSON and PDF/exported reports use the same underlying data as the dashboard.

Do not create separate hardcoded report values.

==================================================
PHASE 17 — DATA INTEGRITY
=========================

Very important:

Remove or isolate fake/mock analytical data from the final production/demo path.

If synthetic telemetry generation is intentionally retained as a simulator/demo mode, clearly label it:

"Synthetic / Simulation Data"

Do not present synthetic values as real measurements.

Do not use mock model predictions.

Do not use fake accuracy numbers.

Do not use fake confidence values.

==================================================
PHASE 18 — TEST EVERYTHING
==========================

After implementation:

### Backend

Run all existing tests.

Then add tests for:

* phase-relative anomaly detection
* scatter data generation
* anomaly deep-dive API
* anomaly explanation calculations
* physics residual calculations
* predictive drift
* recovery comparison
* PINN checkpoint loading
* PINN missing-data masks
* PINN physics loss
* report consistency.

### Frontend

Verify:

* dashboard loads
* telemetry works
* live updates work
* anomaly clicking works
* Deep-Dive opens
* charts render
* filters work
* recovery view works
* simulator works
* reports work
* responsive layout works.

### End-to-end

Test:

CSV
→ telemetry
→ phase detection
→ anomaly detection
→ anomaly Deep-Dive
→ physics validation
→ recovery
→ health score
→ report.

==================================================
PHASE 19 — NO REGRESSIONS
=========================

Before finishing:

1. Run the entire existing test suite.
2. Confirm all previous tests pass.
3. Confirm all existing APIs still work.
4. Confirm all existing pages/routes still work.
5. Confirm existing dashboard functionality is preserved.
6. Confirm existing telemetry processing is unchanged unless explicitly improved.
7. Confirm no existing feature was silently removed.

If something breaks, fix the regression before considering the task complete.

==================================================
FINAL REQUIREMENT
=================

At the end, provide a concise implementation report containing:

1. Files changed
2. Files added
3. Existing features preserved
4. Bugs fixed
5. New features added
6. PINN training/evaluation status
7. Tests run
8. Test results
9. Any remaining limitations
10. Any feature that could not be implemented because the available dataset/model does not support it.

CRITICAL:

DO NOT fabricate results.

DO NOT claim an ML model was trained unless a real training run completed.

DO NOT claim an accuracy/MAE/RMSE value unless it was actually calculated.

DO NOT claim root cause when the system only has correlation/evidence.

DO NOT replace real calculations with mock values.

DO NOT remove existing working functionality.

The final result should be a technically defensible AERIS system with this workflow:

TELEMETRY
→ FLIGHT PHASE
→ MULTI-METHOD ANOMALY DETECTION
→ PHASE-RELATIVE ANALYSIS
→ ANOMALY DEEP-DIVE
→ EVIDENCE / PHYSICS / ML EXPLANATION
→ PREDICTIVE DRIFT
→ TELEMETRY RECOVERY
→ PINN / EKF / PHYSICS VALIDATION
→ HEALTH ASSESSMENT
→ EVALUATION SUMMARY
→ REPORT
