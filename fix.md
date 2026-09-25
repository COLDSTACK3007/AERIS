# AERIS — COMPLETE COMPUTATION, PHYSICS & LOGIC FIX

You are working on an existing project called **AERIS — Automated Evaluation, Anomaly Detection & Re-Imputation System for Launch Vehicle Flight Telemetry**.

The project is already built and functional.

## CRITICAL INSTRUCTION

**DO NOT redesign the frontend.**

**DO NOT change the existing UI layout, styling, animations, routes, dashboard structure, API structure, or user experience unless absolutely required for a bug fix.**

**DO NOT remove existing features.**

**DO NOT replace working functionality with a completely different implementation.**

Your task is to **audit and fix the computational, mathematical, physics, anomaly-detection, health-scoring, imputation, and verification logic of the existing project.**

The objective is:

> Make the generated telemetry internally consistent, make anomaly detection detect the faults that are actually injected, eliminate self-generated false anomalies, make health scores meaningful, make physics-compliance calculations mathematically defensible, and make the automated tests genuinely verify correctness.

---

# 1. FIRST: AUDIT THE EXISTING CODE

Before modifying anything:

1. Inspect the entire backend.
2. Inspect:

   * synthetic telemetry generator
   * telemetry ingestion
   * anomaly detector
   * physics engine
   * alert manager
   * health calculation
   * imputer
   * PINN implementation
   * EKF implementation
   * API routes
   * verification scripts
   * unit tests
3. Identify all existing formulas, constants, thresholds, assumptions, and units.
4. Do not blindly trust the documentation.
5. Do not blindly trust the tests.
6. The actual implementation and physically consistent behavior are the source of truth.

Create a temporary internal audit if necessary, but do not modify the UI.

---

# 2. FIX THE TELEMETRY / PHYSICS CONSISTENCY

The synthetic telemetry generator currently uses approximately:

```text
m_ox = 240 kg/s
m_fuel = 96 kg/s
Isp = 295 s
g0 = 9.81 m/s²
```

Total propellant flow:

```text
m_total = m_ox + m_fuel
```

Therefore:

```text
m_total = 336 kg/s
```

Thrust should be:

```text
F_thrust_N = m_total * Isp * g0
F_thrust_kN = F_thrust_N / 1000
```

which gives approximately:

```text
972.3 kN
```

The existing system has a configured thrust maximum around 800 kN while simultaneously generating normal thrust around 972 kN.

THIS MUST BE FIXED.

Choose one internally consistent model.

Prefer preserving the current thrust-generation equation and update the metadata/ranges/thresholds so approximately 972 kN is a valid nominal Stage-1 value.

Do not simply suppress the anomaly detector.

The detector must correctly understand that this value is nominal.

---

# 3. MAKE THRESHOLDS FLIGHT-PHASE AWARE

Do NOT use one universal threshold for all flight phases when the expected physical behavior changes significantly during:

```text
PRE_LAUNCH
LIFTOFF
MAX_Q
STAGE_1_FLIGHT
STAGE_SEPARATION
STAGE_2_FLIGHT
COAST_ORBIT
```

The documented phase boundaries are:

```text
PRE_LAUNCH       T <= 10 s
LIFTOFF          10 < T <= 60 s
MAX_Q            60 < T <= 90 s
STAGE_1_FLIGHT   90 < T <= 150 s
STAGE_SEPARATION 150 < T <= 160 s
STAGE_2_FLIGHT   160 < T <= 450 s
COAST_ORBIT      T > 450 s
```

Preserve these boundaries unless there is a strong implementation reason to change them.

Instead, make expected telemetry behavior phase-dependent.

For example:

* PRE_LAUNCH should not be treated like powered flight.
* Stage transitions naturally produce rapid changes.
* Stage-2 thrust is different from Stage-1 thrust.
* COAST should not be judged using powered-flight thrust thresholds.

---

# 4. FIX PRE-LAUNCH TELEMETRY

The current synthetic generator gradually increases propellant flow during the first 10 seconds.

This conflicts with the definition of:

```text
PRE_LAUNCH
```

and causes the anomaly detector to classify normal generated values as physics violations.

Choose ONE consistent interpretation.

Preferred solution:

If:

```text
T <= 10 s
```

is genuinely PRE_LAUNCH, then:

```text
m_ox ≈ 0
m_fuel ≈ 0
F_thrust ≈ 0
```

with only realistic startup noise.

Then ignition/liftoff should begin after the PRE_LAUNCH boundary.

Do not make the detector simply ignore these values.

The telemetry generator and detector must agree.

---

# 5. FIX CHAMBER TEMPERATURE LIMITS

The generator currently produces approximately:

```text
300 K ± noise
```

during engine-off periods.

If noise can produce:

```text
298 K
299 K
```

then a hard minimum:

```text
T_chamber >= 300 K
```

will create false critical anomalies.

Fix this properly.

Options:

1. Change the configured minimum to accommodate expected sensor noise.
2. Use phase-dependent limits.
3. Use a physically meaningful engine-off temperature model.

Preferred approach:

Use phase-dependent expectations rather than a universal hard minimum.

Do NOT merely disable temperature anomaly detection.

---

# 6. FIX STUCK SENSOR DETECTION

The synthetic generator intentionally injects a stuck battery sensor:

```text
v_batt = 27.4 V
```

for approximately:

```text
180–210 seconds
```

The anomaly detector must actually monitor `v_batt` for STUCK behavior.

Current issue:

The stuck-detection parameter list does not include all relevant telemetry parameters.

Fix this by defining a proper parameter capability map.

For example:

```python
DETECT_STUCK = {
    "v_batt": True,
    "i_bus": True,
    "P_chamber": True,
    ...
}
```

Do not hard-code an incomplete list scattered across the code.

The final detector must detect the intentionally injected `v_batt` stuck event.

---

# 7. FIX DRIFT DETECTION

The synthetic generator intentionally injects drift into:

```text
P_tank_lox
```

approximately during:

```text
200–240 seconds
```

The drift detector must monitor that parameter.

Do NOT classify normal stage transitions as sensor drift.

The current implementation appears to detect drift primarily on parameters such as:

```text
P_chamber
T_chamber
m_ox
m_fuel
F_thrust
N_pump
```

while the intentionally injected drift is on:

```text
P_tank_lox
```

Fix the detector.

Use a robust drift method.

Possible approach:

1. Establish a baseline for the current flight phase.
2. Calculate deviation from the expected baseline.
3. Apply smoothing/robust statistics.
4. Require sustained deviation for a defined duration.
5. Compare against a meaningful drift threshold.
6. Avoid classifying stage transitions as drift.

A stage transition is a legitimate system-level change.

A drift should represent a sensor gradually departing from its expected behavior while the underlying physical condition remains consistent.

---

# 8. FIX SPIKE DETECTION

The existing spike detector uses statistical methods such as rolling z-score.

Preserve the useful statistical detection but make it phase-aware.

Do not classify every legitimate stage transition as a spike.

A spike should consider:

```text
rate of change
+
rolling deviation
+
physical range
+
flight phase
+
expected parameter behavior
```

Use both statistical and physical reasoning.

For example:

```text
stage transition
```

may produce a large Δx but should not automatically become a sensor fault.

A genuine isolated sensor spike should.

---

# 9. FIX NOISE DETECTION

Noise detection should distinguish:

```text
normal sensor noise
```

from:

```text
abnormally high variance
```

Use rolling standard deviation/variance.

But thresholds must be parameter-specific and preferably phase-specific.

Do not compare the raw standard deviation of:

```text
temperature
pressure
vibration
voltage
```

using the same threshold.

Each parameter has different units and normal variability.

---

# 10. FIX PHYSICS VIOLATION DETECTION

Physics violations should be based on relationships between variables.

Examples:

### Thrust consistency

Expected:

```text
F_expected =
(m_ox + m_fuel) * Isp * g0 / 1000
```

Then:

```text
thrust_residual =
abs(F_measured - F_expected)
```

Use a configurable tolerance.

Do NOT simply classify based on an arbitrary absolute thrust threshold.

---

### Chamber pressure consistency

Current simplified relationship:

```text
P_chamber = k * (m_ox + m_fuel)
```

Preserve this if it is intended as the project's simplified surrogate model.

But DO NOT describe it as a fundamental isentropic equation.

Document it as:

```text
simplified empirical/physics-inspired relationship
```

unless a proper thermodynamic derivation is implemented.

---

### Mixture ratio

Calculate:

```text
O_F_ratio = m_ox / m_fuel
```

Handle:

```text
m_fuel == 0
```

safely.

Do not generate division-by-zero or infinity values.

The acceptable range should be configurable and phase/engine-specific where appropriate.

---

# 11. FIX PHYSICS COMPLIANCE SCORE

THIS IS IMPORTANT.

Do not calculate physics compliance simply from:

```text
100 - anomaly_count / telemetry_count * 100
```

That is not a true physics-compliance measurement.

Instead calculate physics compliance from actual physics residuals.

For each applicable physical relationship calculate:

```text
residual
```

For example:

```text
R_thrust =
abs(F_measured - F_expected)

R_pressure =
abs(P_measured - P_expected)
```

Normalize residuals using defined tolerances.

Example conceptual structure:

```text
normalized_error =
min(abs(residual) / tolerance, 1.0)
```

Then calculate weighted compliance:

```text
physics_compliance =
100 * (1 - weighted_normalized_error)
```

The exact implementation may be improved, but it MUST:

1. Use actual physics relationships.
2. Use explicit tolerances.
3. Be dimensionally sensible.
4. Not mix kN, MPa, K, kg/s directly.
5. Be explainable to a technical judge.

Report separate metrics where possible:

```text
Thrust Physics Compliance
Pressure Physics Compliance
Mass-Flow Consistency
Overall Physics Compliance
```

---

# 12. FIX HEALTH SCORE

The current health score is overly dependent on the number of anomaly records.

This creates situations where duplicate/related anomaly events can push:

```text
Health = 0%
```

even when the underlying physical situation is not catastrophic.

Do not simply remove the health score.

Improve it.

Use:

```text
severity
+
duration
+
confidence
+
subsystem
+
physical significance
```

Avoid counting multiple records generated by the same underlying event as completely independent penalties.

For example:

```text
One sensor stuck for 30 seconds
```

should not become:

```text
300 independent critical faults
```

if there are 300 samples.

Group related anomaly samples into an event.

Then calculate health from events.

---

# 13. MAKE HEALTH SCORE DOCUMENTATION MATCH IMPLEMENTATION

The documentation currently says approximately:

```text
CRITICAL = -8
WARNING = -3.5
INFO = -1
```

while the implementation uses different values.

Choose ONE authoritative formula.

Then update:

```text
backend code
tests
documentation
API output
frontend labels
reports
```

so all of them agree.

Do not leave conflicting formulas in the repository.

---

# 14. FIX ANOMALY EVENT GROUPING

A sensor gap or continuous fault should be represented as an event.

For example:

```text
NaN
NaN
NaN
NaN
NaN
```

should not become:

```text
5 independent critical events
```

It should become:

```text
1 GAP event
start_time
end_time
duration
parameter
severity
confidence
```

Apply similar grouping to:

* STUCK
* DRIFT
* NOISE
* sustained SPIKE conditions

This will make health scoring and reports much more meaningful.

---

# 15. FIX PINN IMPLEMENTATION

IMPORTANT:

Do NOT claim that the current neural network is a trained PINN unless trained weights are actually available.

Inspect the existing PINN implementation.

If there is no trained checkpoint:

Implement a proper training pipeline:

```text
training telemetry
       ↓
normalization
       ↓
neural network
       ↓
data loss
       +
physics loss
       ↓
backpropagation
       ↓
trained model
       ↓
validation
       ↓
checkpoint
```

The total loss should follow:

```text
L_total =
L_data +
lambda_physics * L_physics
```

The physics loss should actually penalize violations of the implemented physical relationships.

After training:

```text
save checkpoint
```

During inference:

```text
load checkpoint
model.eval()
```

Do not silently use random initialized weights.

---

# 16. IF A FULL PINN TRAINING PIPELINE IS NOT PRACTICAL

If training a proper PINN would take too much time for this project, do NOT fake it.

Instead:

1. Keep the neural architecture.
2. Clearly identify it as a PINN prototype.
3. Use deterministic physics-based recovery for parameters where equations are reliable.
4. Use spline/EKF for appropriate gaps.
5. Do not present random neural-network predictions as scientifically validated recovery.

The system should prefer reliable deterministic physics over an untrained neural network.

---

# 17. FIX IMPUTATION STRATEGY

Use an explicit strategy based on gap length.

Suggested:

```text
Short gap
→ interpolation

Medium gap
→ physics-based reconstruction where equations are available

Long gap
→ trained PINN + dynamic state estimator
```

Every imputed value should contain metadata:

```text
imputation_method
confidence
physics_residual
original_missing = true
```

The UI/report should be able to explain:

```text
This value was reconstructed using physics
```

or:

```text
This value was reconstructed using PINN
```

rather than presenting all recovered values as if they were original telemetry.

---

# 18. FIX EKF

The EKF must use a meaningful state model.

Do not assume zero velocity for all telemetry dynamics if that causes unrealistic flat predictions.

At minimum:

```text
state
+
state transition model
+
process noise
+
measurement model
+
measurement noise
```

should be explicitly defined.

If the EKF is only being used as a fallback estimator, document its limitations.

---

# 19. FIX THE "PHYSICS CONSERVATION PASS"

There is currently a function whose behavior is effectively similar to:

```text
value = max(0, value)
```

This is not true conservation enforcement.

Either:

### Option A

Rename it to something accurate, such as:

```text
physical_bounds_pass
```

OR

### Option B

Implement actual conservation constraints.

Do not use the term "conservation" unless the code actually enforces conservation equations.

---

# 20. FIX PHYSICS RESIDUAL REPORTING

Do NOT calculate one raw average across different physical units.

Bad:

```text
average residual = 2.1
```

if the residuals include:

```text
kN
MPa
K
kg/s
RPM
```

Instead report:

```text
Thrust residual:      X kN
Pressure residual:    Y MPa
Mass-flow residual:   Z kg/s
Temperature residual: W K
```

Optionally calculate normalized residuals:

```text
normalized residual =
abs(residual) / acceptable_tolerance
```

Then an overall normalized physics error can be reported.

---

# 21. FIX VERIFICATION TESTS

The existing verification scripts are too permissive.

Do not simply print:

```text
PASS
```

because a calculation executed.

Every verification should have an actual assertion.

Example:

```python
assert mean_thrust_error < THRUST_TOLERANCE
```

instead of:

```python
print("PASS")
```

Define scientifically/engineering-motivated tolerances.

Examples:

```text
THRUST_TOLERANCE
PRESSURE_TOLERANCE
MASS_FLOW_TOLERANCE
TEMPERATURE_TOLERANCE
```

Make them explicit and configurable.

---

# 22. FIX FLIGHT-PHASE TEST

There is a test that expects approximately:

```text
5 sec → LIFTOFF
```

while the implementation/documentation defines:

```text
T <= 10 sec → PRE_LAUNCH
```

Do not change the phase logic merely to satisfy the test.

Instead determine the intended phase definition.

If the documented definition is authoritative:

```text
5 sec → PRE_LAUNCH
```

then fix the test.

The test suite must reflect the actual intended specification.

---

# 23. FIX SYNTHETIC-DATA TESTS

The test suite must verify that every intentionally injected anomaly is actually detected.

Create explicit tests for:

```text
GAP
SPIKE
STUCK
DRIFT
NOISE
```

For each injected fault:

```text
generator creates fault
        ↓
detector detects fault
        ↓
correct parameter
        ↓
correct time interval
        ↓
correct anomaly type
        ↓
reasonable severity
```

Example:

```text
Injected:
v_batt stuck at 27.4 V
180–210 s

Expected:
STUCK
parameter = v_batt
start ≈ 180 s
end ≈ 210 s
```

Do this for every injected anomaly.

---

# 24. ADD NEGATIVE TESTS

The detector must NOT flag normal behavior.

Create tests such as:

```text
normal Stage-1 thrust
→ no anomaly

normal Stage-2 thrust
→ no anomaly

stage transition
→ no DRIFT

normal sensor noise
→ no CRITICAL fault

normal engine startup
→ no false physics violation
```

This is extremely important.

A good anomaly detector is not just:

> "Can it detect faults?"

It must also answer:

> "Can it avoid flagging normal behavior as faults?"

---

# 25. ADD KNOWN-VALUE MATHEMATICAL TESTS

Create deterministic tests.

Example:

```python
m_ox = 240
m_fuel = 96
isp = 295
g0 = 9.81

expected = ((m_ox + m_fuel) * isp * g0) / 1000

assert abs(expected - 972.3) < tolerance
```

Similarly test:

```text
O/F ratio
chamber pressure
thrust
health calculation
physics residual
```

This makes the numerical layer independently verifiable.

---

# 26. TEST UNITS EVERYWHERE

Audit every calculation for unit consistency.

Explicitly document:

```text
Pressure → MPa
Thrust → kN
Mass flow → kg/s
Temperature → K
Acceleration → g
RPM → RPM
Voltage → V
Current → A
Time → s
```

Do not accidentally compare:

```text
N
```

against:

```text
kN
```

or:

```text
Pa
```

against:

```text
MPa
```

without conversion.

---

# 27. FIX API OUTPUTS

The backend API should return transparent metadata.

For anomaly:

```json
{
  "parameter": "...",
  "type": "...",
  "severity": "...",
  "start_time": 0,
  "end_time": 0,
  "duration": 0,
  "confidence": 0,
  "reason": "...",
  "detector": "..."
}
```

For imputation:

```json
{
  "parameter": "...",
  "timestamp": 0,
  "value": 0,
  "method": "physics",
  "confidence": 0,
  "physics_residual": 0
}
```

For physics:

```json
{
  "relationship": "thrust",
  "measured": 0,
  "expected": 0,
  "residual": 0,
  "tolerance": 0,
  "compliant": true
}
```

This will make the system much easier to explain.

---

# 28. DO NOT HIDE FAILURES

Do NOT modify tests just to make them pass.

Do NOT:

```text
remove failing test
```

Do NOT:

```text
increase thresholds until everything passes
```

Do NOT:

```text
suppress anomalies
```

Do NOT:

```text
hard-code expected output
```

Do NOT:

```text
fake PINN accuracy
```

The objective is genuine correctness.

---

# 29. RUN ALL TESTS AFTER FIXING

Run:

```bash
pytest
```

and:

```bash
python test_all.py
```

and all existing computation/verification scripts.

Also perform:

```text
fresh synthetic dataset
→ ingest
→ anomaly detection
→ health calculation
→ physics compliance
→ imputation
→ report
```

multiple times.

Because the synthetic data contains randomness, do not validate only one run.

Use a fixed random seed for deterministic unit tests.

---

# 30. CREATE A FINAL COMPUTATION VALIDATION REPORT

After fixing the code, generate a machine-readable and human-readable validation report.

Include:

```text
Telemetry samples
Anomaly events
GAP events
SPIKE events
STUCK events
DRIFT events
NOISE events

Expected injected anomalies
Detected injected anomalies
False positives
False negatives

Mean thrust residual
Maximum thrust residual
Mean chamber-pressure residual
Maximum chamber-pressure residual

Imputation count
Imputation method distribution
Normalized physics residual

Health score
Physics compliance score

Unit-test results
E2E test results
```

---

# 31. FINAL ACCEPTANCE CRITERIA

Do not consider the task complete until:

### Data consistency

* Generated telemetry is physically consistent with its own equations.
* Metadata ranges contain normal generated values.
* Units are consistent.

### Anomaly detection

* GAP is detected.
* SPIKE is detected.
* STUCK is detected.
* DRIFT is detected.
* NOISE is detected.
* False positives are minimized.
* Stage transitions are not incorrectly classified as sensor faults.

### Physics

* Thrust equation is correct.
* Chamber-pressure relationship is internally consistent.
* O/F ratio is safe.
* Physics residuals are meaningful.
* Physics compliance uses physics residuals.

### Health

* Health score does not collapse because of duplicate samples.
* Severity is meaningful.
* Health calculation matches documentation.

### PINN

* If described as trained, actual trained weights must exist.
* Physics loss must genuinely participate in training.
* Validation metrics must be reported.
* Otherwise clearly label it as a prototype.

### Imputation

* Short gaps use appropriate interpolation.
* Medium gaps use physics where reliable.
* Long gaps use trained models/estimators where appropriate.
* Every imputed value has a method and confidence.

### Verification

* Tests use real assertions.
* All tests pass.
* Known-value tests pass.
* Positive and negative anomaly tests pass.
* Multiple synthetic runs behave consistently.

---

# 32. IMPORTANT: PRESERVE THE EXISTING FRONTEND

After completing the fixes:

DO NOT redesign:

* dashboard layout
* cards
* navigation
* charts
* colors
* animations
* typography
* responsive layout
* report design

unless a tiny change is necessary to display newly corrected numerical information.

The existing UI should remain visually the same.

Only correct the underlying values and, if needed, add small explanatory labels such as:

```text
Physics Compliance
Health Score
Physics Residual
Imputation Method
Confidence
```

without changing the overall design.

---

# 33. FINAL RESPONSE REQUIRED AFTER IMPLEMENTATION

After making changes, give me a concise technical report containing:

## Files changed

List every modified file.

## Bugs fixed

List every actual logical/computational issue fixed.

## Formula changes

Show:

```text
old formula
→
new formula
```

where applicable.

## Threshold changes

Show the old and new thresholds and explain why.

## Test results

Provide:

```text
pytest:
X passed / X total

test_all.py:
X passed / X total

verification:
PASS / FAIL
```

## Physics validation

Provide actual numerical residuals.

## Anomaly validation

Show:

```text
Injected anomaly
Expected
Detected
Result
```

for:

```text
GAP
SPIKE
STUCK
DRIFT
NOISE
```

## PINN status

Explicitly state:

```text
TRAINED
```

only if a trained checkpoint was actually created and validated.

Otherwise state:

```text
PROTOTYPE / NOT TRAINED
```

## Final assessment

State honestly whether:

```text
all computations are internally consistent
```

and identify any remaining limitations.

Do not claim 100% correctness unless the tests and numerical validation genuinely support that conclusion.

# FINAL RULE

**Correctness is more important than making the dashboard look like everything is working.**

Do not hide anomalies, suppress test failures, manipulate thresholds, or fabricate model accuracy just to obtain green PASS indicators.

The final system should be technically defensible if an SIH judge asks:

> "How exactly did you calculate this number?"

and:

> "How did you verify that number is correct?"

Every important output must have a traceable calculation, physical assumption, tolerance, and verification method.
S