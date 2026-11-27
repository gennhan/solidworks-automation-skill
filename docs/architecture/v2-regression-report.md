# V2 Regression Report & Reliability Baseline

> This document preserves historical Phase 7 / 7.5 records. After 2026-10-08, baseline v3 moved to 10/10 nominal with `warning` blocked pending human review; see [`scheme-b-reliability.md`](scheme-b-reliability.md) for that verification record.

> **Historical Scope Note (2026-10-27)**: Figures in the tables below (`Overall Scenario Count 37`, `raw completion 0.5946`,
> `21/37`, etc.) reflect Phase 7's scope **at that time** and are **not current metrics**. `golden-workflows.yaml` now defines 12 workflows
> deriving 43 scenarios (12 nominal + 31 robustness), with baseline updated to v4
> (current raw completion ratio 25/43 = 58.1%, see `raw_task_completion_rate` in `tests/evals/baseline.json`).
> The core verdict ("V2 caused zero regressions") still holds, but do not cite the legacy counts below as current numbers.

> Phase: Phase 7 (Full Regression + Baseline Freeze) + Phase 7.5 (Evaluation Semantics Correction)
> Verdict: V2 introduced zero regressions; Eval metrics corrected (Nominal / Robustness / Safety separated); Baseline frozen under the corrected methodology.

## 1. V2 Architecture Summary

- Execution Core: `scripts/core/` (`state` / `capability` / `trace` / `verification` / `recovery` / `execution`)
- Internal execution pipeline: `State → Capability Facade → Trace → Verification Adapter → Recovery Decision → Execution Core`
- Three user entry points unchanged: Skill / MCP / CAD Studio
- Single existing file modified across all of V2: `apps/desktop/cad_workbench/queue_worker.py` (+58 / −1)

## 2. Regression Matrix

| Subsystem | Tests | Result | Environment |
|---|---|---|---|
| Core State / Capability / Trace | 36 | PASS | CI-safe |
| Core Verification / Recovery / Execution | 62 | PASS | CI-safe |
| Golden Eval (`metrics` / `runner` / `baseline`) | 27 | PASS | CI-safe |
| Worker / Reviewer / Ledger / Policy / Health / Orchestrator | 94 | PASS | CI-safe |
| Other units (`sw`/`mcp`/`design`/`dfm`/`routing`/`fea`/`headless`/`drawing`/`subskills`/…) | 521 | PASS | CI-safe |
| Release Check (bundled Skill packaging) | 1 | SKIP | Requires running `sync_bundled_skill.py` first |
| **pytest Total** | **740 passed / 1 skipped** | **0 failed** | CI-safe |
| SolidWorks live regression (`solidworks_*_regression.py`) | — | NOT RUN | Windows + SolidWorks |
| AutoCAD live regression (`autocad_*_regression.py`) | — | NOT RUN | Windows + AutoCAD |
| CAD Studio weekly regression (`cad_studio_weekly_regression.py`) | — | NOT RUN | Windows + CAD |
| CalculiX external solver (`calculix_*_regression.py`) | — | NOT RUN | CalculiX |

> Live CAD and external-solver regressions run separately via `.github/workflows/windows-cad-regression.yml` on self-hosted Windows + CAD runners.

## 3. Backward Compatibility

| Item | Result |
|---|---|
| A. Skill (`SKILL.md` workflow) | Untouched, completely unchanged |
| B. MCP (Tool Names / Input Schemas / startup) | Untouched, completely unchanged |
| C. CLI (`cad_studio.py` commands) | Untouched, completely unchanged |
| D. CAD Studio (legacy Queue Jobs / events / Worker terminal semantics) | Legacy jobs without sidecar fields work normally; legacy events without `run_id`/`step_id` remain readable; Worker terminal semantics preserved |
| E. `capabilities.yaml` | Remains sole source of truth, untouched |
| F. `golden-workflows.yaml` | Backward-compatible with legacy format, untouched |

## 4. Official Eval Metrics (Phase 7.5 Corrected Methodology)

`python tests/evals/runner.py` (full 37-scenario set across four groups):

### Nominal Reliability (11 Nominal Scenarios)

| Metric | Value |
|---|---|
| Nominal Scenarios | 11 |
| Nominal Task Success Rate | 100.0% |
| Nominal First Pass Success Rate | 100.0% |
| Target First Pass | 90% |
| **Target Status** | **PASS** |
| Average Tool Calls | 1.0 |
| Average Duration | 0.0 ms |

### Robustness (26 Robustness Scenarios)

| Metric | Value |
|---|---|
| Robustness Scenarios | 26 |
| Expected Outcome Accuracy | 100.0% |
| Recovery Success Rate | 100.0% |
| Failure Detection Rate | 100.0% |
| Policy Block Accuracy | 100.0% |
| Capability Gap Detection | 100.0% |
| Backend Fallback Decision Accuracy | 100.0% |
| Reviewer Block Detection | 100.0% |
| Retry Exhaustion Accuracy | 100.0% |

### Safety

| Metric | Value |
|---|---|
| Raw Handler False-Positive Incidence | 33.3% (deliberately injected via fault-injection) |
| False-Completion Detection Rate | 100.0% |
| **Escaped False Completion Rate** | **0.0%** |

### Overall Diagnostic (Not Used for Target)

| Metric | Value |
|---|---|
| Overall Scenario Count | 37 |
| Overall Raw Task Completion Rate | 59.5% (diagnostic only) |
| Overall Average Tool Calls | 1.27 |

## 5. Reliability Baseline (Post-Phase 7.5 Correction)

Frozen into `tests/evals/baseline.json` (`schema_version: 2.0`, `baseline_version: 2`):

- `nominal_metrics`: 11 scenarios / `task_success` 1.0 / `first_pass` 1.0
- `robustness_metrics`: 26 scenarios / `expected_outcome_accuracy` 1.0 / `recovery` 1.0 / `detection` 1.0
- `safety_metrics`: `raw_false_positive` 0.3333 / `detection` 1.0 / **`escaped` 0.0**
- `overall_diagnostic_metrics`: 37 scenarios / raw completion 0.5946

**Release Guard** (`tests/test_eval_baseline.py`):
- `nominal_first_pass_success_rate >= target_first_pass_rate` (1.0 ≥ 0.90 ✅)
- `escaped_false_completion_rate == 0` ✅
- `expected_outcome_accuracy` does not regress ✅

## 6. CI-Safe vs. Live-Test Boundaries

- **CI-safe**: All `pytest` tests (Windows CI + `pywin32`/`comtypes`, requiring no live CAD binaries).
- **CAD-live**: Live SolidWorks / AutoCAD / CAD Studio regression scripts (not named `test_*.py`, excluded from `pytest` collection).
- **external-solver**: CalculiX regression scripts.

## 7. Known Limitations and Metric Notes

- Eval is a **Deterministic Execution Reliability Benchmark** (Fake Handler/Reviewer), **not** real user success rate, live SolidWorks full-scenario success rate, Codex reasoning capability, or a production SLA.
- Duration ≈ 0 ms (instant fake handlers); realistic timings require a future Live Agent Eval.
- `Overall Raw Task Completion Rate` (59.5%) is diagnostic only and never compared against targets.
- **Phase 7.5 semantic correction**: The old formula mixed nominal and fault-injection runs in the same denominator, producing:
  - 29.7% first-pass (falsely flagged `BELOW_TARGET` against 90%);
  - 33.3% false completion (actually "Verification correctly caught 11 injected false-success candidates", not leakage).
  After correction: nominal first-pass = 100% (`PASS`), escaped false completion = 0%.
- `test_release_check` skip: run `python scripts/sync_bundled_skill.py` beforehand.

## 8. Issues Found

**Zero production code bugs.** Phase 7.5 discovered and corrected an **Eval metric methodology flaw** (conflated denominators), resolved via category separation, grouped metrics, and the three-layer false-completion definition without modifying any production execution code.

## 9. Production Code Changes

Only 1 existing file changed across all of V2: `apps/desktop/cad_workbench/queue_worker.py` (+58/−1, minimal Phase 5 integration). Phases 6–7.5 touched zero production code (only `tests/evals/*`, `tests/test_eval_*`, and docs).

Core module sizes (lean, single-responsibility): `state` 373 / `capability` 125 / `trace` 166 / `verification` 295 / `recovery` 432 / `execution` 255 lines. No Worker, Planner, Reviewer, or Router logic was absorbed.

## 10. Readiness for V2 Documentation Freeze

**Ready (pending confirmation).** V2 completed: Architecture Audit → State/Capability/Trace → Verification Adapter → Recovery Decisions → Execution Orchestration + minimal Worker integration → Reliability Eval → Regression + Baseline Freeze → Eval Semantics Correction.
Next step: Phase 8 (Documentation Freeze: add `docs/architecture/execution-core.md` + one-sentence README note).
