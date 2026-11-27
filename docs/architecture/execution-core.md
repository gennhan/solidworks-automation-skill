# V2 Execution Core — Internal Reliable Execution Layer

> Positioning: Execution Core is an **internal implementation**, not a user entry point, not a daemon, not a standalone runtime service,
> not a fourth entry point, and not a replacement for upper-layer planning by Codex / Claude.

## 1. Motivation

Before V2, reliable execution patterns were scattered across Skill, MCP, Worker, Reviewer, and Artifact Ledger modules
(capability gates, backend routing, policy approvals, leases, heartbeats, stale recovery, file-fact review, geometric evidence, and JSONL event streams),
but had **not been consolidated into a single, reusable, testable execution reliability layer**.

V2 engineers these existing capabilities into a lightweight execution layer built on one core principle:

> AI may reason freely, but execution must be controlled, verifiable, recoverable, and traceable.

## 2. Architecture

```
LLM Agent (Codex / Claude / Cursor / OpenClaw)
  ↓
Skill / MCP / CAD Studio（三个用户入口，保持不变）
  ↓
Execution Core（scripts/core/）
  ├─ State（state.py）
  ├─ Capability Facade（capability.py）
  ├─ Trace（trace.py）
  ├─ Verification Adapter（verification.py）
  ├─ Recovery Decision（recovery.py）
  └─ Execution Orchestration（execution.py）
  ↓
Backend Router（scripts/capabilities.py + capabilities.yaml）
  ↓
Tools / MCP / Scripts（Python COM / C# PIA / OCCT / ...）
  ↓
External CAD Software
  ↓
Verification → Recovery Decision → Artifacts / Evidence / Trace
```

**Terminology alignment** (do not conflate Runtime Manager / Agent Engine / Workflow Engine / Orchestrator Core):

- **Skill** = Domain knowledge, capability definitions, SOPs, open capability rules
- **MCP** = Standardized Tool Protocol
- **Capability Registry** = `capabilities.yaml` + adapter
- **Backend Router** = Selects execution backend based on capability / environment / version
- **Execution Core** = Execution Reliability Layer (essentially a lightweight Agent Runtime)
- **Worker** = Job Processor
- **Reviewer** = Result Verification
- **Artifact Ledger** = Delivery Facts (final delivery facts)
- **Trace** = Execution History (runtime execution history)
- **Golden Workflow Eval** = Reliability Benchmark

## 3. State (`state.py`)

A lightweight execution state model that is **not tightly coupled to the CAD Studio Queue Schema** and can be reused across Worker, MCP, and CLI.
Instead of a complex FSM, it enforces a minimal transition allowlist (blocking transitions such as `FAILED → COMPLETED` and `BLOCKED → COMPLETED`).

- `RunStatus`: `created` / `running` / `verifying` / `retrying` / `blocked` / `failed` / `completed`
- `StepStatus`: `pending` / `running` / `success` / `failed` / `verifying` / `retrying` / `blocked`
- `VerificationStatus`: `PASS` / `WARN` / `FAIL` / `BLOCKED`
- `RunContext` / `StepRecord` / `ExecutionResult` / `VerificationResult` / `RecoveryDecision`

All models are JSON-serializable with `schema_version`; they store only `arguments_summary` / `result_summary` summaries and never store full prompts, API keys, secrets, or unnecessary absolute paths.

## 4. Capability Facade (`capability.py`)

**Not a new registry**, but a thin adapter over `scripts/capabilities.py` + `capabilities.yaml`:

- `get_capability` / `get_capability_status` / `get_operation_route`
- `resolve_backend` (delegates directly to `resolve_operation_backend`)
- `get_backend_candidates` / `requires_review` / `capability_gap`

`capabilities.yaml` remains the sole source of truth for capabilities; no secondary config such as `tool_registry.yaml` is introduced.

## 5. Execution (`execution.py`)

`execute_with_core(...)` acts as orchestration glue, chaining together:

```
RunContext + StepRecord
  → Existing Handler（原样调用，raw_result 保留）
  → ExecutionResult（最小归一化，异常原样交还）
  →（requires_review 时）Verification Adapter
  →（失败/blocked 时）Recovery Decision
  → Trace
  → ExecutionAssessment（sidecar）
```

**Explicitly out of scope**: Queue claim / lease / heartbeat / approval / policy / stale recovery / Ledger implementation /
Reviewer implementation / Backend Router implementation / actual retry / actual backend switching / replanning / network access.

## 6. Verification (`verification.py`)

The Verification Adapter solely translates inspection outputs into a unified language:

- `verify(...)` invokes the existing Reviewer (injected callable or pre-existing result) and outputs a unified `VerificationResult`;
- Normalizes legacy statuses: `pass/warn/warning/review_required → PASS/WARN`, `fail/failed → FAIL`,
  `blocked → BLOCKED`, with unknown values safely downgraded to `BLOCKED`;
- Aggregation precedence: `BLOCKED > FAIL > WARN > PASS`, honoring `severity` / `required` / `optional`;
- **`reviewer_result` takes precedence over `reviewer`** so the same review facts are never executed twice.

Core rule: **Tool / Handler returning success ≠ job success**. Capabilities requiring review may reach `completed` only when Verification returns `PASS` and `manual_review_required=false`; `WARN`, `FAIL`, `BLOCKED`, and manual-review-pending results can never enter `completed`. Structured execution results fail immediately if a required boolean flag is `false`, or block if types are ambiguous or critical evidence is `null`; a top-level `PASS` can never override a required check's `FAIL`.

## 7. Recovery Decision (`recovery.py`)

Answers only "what action should be taken next after this failure" and **does not execute the action**.

- `ErrorKind` (10 categories): `transient` / `invalid_argument` / `environment_missing` / `tool_unavailable` /
  `backend_unavailable` / `verification_failed` / `user_action_required` / `policy_blocked` / `capability_gap` / `fatal`
- Deterministic priority in `classify_error(...)`: explicit `error_kind` → structured `error_code` → existing Result status
  (`policy` > `capability` > `verification` > `execution`) → exception type → message keywords → unknown defaults to `FATAL`
- `decide(...)` → `RecoveryDecision` (`retry` / `fallback_backend` / `replan_required` /
  `user_action_required` / `block` / `fail`), with bounded retries (`DEFAULT_MAX_RETRIES = 2`)

**Important: Recovery Decision ≠ Recovery Execution.** The current version only generates and records decisions;
**automatic retry, fallback, and replanning are not enabled by default**—the Worker or upper-layer Agent decides whether to execute the action.

Safe defaults: when uncertain → `BLOCK` / `FAIL` / `REPLAN`, never default to `retry`. `POLICY_BLOCKED → block`;
Recovery is never permitted to bypass Policy Gate.

## 8. Trace (`trace.py`)

Reuses the existing append-only JSONL under `queue/events/` **without creating a separate trace store**:

- Events: `run.started` / `step.started` / `tool.called` / `tool.succeeded` / `tool.failed` /
  `verification.*` / `recovery.*` / `run.completed` / `run.failed` / `run.blocked`;
- Additive schema: `run_id` / `trace_id` / `step_id` / `parent_step_id` / ... are all optional, keeping legacy events readable;
- Fallback `redact` sanitization (`prompt` / `api_key` / `token` / `secret` / ...);
- Trace write failures never affect execution outcomes (observability is a non-blocking sidecar).

Separation of concerns: **Artifact Ledger = final delivery facts; Trace = runtime execution history**; overlap is prohibited.

## 9. Worker Integration (Minimal Intrusion)

`queue_worker.process_job` continues reusing existing handlers and the Review Gate:

```
Job → Policy / Approval（仍在 Execution Core 之前）
    → Execution Core 包裹 Existing Handler
    → Existing Reviewer Gate（仍只发生一次）
    → Verification Adapter + Recovery Decision（复核结果进入既有 Gate）
    → 既有终态映射（passed / review_required / failed / blocked / cancelled）
```

- Policy / Approval / Cancellation / claim lock / lease / heartbeat / stale recovery / quarantine
  are **completely untouched**;
- Existing Handlers remain the sole real execution implementations;
- Queue / Worker / Reviewer / Artifact Ledger were not rewritten;
- Added `executionAssessment` / `verificationAssessment` / `recoveryDecision` as optional sidecars.
- When the Worker calls Core, completion is deferred until the existing Review Gate finishes so Queue and Core terminal states stay synchronized, preventing Core from marking `completed` before Queue marks `failed`.

## 10. Capability Gap

When a capability or backend is missing, Core returns a structured `CAPABILITY_GAP` (`agent_resolution_required`) and hands control back to the upper-layer Agent. **Execution Core does not access the network or auto-generate tools**; the upper-layer Agent proceeds according to `SKILL.md`:

```
references → official API / SDK → alternate backend → minimal implementation → verification
```

`Tool Missing != Capability Missing`: if the capability exists but a tool is unavailable → `replan_required`
(the upper-layer Agent attempts Tool Composition); if the capability itself is missing → `CAPABILITY_GAP`.

## 11. Reliability Eval (`tests/evals/`)

`golden-workflows.yaml` is the single source of truth for Golden Workflows. The Eval derives **43 deterministic scenarios** (12 nominal + 31 robustness) from **12 workflows**,
grouped by category (`nominal` / `recovery` / `fault_injection` / `guardrail`), validating execution control logic via fake handlers and reviewers. Metrics are grouped into four sets: Nominal, Robustness, Safety, and Overall Diagnostic.
Scenario counts are derived dynamically from source data by `build_scenarios()` rather than hard-coded in tests.
See [`v2-evaluation.md`](v2-evaluation.md) and [`v2-regression-report.md`](v2-regression-report.md) for details.

## 12. Compatibility

- Skill usage, CLI commands, and Queue Schema remain backward-compatible; MCP exposes **61 tools in total**—all 60 original tools retain identical names and full Input Schemas, with 1 new read-only artifact tool and optional HTTP transport;
- `capabilities.yaml` remains the sole source of truth, and `golden-workflows.yaml` remains backward-compatible;
- All new fields are additive and optional;
- Scheme B (2026-10-08) fixed execution truth, sketches/patterns, and resource lifecycles; acceptance scope is SolidWorks 2026—see [`scheme-b-reliability.md`](scheme-b-reliability.md).
