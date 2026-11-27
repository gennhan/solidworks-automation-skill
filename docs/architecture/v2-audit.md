# SolidWorks Automation Skill V2 Architecture Audit Report

> Version: Phase 1 (Architecture Audit)
> Status: **Historical Snapshot**. This report records Phase 1 audit conclusions; Phases 2–8 have already been implemented following this plan,
> so point-in-time phrases like "proceed to Phase 2 after confirmation" no longer reflect current status.
> Refer to `capabilities.yaml` for current capability levels and PR #43 / the release blocker checklist for release readiness.
> Scope: Full read of the `main` branch of `wzyn20051216/solidworks-automation-skill`
> Principle: Audit first, modify no code; this document states facts and a minimal refactoring plan without containing implemented code.

---

## 0. Audit Scope and Methodology

Read in full:

- Top-level docs: `README.md`, `SKILL.md`, `SUBSKILLS.md`, `capabilities.yaml`, `golden-workflows.yaml`
- Routing/Capabilities: `scripts/capabilities.py`, `scripts/backend_router.py`, `references/language-backend-routing.md`
- Review/Preflight: `scripts/sw_review.py`, `scripts/sw_preflight.py`
- Desktop runtime (`apps/desktop/cad_workbench/`): `queue_worker.py`, `reviewer_gate.py`, `artifact_ledger.py`, `worker_health.py`, `agent_contracts.py`, `agent_providers.py`, `knowledge_retrieval.py`, `engineering_orchestrator.py`, `core.py`
- MCP: `mcp-server/server.py` (~3,500 lines), `mcp-server/README.md`
- CLI: `scripts/cad_studio.py`
- Docs: `docs/agent-framework/enterprise-agent-control-plane.md`, `docs/product-mvp-spec.md`, `docs/skill-map.md`
- Tests: `tests/fakes.py`, `tests/test_cad_reliability.py`, `tests/test_workbench_queue_worker.py`, and full test tree overview
- Packaging/CI: `pyproject.toml`, `scripts/sync_bundled_skill.py`, `.github/workflows/windows-cad-regression.yml`

Audit conclusion: **This project already embodies reliable-execution principles far beyond a typical skill**—a capability source of truth, backend router, policy gate, queue leases, heartbeats, stale recovery, Artifact Ledger, Reviewer Gate, JSONL event stream, and geometric evidence all exist, yet remain **scattered across modules rather than consolidated into a unified, reusable, testable "Execution Core"**. The essence of V2 is to **engineer these existing capabilities into a lightweight execution reliability layer**—not a rewrite, not a new user entry point, and certainly not a generic Agent Framework.

---

## 1. Current Real Architecture

### 1.1 Three User Entry Points (Confirmed, Kept Unchanged)

| Entry Point | Location | User Interaction |
|---|---|---|
| **Skill** | `SKILL.md` + `scripts/` + `references/` + `subskills/` | After installation, talk to Codex / Claude / Cursor / OpenClaw; the agent reads SOPs and runs scripts |
| **MCP** | `mcp-server/server.py` (FastMCP + Pydantic, stdio) | Agent performs structured tool calling after installation |
| **CAD Studio** | `apps/workbench-ui/` (React+Tauri frontend) + `apps/desktop/cad_workbench/` (Python worker) + `scripts/cad_studio.py` (queue CLI) | Submit jobs via desktop GUI or manage the queue via CLI |

> Note: Subcommands in `scripts/cad_studio.py` (`doctor`/`run`/`status`/`retry`/`cancel`/...) are **CAD Studio's companion CLI**, not a fourth user entry point. Any V2 debug/eval commands should live there instead of creating a new CLI.

### 1.2 Current Module Responsibilities vs. Unified V2 Concepts

| Unified V2 Concept | Current Implementation | Maturity |
|---|---|---|
| Skill (knowledge/SOP/open rules) | `SKILL.md`, `SUBSKILLS.md`, `subskills/*`, `references/*` | Strong |
| MCP (protocol) | `mcp-server/server.py` (~60 tools, allowlisted, serialized) | Strong |
| Capability Registry | `capabilities.yaml` + `scripts/capabilities.py` | **Strong (sole source of truth exists)** |
| Backend Router | `scripts/capabilities.py::resolve_operation_backend` + `backend_router.py` | **Strong (already exists)** |
| Execution Core | **No standalone module**; logic scattered across `queue_worker.py` / `sw_review.py` / `reviewer_gate.py` | **Missing (V2 target)** |
| Worker | `queue_worker.py` (lease/heartbeat/cancel/stale/quarantine) | Strong |
| Reviewer | `sw_review.py` (CAD geometry) + `reviewer_gate.py` (file facts) + DFM/Routing/Drawing evidence | Strong |
| Artifact Ledger | `artifact_ledger.py` (SHA-256, `producedThisRun`) | Strong |
| Trace | `queue_worker.py::append_event` (JSONL, job-level) + stdout/stderr logs | Partial (job-level; no unified run/step model) |
| Golden Workflow Eval | `golden-workflows.yaml` (static validation only, no execution benchmark) | **Missing (V2 target)** |

---

## 2. Current Call Chains

### 2.1 Skill Path (Agent Invokes Scripts Directly)

```
LLM Agent (Codex/Claude/OpenClaw)
  └─ 读 SKILL.md / SUBSKILLS.md / subskills/*/SKILL.md（SOP 与路由）
       ├─ python scripts/sw_preflight.py（依赖/SolidWorks 门禁，含用户授权安装）
       ├─ python scripts/backend_router.py --operation ...（只读后端选择）
       ├─ python scripts/sw_capability_probe.py（能力/类型库探测）
       └─ 执行 scripts/sw_*.py（sw_connect / sw_part / sw_assembly / sw_export / sw_motion ...）
            └─ sw_review.run_review()（多视角预览 + review_report.json + 几何/B-Rep 证据）
                 └─ 能力缺口：references/api-lookup.md → 官方 API Help/SDK → alternate backend → 最小实现 → 真机 → Review → 沉淀
```

Key point: Execution on the Skill path is driven **directly by the upper-layer agent** with no local runtime interceptor. Reliability constraints rest primarily on **SOP rules in `SKILL.md`** ("self-review results", "unwrapped API rules", "never report save-success alone"). Therefore **Execution Core cannot directly rewrite the Skill path**; it serves as a shared underlying layer reused incrementally by Worker and MCP, while the Skill path continues relying on SOP instructions plus `sw_review.py`.

### 2.2 MCP Path (Serialized Allowlisted Tools)

```
Agent → MCP tool call
  └─ server.py @mcp.tool(...) → def solidworks_*/cadstudio_*/design_spec_*
       └─ _run_locked(op, format, load_automation, timeout=300s)
            ├─ _sw_lock.acquire(timeout)   # 全局 RLock，SolidWorks COM 串行
            ├─ _load_automation_modules()  # 惰性加载 sw_*.py
            ├─ _coinitialize()             # COM 线程初始化
            └─ op() → scripts/sw_*.py → _result(json|markdown)
                 └─ 异常 → _tool_error(结构化 status/error_type/message/suggestion)
```

Key point: MCP already enforces **strict serialization, lock timeouts, structured errors, lazy loading, and modal-dialog diagnostics via `solidworks_recover`**. As the most stable module, V2 explicitly leaves it **untouched**.

### 2.3 CAD Studio Path (Worker + Gates + Ledger + Review)

```
UI/CLI → 写 Job JSON 到 queue 目录
  └─ queue_worker.process_queue
       ├─ recover_stale_jobs()                 # lease 过期恢复 / 取消 / 坏任务隔离
       ├─ acquire_lock()（文件锁 + lease）      # 跨进程串行 + 领取
       └─ process_job()
            ├─ _capability_block_reasons()      # capabilities.yaml 能力门禁
            ├─ require_policy_approval()        # Policy Gate（危险操作人工审批）
            ├─ mark_job_claimed() → running → heartbeat/lease/cancel
            ├─ handler 分发：mock | dfm_review | codex_task | agent_task
            │    └─ run_agent_job()
            │         ├─ engineering_orchestrator（阶段 DAG 规划 + RetryPolicy）
            │         ├─ knowledge_retrieval（本地 RAG）
            │         └─ 子进程 Agent CLI + 心跳/续租/超时/取消
            ├─ write_artifact_ledger()           # 交付事实 + SHA-256 + producedThisRun
            └─ write_reviewer_gate()             # 文件级复核
                 └─ 终态：passed / review_required / failed / blocked / cancelled
  └─ write_worker_health()
```

Key point: **CAD Studio Worker is already a de facto "Execution Runtime"** with queue, policy gate, capability gate, ledger, reviewer gate, heartbeats, stale recovery, and JSONL event streaming. V2's Execution Core should serve as the **unified abstraction** for `handler → verification → recovery decision` inside this pipeline rather than replacing Queue, Worker, or Ledger.

---

## 3. Inventory of Existing Reusable Capabilities

### 3.1 Retry (Scattered, Non-Uniform)

| Location | Mechanism |
|---|---|
| `scripts/sw_macro_guard.py` | Retries failed VBA macro validation 1–2 times + local template fallbacks (cube/cylinder/extrude/sketch) |
| `scripts/sw_assembly.py::add_component` | `AddComponent4` failure → retry via `AddComponent5` (SW2024 localized) |
| `scripts/sw_connect.py` / `sw_part.py` | Localized/English reference plane name fallback |
| `queue_worker.py` | `QUEUE_WRITE_RETRIES=24` atomic file-replace backoff (Windows file locks) |
| `engineering_orchestrator.py::RetryPolicy` | Stage-level `max_attempts/strategy/retryable_failures/fallback` (**planning layer, not execution layer**) |

Conclusion: Retry concepts exist, but there is **no structured error-classification-driven execution retry layer**. V2's Recovery Engine unifies this as "classify → decide" instead of adding yet another `try/except/retry 3`.

### 3.2 Review / Verification (Strong, Dual-Layer Complementary)

- **CAD geometry layer**: `scripts/sw_review.py` — `run_review` / `evaluate_review_report` / `collect_geometry_measurements` / `validate_hole_positions` / `inspect_pdf_text_layout` / `review_drawing_layout`; outputs `pass/warn/fail` + `manual_review_required` + `retryable`.
- **File-fact layer**: `reviewer_gate.py::evaluate_ledger` — existence, non-empty size, SHA-256, format headers (STEP/STL/DXF/PDF/DWG), and spec consistency (3D bounding dimensions, hole diameters).
- **Domain evidence layer**: `dfm_review.py`, `routing_review.py`, `sw_drawing_review.py`, FEA evidence, and drawing subskill `drawing_review.py`.

Conclusion: **Reviewers are already strong—do not rebuild them.** Execution Core's Verification Adapter solely "invokes existing reviews, interprets outcomes, and determines status".

### 3.3 Routing (Strong, Sole Source of Truth Exists)

`scripts/capabilities.py` already provides `load_capabilities`, `capability_index`, `backend_index`, `operation_route_index`, `resolve_operation_backend`, `capability_level`, `unattended_allowed`, `capability_snapshot`, and `backend_route_snapshot`.

`resolve_operation_backend` already implements semantic filtering (`automation_equivalent`/`exact_native`...), revision blockers (`KNOWN_HOST_REVISION_BLOCKER`), add-in/license requirements (`MISSING_RUNTIME_REQUIREMENT`), candidate prioritization, and `unavailable` (no compatible backend).

Conclusion: **Backend Router is complete.** `scripts/core/capability.py` must strictly be an Adapter/Facade and never duplicate this logic.

### 3.4 Trace / Logs (Job-Level JSONL Already Exists)

`queue_worker.py` already provides:
- `append_event()` → `queue/events/{job_id}.jsonl`, with events such as `run.claimed`, `step.started`, `run.heartbeat`, `run.blocked`, `run.failed`, `run.passed`, `policy.approval_required`, `artifact.ledger_written`, and `review.gate_completed`.
- `logs/{job_id}.stdout.log` / `.stderr.log`.

Conclusion: JSONL event streaming exists, but is **job-scoped without a unified `run_id/trace_id/step_id/parent_step_id` model**, and its boundary vs. Artifact Ledger is not yet codified in documentation. V2 Trace reuses `queue/` and append-only JSONL semantics while adding unified step-level metadata.

### 3.5 Queue State / Worker Health (Strong)

`queue_worker.py`: `read_job/write_job` (atomic), `acquire_lock/release_lock` (OS file lock + lease), `recover_stale_jobs`, `quarantine_bad_job`, `mark_job_claimed`, `refresh_job_heartbeat`, `request_cancel`, cancellation flags, `watch_queue`.
`worker_health.py`: `write_worker_health`, `count_jobs`, `health_level` (`healthy`/`attention`/`warning`/`error`).

Job terminal states: `passed / review_required / failed / cancelled / blocked`; non-runnable state: `approval_required`.

Conclusion: **Queue and Worker are stable and irreplaceable.** Execution Core does not replace them.

### 3.6 Artifact Ledger (Strong)

`artifact_ledger.py`: `sha256_file`, `collect_artifact_paths`, `describe_artifact` (exists/size/sha256/**`producedThisRun`** via baseline snapshot), `build_artifact_ledger`, `write_artifact_ledger`.

Conclusion: **Artifact Ledger = delivery facts** and is complete. Trace must never duplicate it.

### 3.7 Error Handling (Weak, Lacks Structured Classification)

Current state: `sw_preflight` has `DependencyInstallDeclined`/`SolidWorksNotInstalledError`; MCP has structured `_tool_error` payloads; `queue_worker` has `JobCancelled`/`JobBlocked` and fallback `except Exception → failed`.

Gap: **No structured `TRANSIENT/INVALID_ARGUMENT/ENVIRONMENT_MISSING/TOOL_UNAVAILABLE/BACKEND_UNAVAILABLE/VERIFICATION_FAILED/USER_ACTION_REQUIRED/POLICY_BLOCKED/CAPABILITY_GAP/FATAL` taxonomy**, nor a unified `RecoveryDecision`.

### 3.8 Policy Gate (Strong)

`agent_contracts.py`: `DANGEROUS_CAPABILITIES`, `policy_reasons`, `require_policy_approval`, `is_policy_approved` (approval-scope re-check intercepts again if risk reasons change post-approval).

Conclusion: Policy Gate is authoritative. Execution Core's `POLICY_BLOCKED` classification must strictly honor it; **Runtime may never bypass Policy Gate**.

### 3.9 Open Capability Gap Mechanism (Exists in Skill Docs, Missing in Code)

Current state: **Purely text-based in `SKILL.md` / `references/`**:
- `SKILL.md` "Unwrapped API rules": insufficient capability → check `references/api-lookup.md` → official API Help / local SDK → `references/language-backend-routing.md` for alternate backend → minimal implementation → live run → `sw_review.py` → codify.
- `references/api-lookup.md` provides lookup templates, minimal verification script rules, and codification rules.

Gap: **No structured `CAPABILITY_GAP` return value.** `resolve_operation_backend` returns `blocked/UNKNOWN_OPERATION_ROUTE` or `unavailable/NO_COMPATIBLE_BACKEND_AVAILABLE`, which is close in meaning but does not explicitly signal "this is a capability gap; hand control back to the upper-layer agent".

---

## 4. Current Responsibilities of `capabilities.yaml` (Sole Source of Truth)

`capabilities.yaml` (`schema_version: 1.0`) currently serves **four distinct roles**:

1. **Capability maturity catalog** (`capabilities[]`, 29 entries): `id/level/backends/verified_versions/dependencies/limitations/allowed_modes` (some with `skills`/`mcp_tools`), where `level ∈ {verified, pilot, reference_only, not_implemented}`.
2. **Backend catalog** (`backend_catalog`, 10 entries): `language/runtime/suitable_for/limitations`.
3. **Atomic operation routing** (`operation_routes`, 14 entries): `id/capability_ids/candidates[{backend,semantics,priority}]/review_required/blocked_revisions/requires/notes/blocked_reason`.
4. **Version matrix facts** (`verified_versions.solidworks/autocad`).

**Key conclusion: `capabilities.yaml` is already the single source of truth for capabilities, fulfilling three roles simultaneously (capability gating + backend routing + version matrix).** V2 strictly prohibits adding duplicate config files like `tool_registry.yaml`. Any future extensions may add **optional** fields only (`risk_level / review_required / preferred_backend / fallback_backends / retry_policy / timeout / side_effects`), keeping `scripts/capabilities.py::load_capabilities` backward-compatible when omitted.

---

## 5. Duplication and Over-Engineering Risks

### 5.1 Pre-Existing Duplication (V2 Must Not Replicate)

1. **Duplicate capability map**: `engineering_orchestrator.py::CAPABILITIES` embeds an internal capability map (`CapabilityLevel`/skills/mcp_tools) overlapping `capabilities.yaml`. This is historical; **V2 will not refactor it**, but new code must never create a third capability map.
2. **`resolve_operation_backend` already performs routing**: reimplementing backend selection anywhere else is wheel-reinvention.

### 5.2 Duplication V2 Must Avoid

1. Creating `tool_registry.yaml / runtime_capabilities.yaml / agent_capabilities.json`.
2. Rebuilding Reviewers (`sw_review.py` + `reviewer_gate.py` suffice).
3. Rebuilding Artifact Ledger (Trace logs process only, never delivery facts).
4. Rebuilding Fake/Mock suites (`tests/fakes.py` already provides COM fakes; Eval should reuse or sit adjacent to it).
5. Rebuilding Golden Workflows (`golden-workflows.yaml` already exists and only lacks an execution benchmark).

### 5.3 Over-Engineering Risks (Critical Watchouts)

1. **Building a generic Agent Framework**: multi-agent Planner/Executor/Reviewer/Manager/Supervisor nesting. Upper-layer agents already own Planning; Execution Core handles Execute/Observe/Verify/Recover/Trace only.
2. **Complex state machines**: lightweight `RunStatus`/`StepStatus` enums suffice; avoid DAG state engines or event sourcing.
3. **Standalone Trace Server / Runtime daemon**: Trace writes append-only JSONL under existing `queue/`; never launch extra services.
4. **Self-networking Runtime**: V2 v1 does no Web/API discovery; capability gaps return to the upper-layer agent.
5. **Re-wrapping MCP wholesale**: 60+ tools, COM lock, and Pydantic schemas are stable; Execution Core is adopted incrementally underneath without rewriting MCP.
6. **Terminology proliferation**: use **Execution Core** consistently; avoid mixing synonyms like Runtime Engine / Orchestrator / Workflow Engine / Agent Engine.

---

## 6. Minimal V2 Refactoring Plan

### 6.1 New Internal Module (`scripts/core/`, Not a User Entry Point)

```
scripts/core/
├── __init__.py
├── state.py        # 轻量状态模型（JSON 可序列化、带 version）
├── capability.py   # Adapter/Facade，复用 scripts/capabilities.py + capabilities.yaml
├── trace.py        # append-only JSONL Trace，复用 queue 目录
├── recovery.py     # ErrorKind 分类 + RecoveryDecision 映射
└── execution.py    # Execution Core facade：Execute → Observe → Verify → Recover → Trace
```

`sync_bundled_skill.py` already synchronizes the entire `scripts/` tree, so adding `scripts/core/` automatically flows into the desktop bundle without editing packaging scripts.

### 6.2 Module Highlights

**`state.py`**
- `RunStatus`: `CREATED` / `RUNNING` / `VERIFYING` / `RETRYING` / `BLOCKED` / `FAILED` / `COMPLETED`
- `StepStatus`: `PENDING` / `RUNNING` / `SUCCESS` / `FAILED` / `VERIFYING` / `RETRYING` / `BLOCKED`
- `RunContext` (`run_id`/`trace_id`/`goal`/`status`/`started_at`/`finished_at`/`current_step`/`steps`/`artifacts`/`evidence`/`errors`/`retry_count`/`metadata`)
- `StepRecord` (`step_id`/`parent_step_id`/`tool_name`/`capability_id`/`backend`/`status`/`started_at`/`finished_at`/`duration_ms`/`arguments_summary`/`result_summary`/`error_code`/`retryable`/`artifacts`/`evidence`/`verification`)
- `ExecutionResult` / `VerificationResult` / `RecoveryDecision`
- Constraints: JSON-serializable, versioned schema, **decoupled from CAD Studio Queue Schema**, reusable across Worker/MCP/CLI, **never duplicates Job objects**, never stores API keys, full prompts, secrets, or unnecessary absolute paths.

**`capability.py` (Facade)**
- Exposes `get_capability` / `get_operation_route` / `resolve_backend` / `requires_review` / `get_capability_status` / `get_backend_candidates`
- Delegates completely to `scripts/capabilities.py` with zero logic duplication.

**`trace.py`**
- Append-only JSONL; events: `run.created` / `step.started` / `tool.called` / `tool.succeeded` / `tool.failed` / `verification.started` / `verification.passed` / `verification.failed` / `recovery.retry` / `recovery.backend_fallback` / `capability.gap` / `run.blocked` / `run.failed` / `run.completed`
- Reuses existing `queue/` runtime directory (preferring `queue/events/` over adding `queue/trace/` to avoid new top-level concepts); **never writes to the repository root**.

**`recovery.py`**
- `ErrorKind`: `TRANSIENT` / `INVALID_ARGUMENT` / `ENVIRONMENT_MISSING` / `TOOL_UNAVAILABLE` / `BACKEND_UNAVAILABLE` / `VERIFICATION_FAILED` / `USER_ACTION_REQUIRED` / `POLICY_BLOCKED` / `CAPABILITY_GAP` / `FATAL`
- `RecoveryDecision`: `RETRY` / `FALLBACK_BACKEND` / `REPLAN_REQUIRED` / `USER_ACTION_REQUIRED` / `BLOCK` / `FAIL`
- Rules: `TRANSIENT` → bounded retry; `INVALID_ARGUMENT` → return to upper-layer agent; `BACKEND_UNAVAILABLE` → backend_router fallback; `ENVIRONMENT_MISSING` → fallback only if valid fallback exists, else `blocked`; `VERIFICATION_FAILED` → forbid `success` → repair/replan; `USER_ACTION_REQUIRED` → `blocked`; `POLICY_BLOCKED` → honor Policy Gate without bypass; `FATAL` → `failed`.
- Retries must be bounded, traceable, testable, and loop-proof.

**`execution.py` (Core Gate)**
- Enforces "Tool Success != Task Success": `requires_review` capabilities must complete `Execute → Verification → PASS → COMPLETED`; `Verification FAIL` forbids `COMPLETED` and must route to Recovery/Replan/Blocked/Failed.
- Handles multi-step execution, unified tracing, and status decisions only—no complex Planner.

### 6.3 Golden Workflow Eval (`tests/evals/`)

- Reuses `golden-workflows.yaml` (preserving `target_first_pass_rate` compatibility), optionally adding `must_review/max_retries/max_tool_calls/expected_capabilities/required_artifacts`.
- Three test classes: Happy Path, Failure Path (Tool success → missing artifact → Verification Fail → forbid Completed), Recovery Path (Primary Backend Fail → Fallback → Success → Verification Pass), plus Capability Gap.
- Metrics: Task Success Rate, First Pass Success Rate, Retry Rate, Recovery Success Rate, **False Completion Rate** (cases where execution reports success but Verifier fails), Average Tool Calls, Average Duration.
- Outputs: `eval_report.json` + `eval_report.md`.
- CI requires no real SolidWorks; uses Fake Backends / Mock Tools / Mock Reviewers (reusing or adjacent to `tests/fakes.py`).

---

## 7. Planned File Changes

| File | Change | Phase |
|---|---|---|
| `docs/architecture/v2-audit.md` | This audit report (new) | Phase 1 ✅ |
| `scripts/core/__init__.py` | New | Phase 2 |
| `scripts/core/state.py` | New state models | Phase 2 |
| `scripts/core/capability.py` | New Facade | Phase 2 |
| `scripts/core/trace.py` | New JSONL Trace | Phase 2 |
| `scripts/core/recovery.py` | New error classification & recovery decisions | Phase 4 |
| `scripts/core/execution.py` | New Execution Core facade | Phase 3–4 |
| `scripts/core/verification.py` (standalone) or merged into `execution.py` | Verification Adapter (reusing `sw_review` + `reviewer_gate`) | Phase 3 |
| `tests/test_core_state.py`, etc. | Unit tests for transitions, retry bounds, fallback, `POLICY_BLOCKED`, `CAPABILITY_GAP`, Trace JSONL | Phase 2–4 |
| `tests/evals/runner.py` (tentatively `golden_workflow_eval.py`) | Golden Workflow Eval + `eval_report` outputs; landed as `runner.py` + `metrics.py` + `baseline.json` | Phase 6 |
| `golden-workflows.yaml` | Append **optional** fields only (`must_review`/`max_retries`/...); existing workflows untouched | Phase 6 |
| `apps/desktop/cad_workbench/queue_worker.py` | Minimal intrusion: wire Execution Context + Verification + Recovery Decision between handler and ledger/reviewer, **no rewrite** | Phase 5 |
| `scripts/cad_studio.py` | (Optional) attach `inspect-trace` / `eval` under debug subcommands; skippable if unneeded | Phase 8 |
| `capabilities.yaml` | (Optional) append optional fields (`risk_level`/`review_required`/...) only; deferred by default | Phase 2 optional |
| `docs/architecture/execution-core.md` | New technical doc | Phase 8 |
| `README.md` | One user-facing sentence: "V2 adds internal reliable execution, automated verification, and failure recovery with no extra services required" | Phase 8 |

---

## 8. Modules Explicitly Untouched

| Module | Rationale |
|---|---|
| `mcp-server/server.py` | 60+ tools, Pydantic schemas, `_sw_lock` serialization, lock timeouts, `_coinitialize`, `_run_locked`, and `solidworks_recover` are all stable; SolidWorks COM must stay serialized without a second lock |
| `scripts/sw_*.py` (COM wrappers: `sw_connect`/`sw_part`/`sw_assembly`/`sw_export`/`sw_motion`/`sw_drawing`/`sw_hole_features`/`sw_measure`/`sw_edge_select`/`sw_document_data`/`sw_delivery`/`sw_appearance`/`sw_session`/`sw_macro_guard`...) | Live-verified stable wrappers; reuse without rewriting |
| `scripts/capabilities.py` + `scripts/backend_router.py` | Routing logic is complete; reuse as source of truth |
| `apps/desktop/cad_workbench/reviewer_gate.py` | Reviewer Gate is complete |
| `apps/desktop/cad_workbench/artifact_ledger.py` | Artifact Ledger is complete |
| `apps/desktop/cad_workbench/worker_health.py` | Worker Health is complete |
| `apps/desktop/cad_workbench/agent_contracts.py` | Policy Gate is authoritative |
| `apps/desktop/cad_workbench/agent_providers.py` | Provider Adapter is stable |
| `apps/desktop/cad_workbench/knowledge_retrieval.py` | RAG is stable |
| `apps/desktop/cad_workbench/engineering_orchestrator.py` | Stage DAG is stable (embedded capability map is historical; V2 does not refactor it) |
| `apps/workbench-ui/` (frontend) | User interface unchanged |
| `SKILL.md` / `SUBSKILLS.md` / all `subskills/*` | User SOP unchanged; open capability-gap text retained |
| `install.js` / `manifest.json` / `package.json` / `setup.py` / `pyproject.toml` / registry scripts | Installation and packaging unchanged |
| `scripts/sync_bundled_skill.py` | Already syncs `scripts/` recursively, automatically picking up `scripts/core/` |

> `queue_worker.py` is the **only** runtime file planned for minimal modification, strictly wrapping the existing `handler → ledger → reviewer` boundary without rewriting Queue, Lease, Heartbeat, or Policy Gate logic.

---

## 9. Critical Compatibility Red Lines (Throughout V2)

1. No new user entry points and no new background services (runtime/executor/orchestrator/trace server/eval server are all forbidden).
2. `capabilities.yaml` remains the sole capability source of truth; only optional fields may be appended.
3. Zero breaking changes to MCP Tool Names / Input Schemas or the SolidWorks COM serial lock.
4. Runtime may never bypass Policy Gate or Approval authority.
5. Worker Health, Heartbeat, Stale Recovery, and Artifact Ledger continue operating intact.
6. Runtime artifacts (Trace/Log/Artifact) write only to existing runtime directories (`queue/`, `logs/`, `artifacts/`), never the repository root.
7. CI requires no live SolidWorks; live regressions stay on dedicated self-hosted runners.
8. End users still follow "Install → Talk to AI → Receive trustworthy results".

---

## 10. Core Conclusions

- **The project is already halfway to an Execution Runtime**: queue, policy gate, capability gate, backend router, reviewer gate, artifact ledger, JSONL event stream, stale recovery, and heartbeats are all in place.
- **V2 truly needs only 5 minimal core files**: `state.py`, `capability.py` (facade), `trace.py`, `recovery.py`, and `execution.py`, plus a thin `verification` adapter and Golden Workflow Eval.
- **Real engineering value**: consolidating four currently scattered, implicit, prompt-dependent principles—"Tool Success ≠ Task Success", "structured error classification → recovery decision", "unified run/step Trace", and "structured capability-gap returns"—into a **reusable, unit-testable, quantifiable** lightweight execution reliability layer.
- **The biggest risk is building too much, not too little**: recreating capability maps, Reviewers, Ledgers, multi-agent frameworks, locks, or background services would turn an internal reliability upgrade into over-engineering. Every phase must ask three checks: Does it reinvent a wheel? Does it break compatibility? Does it add user-facing complexity?

---

## 11. Pre-Phase-2 Decisions (Awaiting User Sign-Off)

1. **Trace storage location**: Reuse existing `queue/events/{job_id}.jsonl` (extending schema with `step_id`) vs. adding `queue/trace/{run_id}.jsonl`? Recommendation: **Reuse `queue/events/`**, adding `schema_version`, `run_id`/`trace_id`/`step_id`/`parent_step_id` to avoid a new top-level concept.
2. **Standalone `scripts/core/verification.py`**: Recommended as a standalone single-responsibility adapter (reusing `sw_review` + `reviewer_gate`) rather than merging into `execution.py`.
3. **Phase 5 Worker integration depth**: Wire `queue_worker.process_job` into Execution Core in Phase 5 vs. deferring until after `scripts/core/` stabilizes? Recommendation: **Minimal integration in Phase 5**, wrapping only the `handler → verification → recovery` boundary.
4. **Optional fields in `capabilities.yaml`**: Append `risk_level`/`review_required`/... now vs. leaving YAML untouched and reading existing fields via the facade? Recommendation: **Leave YAML untouched in Phase 2**; add optional fields later only if strictly needed.

Once these four items are confirmed, proceed to Phase 2 (State + Capability Adapter + Trace).
