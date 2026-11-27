# V2 Release Notes (Draft)

> SolidWorks Automation Skill V2 — Internal Reliability Architecture Upgrade.
>
> **Status Note (2026-10-27)**: This document contains the original V2 draft release notes and **does not represent current release readiness**.
> Current release readiness is `BLOCKED`; see the external P0-2.1 release blocker checklist for open items.
> References to `37 scenarios` reflect the metric scope at that time; the current suite has 12 workflows / 43 scenarios (baseline v4).

## Added

- **Execution Core** (`scripts/core/`): Chains State, Capability, Trace, Verification, and Recovery into an internal execution layer wrapping existing handlers.
- **State Model** (`state.py`): Lightweight Run / Step / Execution / Verification / Recovery state models.
- **Capability Facade** (`capability.py`): Thin adapter reusing `capabilities.yaml` as the sole source of truth.
- **Verification Adapter** (`verification.py`): Unifies existing Reviewer results into `PASS` / `WARN` / `FAIL` / `BLOCKED`.
- **Recovery Decision Layer** (`recovery.py`): 10 error categories + 6 recovery decisions (decision-only; does not auto-execute by default).
- **Trace Integration** (`trace.py`): Reuses append-only execution history under `queue/events/`.
- **Golden Workflow Reliability Eval** (`tests/evals/`): Deterministic execution reliability benchmark.

## Preserved

- Existing Skill workflows, MCP Tool Names / Input Schemas, CLI commands, and CAD Studio Queue state semantics remain completely unchanged.
- Worker, Reviewer, Artifact Ledger, and Policy Gate were not rewritten.
- `capabilities.yaml` remains the sole capability source of truth; `golden-workflows.yaml` remains backward-compatible.
- All new fields are additive and optional.

## Metrics (Deterministic Execution Reliability Benchmark, 37 Scenarios)

| Metric | Value |
|---|---|
| Nominal First-Pass Success | 100% (10/10, baseline v3) |
| Nominal Task Success | 100% |
| Failure Detection | 100% |
| Policy Block Accuracy | 100% |
| Capability Gap Accuracy | 100% |
| Backend Fallback Decision Accuracy | 100% |
| False-Completion Detection | 100% |
| Escaped False-Completion | 0% |

## Limitations

- Scheme B (2026-10-08) changed `warning`/manual review to `blocked` and added SolidWorks 2026 live acceptance for sketches, patterns, document ownership, and remote artifacts; see [`scheme-b-reliability.md`](scheme-b-reliability.md). Older SolidWorks versions are outside current support and acceptance scope.
- The benchmark above is **synthetic and deterministic** (Fake Handler/Reviewer + fault injection) and is **not** real user success rate, live SolidWorks full-scenario pass rate, LLM intelligence, or a production SLA.
- Execution Core does not perform automated LLM planning (upper-layer agents remain responsible for planning).
- No automated Web / API capability discovery (capability gaps are handed back to the upper-layer agent).
- Recovery emits **decisions only**; automatic retry, fallback, and replan actions remain under Worker / upper-layer agent control and are disabled by default.

## Docs

- [`docs/architecture/execution-core.md`](execution-core.md)
- [`docs/architecture/v2-evaluation.md`](v2-evaluation.md)
- [`docs/architecture/v2-regression-report.md`](v2-regression-report.md)
- [`docs/architecture/v2-audit.md`](v2-audit.md)
