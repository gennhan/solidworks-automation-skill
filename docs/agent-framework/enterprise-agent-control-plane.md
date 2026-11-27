# CAD Studio Enterprise Agent Control Plane

## Positioning

CAD Studio does not bolt an LLM directly inside CAD software; it serves as an agent control plane for mechanical engineers:

```text
图形化配置 -> 企业任务契约 -> Codex 执行 -> Skill/工具链 -> 审核门禁 -> 交付回写
```

Codex remains the final executor, and the `solidworks-automation` skill is the core capability bundle. The UI translates user intent into auditable, reusable, and replayable job tickets.

## Reference Patterns Adopted

Adopted from educational/framework projects such as `datawhalechina/hello-agents`:

- Core agent abstractions: roles, tools, memory, context, protocols, and evaluation.
- Upgrading from single-turn prompts to reusable workflows.
- Grounding framework capabilities in real engineering use cases.

Adopted from fuller frameworks such as Hermes Agent:

- Long-running workers.
- Layered Agent Profile / Skill / Memory architecture.
- Multi-agent delegation and review.
- Gateways, auditing, permissions, and rollback-capable execution.

Rather than copying a generic agent framework wholesale, this project narrows the design to vertical CAD/Skills workflows.

## Module Boundaries

- **UI**: Collects configuration, displays queues, and renders prompt previews and execution results.
- **Queue**: Persists jobs as JSON for offline recoverability.
- **Agent Contract**: Compiles Agent Profile, Policy, Prompt, and Output Schema.
- **Worker**: Polls the queue and dispatches mock / Codex / CAD handlers.
- **Codex Executor**: Invokes `codex exec`, enforces skill loading, and produces structured outputs.
- **Reviewer Gate**: Checks real hole cuts, engineering drawings (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, retaining `GB/T` as a secondary reference), tests, Git status, and deliverables.
- **Artifact Store**: Stores Codex outputs, CAD files, review reports, and queue logs.

## Current Implementation Status

Implemented:

- Tauri local queue.
- Python worker.
- `executor: "codex"` bridge.
- Codex Bridge UI.
- Agent Profile and prompt compiler.
- Final Codex response JSON schema.
- Versioned job schema.
- Default `workspace-write` sandbox, workspace allowlist, and fixed output directory.
- JSON queue claim lock, lease, stale-running recovery, and malformed-job quarantine.
- In-flight heartbeat lease renewal, cancellation semantics, JSONL event streams, and persisted stdout/stderr logs.
- Policy Gate human approval state covering `git push`, full-access sandbox, CAD macros, external network, cross-workspace writes, and file deletion.
- Approval-scope re-verification: if a job's risk reasons change after approval, the worker intercepts it again.
- Artifact Ledger: automatically records deliverable paths, existence, sizes, and SHA-256 hashes for successful jobs.
- Worker Control: desktop UI can start/stop the local Python worker and display live status and PID.
- Worker Health: worker writes health heartbeats, queue counts, recovery counts, and recent errors.
- Reviewer Gate: generates deliverable review reports from the Artifact Ledger and performs lightweight format header checks on STEP/STL/DXF/PDF/DWG.

Not yet implemented:

- In-app start/stop worker *(historical item; superseded by Worker Control above)*.
- Real-time queue log streaming.
- Multi-agent parallel/review scheduling.
- Memory and enterprise RBAC permissions.
- Production-grade rollback for live CAD executors.
- HMAC signatures and an immutable audit ledger.

## Minimal Enterprise Principles

- Every job must be backed by structured JSON.
- Every execution must produce output files.
- Every Codex invocation must reference the skill path.
- Every delivery must include verification records.
- Real manufacturing files must pass the Reviewer Gate.
- Engineering options left unspecified by the user default to `auto_best`, allowing AI to select the best approach while recording rationale and residual risks.
- Codex execution must be explicitly enabled and never runs silently by default.
- `danger-full-access` requires both job approval and the worker `--codex-full-access` flag; it can never be a default.
- Frontend job JSON is untrusted; Policy Gate must be enforced at the worker/control-plane layer.

## Policy Gate

Policy Gate prevents hazardous actions from being executed silently with one click in the UI. When a Codex job enters the worker, it checks the following before invoking `codex exec`:

- `policy.approval == "manual-required"`.
- `policy.requirePush == true` or UI setting `commitAndPush == true`.
- `policy.sandbox == "danger-full-access"`.
- `capabilities` includes `git_push`, `full_access`, `cad_macro`, `external_network`, `cross_workspace`, or `delete_files`.

When triggered, the job enters `approval_required`, and the worker writes `approvalReasons` and a `policy.approval_required` event. After desktop approval writes `approvedAt`, `approvedBy`, and `approvedPolicyReasons` and returns the job to `queued`, the worker recomputes approval reasons and proceeds only if current reasons match the approved set.

## Artifact Ledger

The Artifact Ledger is the prerequisite for the Reviewer Gate. After a job succeeds, the worker aggregates `result.outputPath`, `result.outputs`, `result.artifacts`, and job-level `artifacts` into `queue/ledgers/{job_id}.ledger.json`, recording:

- Deliverable kind and path.
- File existence and directory flag.
- File size and SHA-256 hash.
- Execution result message and verification summary.

The ledger records facts only and does not replace manufacturing-grade acceptance. Live CAD handlers must still verify that P0 files (STEP/STL/DWG/PDF, etc.) genuinely exist, open cleanly, and are manufacturable before marking `passed`.

## Worker Health

The worker writes `queue/worker_health.json` with heartbeats, process PID, queue state statistics, current-cycle processed count, stale-running recovery count, and recent errors. Reading this file lets the desktop UI separate process liveness from queue health: a live process does not mean healthy jobs, and failed or approval-pending jobs must be surfaced clearly.

## Reviewer Gate

The Reviewer Gate currently performs deliverable existence verification and lightweight format inspection, writing reports to `queue/reviews/{job_id}.review.json`. It verifies whether deliverables are declared, exist, are non-empty, and have SHA-256 hashes, and inspects file headers or structural markers for STEP/STP, STL, DXF, PDF, and DWG. Because SLDPRT is proprietary, it currently logs a warning until native SolidWorks open-and-verify checks are integrated.

## Near-Term Roadmap

1. **Queue Store**: Add an event-stream UI timeline, in-flight retry policies, and queue health indicators.
2. **Reviewer Gate**: Add native SolidWorks/AutoCAD open checks, drawing dimension-chain verification, and real-hole verification for 3D printing.
3. **Worker Health**: Persist crash reasons, add queue health scoring, and display a UI timeline.
4. **UI**: Replace raw Prompt Preview with an execution plan, gate summary, and impact scope, moving raw prompts to Advanced Details.
5. **Multi-Agent**: Introduce a three-stage Planner/Executor/Reviewer flow focused on traceability and acceptance rather than multi-process complexity.
