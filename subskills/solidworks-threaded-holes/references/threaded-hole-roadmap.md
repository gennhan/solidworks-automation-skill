# SolidWorks Threaded Hole Expansion Roadmap

This roadmap separates "worth expanding" from "stably supported". Items that have not passed their acceptance gates must never be listed under `verified` capability claims.

## P0: Core Correctness (Completed)

- Switched through tap-drill holes to genuine `Through All`.
- Added validation for finite numbers, positive values, depth chains, hole-position margins, and tap-drill diameter strictly less than nominal diameter.
- Enabled genuine internal `ThreadFeatureData` using `Metric Tap` + selection mark `1`.
- Added tolerance class properties, right/left-hand support, and non-table ISO metric specs (requiring an explicit tap-drill diameter).
- Read back the FeatureManager Design Tree after rebuild, separating API attempts from final persistence evidence.
- Preserved true pitch on the 3D helix and separated the evidence preview from clean delivery previews.

## P1: Native Hole Semantics & Existing Parts (Highest Priority)

### 1. `HoleWizard5` / `WizardHoleFeatureData2`

Goal: When the user requires standard Hole Callouts, hole tables, or database-driven thread specifications, prioritize creating native Hole Wizard tapped holes instead of a tap-drill Cut + `Thread` pair.

Required work:

- Wrap `HoleWizard5` and `IWizardHoleFeatureData2` with explicit ISO/DIN/GB/ANSI standards, fastener types, sizes, hole depth, tap depth, tap-drill diameter, and tolerance class.
- Probe local Hole Wizard / Toolbox database paths and available sizes rather than guessing enums or size strings.
- Read back `ThreadDepth`, `TapDrillDiameter`, `ThreadClass`, and hole center points from saved feature data.
- Build a version matrix covering SW2024/SW2026 and both Chinese and English UI locales.

Acceptance gate: At least 3 consecutive passes each for blind and through-holes; standard, size, tap-drill diameter, thread depth, and hole positions read back accurately after reopening the `SLDPRT`; generated Engineering Drawing Hole Callouts match the model.

### 2. Editing Existing Parts & Multi-Hole Patterns

Goal: Expand the template from "new rectangular coupon" to semantic entity selection and multi-hole creation on existing `SLDPRT` files.

Required work:

- Select target faces via `sw_entity_reference.py` using face normals, bounds, coordinate systems, and persistent references instead of "Front/Top/Right plane + fixed offset".
- Support explicit hole coordinate lists, linear/circular patterns, multi-size hole groups, and per-hole evidence.
- Detect intersections, edge-distance violations, thin walls, and conflicts with existing features before modifying; partial failures must never leave a half-built model.

Acceptance gate: Cover planar, side, angled, and multi-body parts; cross-verify every hole's position, axis, diameter, and depth against both B-Rep geometry and the FeatureManager tree.

## P2: Data-Driven Thread Standards

Goal: Replace the small inline coarse-pitch dictionary with versioned data tables.

- ISO metric coarse/fine pitches, separating cut-tap and form-tap drill diameters.
- UNC/UNF/UNEF, NPT/NPTF, BSPP/BSPT; imperial and pipe threads must never reuse the `Metric Tap` profile.
- Tolerance classes, handedness, multi-start threads, workpiece material / percent thread engagement, and tap-drill selection sources.
- Tag every table entry with standard edition, source, units, applicability scope, and a "manual confirmation required" flag.

Acceptance gate: Schema validation, boundary tests, unit-conversion tests, and spot checks against authoritative reference tables all pass.

## P3: Manufacturing Realism

- Standard drill-point angles for blind holes, distinguishing "full cylindrical depth" from "total depth to drill point".
- Effective full-thread depth, lead-in chamfer/threads, incomplete runout threads, bottom relief, and chip clearance.
- Determine hole-mouth Chamfer from nominal diameter, standard, and shop process instead of generalizing a single M6 rule of thumb.
- Optional explicit swept thread forms reserved strictly for 3D printing, rendering, or explicit customer requests, gated by independent checks for performance, self-intersection, file size, and STEP reopen.

Acceptance gate: Parameter evidence matches measured B-Rep depths; flat-bottom holes are never claimed as real drilled holes; every manufacturing assumption is recorded in the delivery report.

## P4: Engineering Drawings, PMI & CAM Evidence

- Automatically generate and read back GB/ISO-style threaded-hole callouts containing size, tolerance class, depth, quantity, and locating dimensions.
- Integrate with `solidworks-engineering-drawing` hole tables / hole-slot schedules, ensuring three-way consistency across model properties, drawing text, and B-Rep evidence.
- Perform separate capability probing for STEP AP242/PMI and CAM feature recognition; the presence of thread geometry in a plain STEP file does not imply CAM will automatically recognize tapping operations.

Acceptance gate: Hole-callout contents read back in structured form, and both keywords and dimensions are verified on actual PDF/Drawing deliverables—never substituting "API call succeeded" for callout readability.
