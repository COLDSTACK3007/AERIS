AERIS — PRODUCTION-GRADE UI/UX OVERHAUL
============================================================

You are working on the EXISTING AERIS project.

The current functionality is already implemented. The current problem is primarily VISUAL DESIGN, INFORMATION HIERARCHY, SPACING, COMPONENT QUALITY, AND PROFESSIONAL POLISH.

IMPORTANT:
- DO NOT rebuild the application.
- DO NOT remove existing functionality.
- DO NOT change backend logic.
- DO NOT change APIs.
- DO NOT change telemetry calculations.
- DO NOT change anomaly detection.
- DO NOT change PINN/ML logic.
- DO NOT change physics calculations.
- DO NOT replace working charts with fake/demo charts.
- Do not introduce fake data.
- Do not hardcode analytical results.
- Preserve all current routes and interactions.
- Preserve all existing functionality.
- Only redesign the presentation layer and make minimal frontend changes where required for better interaction.

The goal is to make AERIS look like a REAL production aerospace telemetry and anomaly-analysis platform, not a student dashboard.

============================================================
1. DESIGN DIRECTION
============================================================

Use the visual language of:

- aerospace mission control
- flight telemetry systems
- professional engineering software
- high-end observability platforms
- modern industrial analytics
- scientific visualization

The design should feel:

PRECISE
TECHNICAL
PREMIUM
CALM
DENSE
TRUSTWORTHY
PROFESSIONAL

It should NOT feel:

- like a gaming dashboard
- like a generic SaaS template
- like a university project
- like a crypto dashboard
- like a futuristic neon landing page
- overly glassmorphic
- overly colorful
- cartoonish
- flat
- empty
- excessively rounded

============================================================
2. CORE VISUAL LANGUAGE
============================================================

Use a refined dark aerospace interface.

Primary background:
very dark navy / charcoal.

Panels:
slightly lighter navy/charcoal than the background.

Borders:
subtle, thin, low-contrast borders.

Text:
high-contrast primary text
muted secondary text
clear tertiary labels.

Accent:
use the existing AERIS accent color consistently.

Status colors:
GREEN = healthy
AMBER = warning
RED = critical
BLUE/CYAN = telemetry/information

Do NOT use many unrelated accent colors.

Do NOT make every card glow.

Use glow only for:
- critical alerts
- active states
- important telemetry
- selected data points

============================================================
3. REMOVE THE "FLAT CARD GRID" LOOK
============================================================

The current interface feels like:

[ CARD ] [ CARD ] [ CARD ]
[ CARD ] [ CARD ] [ CARD ]
[ CARD ] [ CARD ] [ CARD ]

Avoid this.

Instead create a visual hierarchy.

Example:

-----------------------------------------------------
MISSION OVERVIEW
Mission status       Health       Phase       Alerts
-----------------------------------------------------

LIVE TELEMETRY
-----------------------------------------------------
Large primary chart
-----------------------------------------------------

SECONDARY ANALYSIS
---------------------------  ------------------------
Anomaly timeline             Subsystem health
---------------------------  ------------------------

DETAILED ANALYSIS
-----------------------------------------------------
Physics / ML / Recovery
-----------------------------------------------------

The page should feel like one coherent control system rather than a collection of unrelated cards.

============================================================
4. IMPROVE THE MAIN DASHBOARD
============================================================

Create a strong hierarchy.

TOP:

AERIS
MISSION TELEMETRY & ANOMALY ANALYSIS

Mission status:
● NOMINAL / WARNING / CRITICAL

Current phase:
MAIN_STAGE

Live indicator:
● LIVE

Then show a compact mission-status strip:

HEALTH
92%

ACTIVE ANOMALIES
3

SENSORS
18

PHASE
MAIN_STAGE

TELEMETRY
LIVE

These should be compact information modules, not giant cards.

============================================================
5. SIDEBAR / NAVIGATION
============================================================

Make the navigation look like a professional engineering console.

Sections:

Overview
Telemetry
Anomalies
Physics
Recovery
Prediction
Evaluation

Use clear icons.

Active navigation item:

- subtle accent background
- thin accent indicator
- high-contrast text
- subtle transition

Do not use huge glowing pills.

Sidebar should feel compact and intentional.

============================================================
6. TYPOGRAPHY
============================================================

Use a professional technical typography hierarchy.

Avoid oversized headings.

Recommended hierarchy:

Page title:
24–30px

Section title:
15–18px

Card/module title:
12–14px

Metric:
22–30px

Body:
13–14px

Metadata:
11–12px

Use:

- uppercase labels sparingly
- letter spacing for technical labels
- tabular/monospace numbers where appropriate

Telemetry numerical values should align cleanly.

Example:

P_CHAMBER
6.24 MPa

not:

P Chamber
6.24

============================================================
7. SPACING SYSTEM
============================================================

Use a consistent spacing system.

Base spacing:
4px / 8px / 12px / 16px / 24px / 32px

Avoid random margins.

Avoid excessive empty space.

Avoid cramped components.

The dashboard should feel dense enough for professional monitoring while remaining readable.

============================================================
8. PANELS
============================================================

Replace generic cards with structured dashboard panels.

Each panel should have:

HEADER
--------------------------------
Title                  Controls
--------------------------------

CONTENT

--------------------------------
Optional footer/status

Use subtle borders.

Use very small corner radii.

Avoid excessive rounded rectangles.

Do not use huge shadows.

============================================================
9. CHART DESIGN
============================================================

Charts are one of the most important parts of AERIS.

They should look like professional telemetry plots.

Improve:

- grid lines
- axis labels
- units
- tick spacing
- tooltip
- legend
- line thickness
- anomaly markers
- threshold lines
- expected bands

Use subtle grid lines.

Avoid bright chart backgrounds.

Charts should blend into the dashboard rather than look like embedded generic charts.

============================================================
10. TELEMETRY CHARTS
============================================================

For live telemetry charts:

Show:

Parameter
Current value
Unit
Status

Example:

P_CHAMBER
6.24 MPa
● NOMINAL

Chart:

Observed ─────────────╱──────

Expected band:
████████████████████████████

Threshold:
----------------------------

Anomaly:
                  ●

Use actual project data.

Do not add decorative lines.

============================================================
11. PARAMETRIC SCATTER
============================================================

Redesign the current Parametric Scatter panel.

It should NOT look like a plain chart inside a rectangle.

Header:

PARAMETRIC RELATIONSHIP

X:
[m_ox]

Y:
[F_thrust]

Phase:
[ALL]

Status:
[ALL]

Then the chart.

Make:

- axes readable
- units visible
- phase legend compact
- anomalies visually distinct
- tooltip professional
- selected point highlighted
- hover crosshair if supported

Use a subtle plot background.

Do not add artificial data.

============================================================
12. ANOMALY TIMELINE
============================================================

Make anomaly visualization feel like a professional incident timeline.

Example:

T+000 ───── T+100 ───── T+200 ───── T+300

                ▲
                │
          P_CHAMBER DRIFT
          CRITICAL

Use severity hierarchy.

Critical:
strong red indicator

Warning:
amber

Informational:
blue/cyan

Normal:
muted

Do not make every anomaly glow.

============================================================
13. ANOMALY DEEP-DIVE
============================================================

The Deep-Dive must feel like an investigation workspace.

Header:

ANOMALY A-0231
P_CHAMBER DRIFT

CRITICAL
T+127.4s
MAIN_STAGE

Then:

------------------------------------------------
OBSERVATION
Observed       6.48 MPa
Expected       6.20 MPa
Deviation      +4.52%
Phase σ        +3.7σ
------------------------------------------------

Then:

TELEMETRY TRAJECTORY

large chart

Then:

EVIDENCE

Phase deviation       +3.7σ
Physics residual      0.42
Temporal drift        HIGH
ML anomaly            HIGH

Then:

RELATED PARAMETERS

P_CHAMBER
F_THRUST
M_OX
M_FUEL

Then:

RECOVERY

PINN
EKF
PHYSICS
INTERPOLATION

Make this look like a real engineering investigation console.

============================================================
14. HEALTH SCORE
============================================================

Do NOT use a giant gaming-style circular gauge.

Instead use:

HEALTH
92

██████████████████░░

Status:
NOMINAL

Then subsystem bars:

PROPULSION       ████████████████ 96
THERMAL          ██████████████░░ 88
POWER            ███████████████ 93
GUIDANCE         ████████████████ 97

This is cleaner and more professional.

============================================================
15. SUBSYSTEM STATUS
============================================================

Create compact status rows:

PROPULSION
● NOMINAL

THERMAL
● WARNING

POWER
● NOMINAL

GUIDANCE
● NOMINAL

Include a small reason for warnings.

Avoid huge cards.

============================================================
16. RECOVERY / PINN UI
============================================================

Make recovery visualization technically impressive.

Show:

TELEMETRY RECOVERY

Parameter:
P_CHAMBER

Observed
----------------╲     ╱----------------

PINN
-----------------╲___╱-----------------

Missing interval:
████████

Then metrics:

PINN
MAE       0.021
RMSE      0.034
Physics residual 0.018

Use actual calculated values.

No fake numbers.

============================================================
17. PHYSICS ANALYSIS
============================================================

Make the physics module feel like an engineering analysis tool.

Use:

PARAMETER RELATIONSHIP

P_CHAMBER ↔ F_THRUST

Expected relationship
Observed relationship
Residual
Status

Use compact engineering notation.

Do not decorate unnecessarily.

============================================================
18. EVALUATION SUMMARY
============================================================

Make the Evaluation Summary feel like a final mission report.

Sections:

MISSION
TELEMETRY
ANOMALIES
PHYSICS
RECOVERY
MODEL PERFORMANCE
SYSTEM HEALTH

Use clean tables and compact metrics.

Avoid giant cards.

============================================================
19. COLOR SYSTEM
============================================================

Use a strict semantic color system.

Background:
dark navy/charcoal

Primary:
near-white

Secondary:
muted blue-gray

Telemetry:
cyan/blue

Healthy:
green

Warning:
amber

Critical:
red

Do not use random colors.

Do not use gradients everywhere.

Do not make all text colorful.

============================================================
20. MICRO-INTERACTIONS
============================================================

Add subtle professional interaction.

Examples:

Hover:
small elevation / border emphasis

Chart point:
highlight + tooltip

Panel:
subtle border transition

Navigation:
smooth active transition

Button:
subtle press state

Anomaly:
subtle pulse only for active critical alerts

Avoid:

- excessive bouncing
- huge scaling
- flashy particle effects
- constant animations
- distracting glow

The interface should feel fast.

============================================================
21. ANIMATION
============================================================

Animations should communicate state, not decorate the UI.

Use short transitions:

150–250ms

Use smooth easing.

Avoid:

- slow page animations
- excessive GSAP effects
- continuous background animation
- parallax everywhere
- animated gradients everywhere

The dashboard should remain responsive at 60 FPS where practical.

============================================================
22. LOADING / EMPTY / ERROR STATES
============================================================

Every major module must have professional states.

Loading:

small spinner/skeleton

Empty:

NO TELEMETRY AVAILABLE

with explanation.

Error:

TELEMETRY STREAM INTERRUPTED

with retry action.

Do not leave blank cards.

============================================================
23. RESPONSIVE DESIGN
============================================================

Desktop:

dense professional control-room layout.

Tablet:

reflow panels intelligently.

Mobile:

stack important information.

Do NOT simply shrink the desktop layout.

Charts must remain readable.

Controls must remain touch-friendly.

Do not break the current desktop functionality.

============================================================
24. ACCESSIBILITY
============================================================

Ensure:

- sufficient text contrast
- visible focus states
- keyboard navigation
- tooltips where icons are ambiguous
- semantic buttons
- readable chart labels

Do not rely only on color to communicate anomaly severity.

Example:

CRITICAL
● red

not just:

● red

============================================================
25. PERFORMANCE
============================================================

The dashboard is a real-time telemetry application.

Do not introduce heavy visual effects that reduce performance.

Avoid:

- excessive blur
- massive box shadows
- unnecessary DOM nodes
- continuous expensive animations
- repeated chart recreation
- unnecessary React re-renders

Optimize charts.

Keep live telemetry smooth.

============================================================
26. RESPONSIBLE DATA VISUALIZATION
============================================================

Never modify the data simply to make the UI look better.

Do NOT:

- add fake noise
- add fake anomalies
- distort axes
- exaggerate deviations
- fabricate expected values
- fabricate model performance

If a relationship is naturally linear, display the true relationship.

Professional engineering software prioritizes truthful visualization over visual drama.

============================================================
27. DESIGN SYSTEM
============================================================

Create/reuse a consistent design system.

Define reusable:

- Panel
- SectionHeader
- Metric
- StatusBadge
- DataTable
- ChartContainer
- Tooltip
- Tabs
- Select
- Button
- Alert
- EmptyState
- LoadingState

Do not implement every panel independently with slightly different styles.

============================================================
28. FINAL VISUAL QUALITY BAR
============================================================

Before finishing, inspect EVERY page.

Ask:

1. Does this look like production software?
2. Is the information hierarchy obvious?
3. Can I understand the mission state within 3 seconds?
4. Can I identify a critical anomaly immediately?
5. Can I investigate an anomaly without searching through the UI?
6. Are charts readable?
7. Are units visible?
8. Are numbers aligned?
9. Is spacing consistent?
10. Are colors semantically meaningful?
11. Is anything unnecessarily glowing?
12. Is anything unnecessarily rounded?
13. Does anything look like a generic template?
14. Does anything look like placeholder/mock UI?
15. Does the UI remain responsive?

============================================================
29. IMPORTANT — DO NOT OVERDESIGN
============================================================

Avoid the common AI-generated dashboard problems:

NO:
- excessive glassmorphism
- excessive gradients
- neon everywhere
- giant rounded cards
- oversized headings
- random decorative icons
- fake futuristic elements
- unnecessary 3D effects
- excessive blur
- excessive shadows
- huge empty spaces
- dashboard "card soup"

AERIS should feel like:

"Aerospace engineering software"

NOT:

"Gaming website pretending to be aerospace software."

============================================================
30. FINAL VALIDATION
============================================================

After redesigning:

- run the existing test suite
- verify dashboard loads
- verify telemetry works
- verify WebSocket/live updates work
- verify charts work
- verify Parametric Scatter works
- verify anomaly interactions work
- verify Deep-Dive works
- verify PINN/recovery views work
- verify reports work
- verify responsive layouts
- verify no backend behavior changed

At the end provide:

1. Files changed
2. Components created/reused
3. Design system changes
4. Pages redesigned
5. Performance improvements
6. Tests passed
7. Any remaining UI limitations

FINAL GOAL:

Transform the current AERIS UI from a flat/basic dashboard into a:

PRODUCTION-GRADE
AEROSPACE TELEMETRY
MISSION ANALYSIS
ANOMALY INVESTIGATION
ENGINEERING PLATFORM

while preserving 100% of the existing functionality and data correctness.