# P0-1.2 Pre-Merge Readiness Report

> **PR Number Alignment (2026-10-27)**: This document was authored at P0-1.2 when **PR #39** was active.
> The current stage is P0-2.1 with active **PR #43** (Draft, based on P0-2 branch `test/p0-real-assembly-gripper-2026`).
> Intermediate **PR #42** represents P0-2. All three are stacked Drafts and none merge into `main`.
> All other conclusions below (`BLOCKED`, required GitHub configuration) apply equally to #43.

**Merge readiness: BLOCKED. Keep Draft PR #39 open; merging into `main` is not recommended at this time.**
One-off test-branch restrictions were removed in code, but actual GitHub permissions and environment protections do not yet meet full security prerequisites.
No Environment, Secret, or Runner was created in this stage, and neither repository settings nor `main` were modified.

## Governance Standard Adjustment Record (2026-10-27)

The main body preserves original P0-1.2 requirements **without deleting or rewriting historical items**. However, requirements such as "at least one approving reviewer" and "requires a second eligible approver" have been formally adjusted to match the project's real governance model; read the admission criteria below alongside this section.

| Item | Original Requirement (P0-1.2) | Adjusted Standard (Single-Maintainer Mode) |
| --- | --- | --- |
| Branch rules | Ruleset requires >= 1 approval + required status checks | Ruleset `active`; **must enter `main` via Pull Request**; required status checks include `test-and-build`; **`bypass_actors` must be empty** (unreadable by read-only tokens; evidenced via maintainer offline signed attestation). Approval count may be `0` |
| Independent reviewer | Environment requires Required reviewers + Prevent self-review with a second eligible human approver | Not a hard admission gate. Absence is recorded as a **residual risk** and must never be claimed as "independent approval passed" |
| Governance posture | Assumed two-person review | Single core maintainer + open community contributions; owner decides merges without claiming two-person review |

**Rationale**: The repository has a single maintainer, with external contributions arriving via Fork + PR. Mandating an independent approver produces two broken outcomes—either keeping maintainer bypass (rules become theater / false compliance) or removing bypass without a second reviewer (every PR deadlocks). Neither delivers real security value.

**Impact**: `scripts/ci/cad_ci_guard.cjs` refactored admission checks (`reviewed_ruleset` split into `ruleset_active` + `pull_request_required` + `required_status_checks_present`; `independent_human_review` moved from hard gate to `governance.remaining_risks` disclosure).

**2026-10-27 Addendum (Phase 2.1.2)**: Renamed the bypass check to **`no_bypass_actors`** with semantics **list must be empty** (rather than "forbid owner only"), aligned across code, tests, this document, and `CONTRIBUTING.md`. A single-maintainer repo has no legitimate permanent bypass actor, and "forbid owner only" would miss a newly added collaborator with bypass rights. In addition:

- Added `protected_ref_is_main`: `ref_protected` only confirms the branch is protected, not that it is specifically `main`, so `main` is asserted explicitly.
- Switched `bypass_actors` evidence to **offline capture + Ed25519 signed attestation** verified read-only by CI with zero write permissions; because the attestation is self-signed by the maintainer with an in-repo trust root, it **does not constitute an independent audit** (see [`governance-attestation.md`](governance-attestation.md)).

Reviewer descriptions in Sections 3, 5, and "Actual GitHub Settings and Manual Prerequisites" below must be read under this updated standard.

**2026-10-27 Addendum (Full Hardening V2 / B1)**: Tightened the governance chain further, expanding admission checks from 24 to **28**:

- **Trust anchor**: Added `trust_root_anchor`, reading repository variable `GOVERNANCE_TRUST_ROOT_ANCHOR` and comparing it against the computed trust root. Prevents atomic replacement of "public key + rotation log + attestation"; missing, malformed, or mismatched values unconditionally block. Limitation: a repository admin can modify the variable too, so it is still **not** an independent root of trust.
- **Dual digests**: Split legacy single `config_digest` into `policy_digest` (rule definitions excluding bypass) and `snapshot_digest` (including bypass and `updated_at`). **Never use an unchanged `policy_digest` to claim the full configuration is unchanged.**
- **Compliance fields**: Added `compliant` / `noncompliance_reasons` into the signed payload; capture refuses to sign by default when remote state is non-compliant (writes no file, exits non-zero), and verification strictly requires `compliant === true` matching recomputed compliance.
- **Rotation log**: Retired keys must have an explicit `revoked_at` (omission is not treated as revoked); `KEYS` and the rotation log must match bidirectionally.
- **CODEOWNERS downgrade**: Added `.github/CODEOWNERS` declaring ownership while keeping `require_code_owner_review = false`. **The file alone is not an enforced gate**, disclosed under governance risk `code_owner_review_not_enforced`.
- **Drift detection**: Integrated `check_governance_drift.cjs` into `test-and-build` so edits to governance code/workflows/trust root/attestation surface as explicit diffs. Because it **cannot block** someone with merge rights from editing both together, governance risk discloses `trusted_baseline_workflow_not_established`.

Specification details (fields, invalidation rules, rotation steps) are defined authoritatively in [`governance-attestation.md`](governance-attestation.md).

**Residual risks (uneliminated, must be accepted in writing)**: (1) No independent review; merge quality relies on single-maintainer judgment. (2) No second Environment approver; deployment approval cannot be gated by another person. (3) As repository admin, the maintainer can still temporarily modify rulesets—no GitHub setting eliminates inherent admin authority. (4) External PR reviews may lack GitHub review trails unless reinforced by process or `required_review_thread_resolution`.

**Unchanged**: Environment / Runner / Secret prerequisites and execution evidence requirements for remote CAD CI remain unchanged; this adjustment **does not clear** B-01.

## Complete PR Audit Relative to `main`

Starting commit `b2dbd38f6405466ab5e0cc331bd4cb9c8ca39104`, `main` base `f9d6efbecf297bcdfffc451de81ba3a7bdea6a0d`.

| Original PR Change | Audit Conclusion & Current Handling |
| --- | --- |
| `golden-workflows.yaml` | Adds fixed live-machine spec for `mounting_bracket` only; 2026 version and dimensions are verified case boundaries and cannot be overridden via runtime config. |
| Mounting-bracket live script | Preserves model and production interfaces; adds portable config, side-effect-free diagnostics, PID creation timestamps, safe evidence paths, and strict trace correlation. |
| Mounting-bracket offline tests | Retains all false-success rejection cases; adds shared entry, config, link, and PID-reuse fault injections. Synthetic inputs are excluded from live statistics. |
| Windows CAD Workflow | Original hard-coded test branch could not run after merge; replaced with protected branch, actor authorization, environment checks, and Environment human approval. |
| Acceptance docs | Older sections kept as historical records; current spec is defined by this document and P0-1.2 sections. |
| Two historical evidence indexes | Absolute paths record historical provenance rather than execution dependencies; old runs are neither rewritten, migrated, nor claimed compliant with the new protocol. |

Production `scripts/sw_review.py`, `scripts/core/verification.py`, and `scripts/core/execution.py` were not modified and no auto-approval was introduced. Core continues performing terminal adaptation after CAD and cleanup finish and cannot be claimed to schedule live modeling steps.

## Maintainable Manual CI Admission

`windows-cad-regression.yml` supports `workflow_dispatch` only, with no PR or `pull_request_target` live triggers. Stage 1 runs on GitHub-hosted Ubuntu to verify the following facts—any unknown state or API failure blocks before any self-hosted CAD Runner is allocated:

1. Repository name and immutable ID match the trusted repo; ref must be a protected branch (tags rejected).
2. GitHub API confirms branch protection and that branch `HEAD` equals the triggered SHA, rejecting moved branches.
3. Active ruleset requires at least one approval and required status checks. (**Adjusted 2026-10-27**: under single-maintainer mode, requires active ruleset + mandatory PR + required status check `test-and-build` + empty `bypass_actors`; approval count may be 0. See Governance Standard Adjustment Record.)
4. Both triggering actor and rerunner hold `admin` or `maintain` permission; standard `write`/`read` is insufficient.
5. `cad-validation` exists with Required reviewers, Prevent self-review, and protected-branch-only deployment. (**Adjusted 2026-10-27**: Environment existence and protected-branch policy remain hard gates; Required reviewers / Prevent self-review are unreachable in single-maintainer mode and disclosed as residual risks instead of standalone blocks. See Governance Standard Adjustment Record.)
6. API shows an idle, online Windows CAD Runner with matching labels. Incomplete pagination is never assumed passing.

Only after admission passes does the CAD job enter server-side human approval in `environment: cad-validation`—never "schedule on the self-hosted runner first, then reject on-host". Checkout pins the trigger SHA with no persisted Git credentials and creates a fresh directory per `run_id`/`run_attempt`; pre-existing directories immediately `BLOCK` without deleting user files. Full offline regressions and deterministic eval run prior to live CAD with UTF-8 enforced across parent/child Python processes. Legacy SolidWorks/AutoCAD regressions remain opt-in inputs, and the default Golden case does not depend on AutoCAD. All third-party Actions in this workflow are pinned to verified full SHAs and validated with `actionlint`.

Admission passage confirms only that the workflow may enter approval—it does not prove complete runner isolation; reports always state `scope=workflow_admission_only` and `safety_acceptance_complete=false`. Neither an environment check PASS nor a local live PASS may be reported as completed remote security acceptance.

## Actual GitHub Settings and Manual Prerequisites

Read-only audit observed a public personal repository where `main`'s ruleset is active with 0 required approvals, `cad-validation` does not exist, runner count is 0, and `CAD_CI_AUDIT_TOKEN` is unconfigured. Admission is therefore `BLOCKED` and remote CAD CI has not executed.

The administrator must complete and provide verifiable evidence for:

- Apply a ruleset to `main` and live-run branches requiring >= 1 approval, required CI, and restrictions on force-push and deletion; audit bypass lists and protect workflow, guard script, and CAD test sources.
  (**Adjusted 2026-10-27**: approval count requirement removed in favor of mandatory PR + required CI + **empty bypass list**; force-push and deletion protections unchanged. See Governance Standard Adjustment Record.)
- Create `cad-validation` with Required reviewers, Prevent self-review, protected-branch-only policy, and admin bypass disabled in UI, requiring a second eligible approver beyond the trigger actor.
  (**Adjusted 2026-10-27**: no second approver exists in single-maintainer mode. Environment existence and protected-branch restriction remain hard gates; Required reviewers / Prevent self-review are disclosed as residual risks. Remote CAD CI remains **unreachable** under this posture, keeping B-01 `BLOCKED` pending manual disposition. See Governance Standard Adjustment Record.)
- Configure `CAD_CI_AUDIT_TOKEN` scoped strictly to this repository with `Administration:read`, `Actions:read`, and `Metadata:read`, zero write permissions, short TTL, and a rotation owner. Standard `GITHUB_TOKEN` lacks `Administration:read` needed for runner listing—never assume it suffices or skip verification. The token enters only the hosted admission script, never the CAD job or logs; no token was created in this stage.
- Provision a dedicated, isolated Windows CAD Runner with proper labels, 64-bit Python, licensed SW2026, templates, material libraries, and an interactive desktop; never register a daily-driver workstation as a persistent public-repo runner.
- **Solve cross-workflow isolation independently**: `if` guards and Environments in this workflow cannot constrain a separate workflow added by a malicious PR. Use a Runner Group restricted to specific repositories and workflows, or review a trusted private control-repo / isolation design. Public personal repos cannot assume org-level Runner Groups exist. Also review external-contributor workflow approval, runner network/credential isolation, and post-failure cleanup procedures.
- Finally, execute the remote workflow end-to-end with an authorized actor, protected branch, and independent approval—verifying unauthorized rejection, approval blocking, artifact upload, and failure cleanup—before re-evaluating `READY`. Local results cannot substitute for this step.

Do not modify these security settings automatically for this PR; they are unfulfilled manual prerequisites.

## Reusable Entry Point, Configuration, and Evidence Protocol

```powershell
$env:PYTHONUTF8 = '1'
python -m pytest -q -rs
node --test tests/test_cad_ci_guard.cjs
python tests/evals/runner.py --output-dir output/offline-unique
python tests/solidworks_golden_workflow.py --case mounting_bracket --output output/golden-unique --runs 5 --expected-terminal blocked
```

The shared entry point dispatches only reviewed modules registered in `CASE_REGISTRY`, never arbitrary Python paths or alternate backends. The legacy mounting-bracket entry remains compatible; new cases must register contracts, model acceptance, and corresponding fault evidence rather than inheriting verification tiers automatically. Default mode remains strict `completed`; explicit `blocked` mode requires 5 runs and returns `acceptance_status=passed`, `task_status=blocked`, `manual_review_required=true` only when human review is the sole blocker.

`--runtime-config` reads JSON permitting only `part_template`, `material_database`, `connect_timeout_seconds` (5..120), and `cleanup_timeout_seconds` (5..60). Paths resolve relative to the config file; default templates reuse existing discovery, and material databases search English/Simplified Chinese libraries under the diagnosed install path. Case versions, material entries, dimensions, tolerances, and approval requirements cannot be overridden via config. Resolved paths and SHA-256 hashes are recorded without treating the library hash as material certification. Missing Windows/64-bit Python/COM dependencies, unreadable configs, or missing files emit explicit `BLOCKED` / `acceptance failed` reports without installing fallback backends.

Schema 1.2 extends dual-status, raw Review, Core, Ledger, hashes, and geometry evidence with `runtime_config.json`, `runtime_diagnostics.json`, OS process creation timestamps, and a globally unique `trace_run_id`. Even identically named `run-01` folders cannot copy traces across suites, and Ledger `runId` matches Core. PID + creation time jointly identify instances to avoid false failures from Windows PID reuse. Core traces must share one run/step, match verification copies, follow valid event order, and emit exactly one terminal event. Symlinks, junctions, hard links, and out-of-bounds paths are rejected prior to hashing or writing, and fallback write paths on report-write failure cannot overwrite external files.

The output directory must not exist; duplicate runs are rejected immediately without overwriting historical evidence. Teardown closes only documents owned by the current run and requests `ExitApp` only when the run owns the process and zero unknown documents remain—never killing processes globally. Permanent hangs inside a single COM call cannot be fully solved by connect/cleanup timeouts; operators must inspect ownership after aborts rather than treating unknown cleanup outcomes as passing.

## Verification References

- [GitHub Environments REST API and permissions](https://docs.github.com/en/rest/deployments/environments)
- [`Administration:read` required for self-hosted runner listing](https://docs.github.com/en/rest/actions/self-hosted-runners)
- [Runner group workflow access restrictions and public repository risks](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access)

## Complete File Manifest for This Stage

The 12 files below are P0-1.2 changes; relative to `main`, the PR also includes `golden-workflows.yaml` and two historical evidence indexes (15 files total). Historical indexes are excluded from this stage's new-protocol pass counts.

```text
.github/actionlint.yaml
.github/workflows/windows-cad-regression.yml
scripts/ci/cad_ci_guard.cjs
tests/golden_workflow_support.py
tests/solidworks_golden_workflow.py
tests/solidworks_golden_mounting_bracket_2026.py
tests/test_solidworks_golden_mounting_bracket_2026.py
tests/test_golden_workflow_support.py
tests/test_cad_ci_guard.cjs
docs/architecture/real-golden-workflow-acceptance.md
docs/architecture/real-golden-merge-readiness.md
docs/architecture/evidence/p0-12-real-golden-2026-10-23.json
```

## Failure and Remediation Log

- New "missing config" test failed initially, exposing that the test adapter passed `success=false` alongside `blocked`, causing Core to classify it as a tool failure. Fixed pre-flight blocks to pass `blocked` only without modifying production Core; this case remains `task blocked` / `acceptance failed` and cannot pass `expected-terminal` mode.
- First full run hit 6 failed / 956 passed / 1 skipped due to UTF-8 vs. GBK decoding mismatches across Windows parent/child processes in six legacy CLI tests. Enforcing `PYTHONUTF8=1` passed the full suite; original failure log preserved.
- First `actionlint` run rejected custom CAD runner labels; adding project config resolved it, with the original failure log preserved.
- One auxiliary process probe mistakenly imported a non-existent `sw_api` module and was switched to existing `scripts.sw_process`; the probe neither launched nor closed CAD. All development fault injections used synthetic inputs and are excluded from live CAD stats.

Added regressions cover symlink/hardlink guards, cross-suite trace swaps, out-of-order events, wrong step IDs, multiple terminal events, mismatched Verification copies, PID reuse, duplicate directories, and disallowed config keys. Existing regressions for wrong hole diameters/positions, missing artifacts, Review WARN/FAIL, cleanup failures, Ledger/hash checks, and non-zero CLI exits remain intact.

## Actual Acceptance Results (2026-10-23)

Live execution commit: `bbdda7c00f077f58baeffe97e075666b078dfe7e`; subsequent commits added only documentation and evidence indexes.

- Full offline suite: **963 passed / 1 skipped** (104.44 s). The skipped item is the existing release check for unbuilt desktop bundled skills and was not counted as passing.
- CI policy: **26/26** synthetic snapshot fault-injection tests passed; `actionlint` passed. These are not remote authorized execution records.
- Deterministic mock eval: **37** scenarios matched expectations with **0** escaped false completions, stored separately under `offline/eval` and excluded from live CAD figures below.
- Local live **SolidWorks 2026 SP01.1 (34.1.1)**: all five independent runs passed acceptance with command exit code **0**.

| Run | Actual PID | Native / STEP Volume (mm³) | `task_status` | `acceptance_status` | Cleanup |
| --- | --- | --- | --- | --- | --- |
| 1 | 48492 | 94460.6196 / 94460.6196 | blocked | passed | PASS |
| 2 | 12520 | 94460.6196 / 94460.6196 | blocked | passed | PASS |
| 3 | 43636 | 94460.6196 / 94460.6196 | blocked | passed | PASS |
| 4 | 47668 | 94460.6196 / 94460.6196 | blocked | passed | PASS |
| 5 | 49280 | 94460.6196 / 94460.6196 | blocked | passed | PASS |

All five runs verified actual 120×80×10 mm dimensions, four Ø7 through-holes at ±48/±28 mm, material and density readback, two fully defined sketches, feature health, SLDPRT save-and-reopen, STEP re-import readback, and four-view previews. All Review rules scored PASS / 100 with `manual_review_required=true`; Core verification passed with terminal state `run.blocked`, `Recovery=user_action_required`, and sole blocker `EXPECTED_MANUAL_REVIEW_REQUIRED`.

Geometry pass rate **5/5 (100%)**; expected-gate accuracy **5/5 (100%)**; Task Completion **0**; Test Acceptance **5**; False Completion **0**; cleanup pass rate **5/5 (100%)**. Each run had a distinct PID + creation time and `trace_run_id`, left zero residual SolidWorks test documents or processes, and did not close any existing user instance. All 19 files per run (**95 SHA-256 hashes** total) matched Ledger, raw Review, snapshots, and Core traces on re-read. Zero live-run failures occurred across the five runs; all development failure logs remain preserved. Re-evaluating the same live evidence under strict `completed` mode still yielded `acceptance failed` / `task blocked` without launching CAD or altering original reports.

Actual command executed (working directory = repository root):

```powershell
$env:PYTHONUTF8 = '1'
python tests/solidworks_golden_workflow.py --case mounting_bracket --output output/p0-12-real-five-01 --runs 5 --expected-terminal blocked --runtime-config output/p0-12-runtime.json
```

> This records the actual command executed at the time; `output/p0-12-runtime.json` is an uncommitted local config.
> For external reproduction, use `config/runtime.example.json` (`null` paths = auto-discovery) and a new non-existent output directory.

The JSON config explicitly pointed to the locally installed stock material database while templates used auto-discovery; install paths and library hashes are logged in reports rather than hard-coded as defaults. Results cover only this 2026 installation and exact material entry, with no claim for other versions.

Evidence locations:

```text
<worktree-p0-real-golden-2026>/output/p0-12-real-five-01
<worktree-p0-real-golden-2026>/output/p0-12-offline
<worktree-p0-real-golden-2026>/output/p0-12-evidence-20261023.zip
```

> These artifacts were produced in a dedicated P0-1.2 worktree (`p0-real-golden-2026`); the path varies by local disk layout and is represented with a placeholder. The archive is uncommitted and retained locally by the maintainer.

Evidence archive contains 121 files (including master hash manifest); SHA-256:

```text
ce64a118beef1ac562641a61698b301fc793ef6a81084327988226f89a6af7ed
```

The [stage evidence index](evidence/p0-12-real-golden-2026-10-23.json) records per-run report hashes, instance creation timestamps, unique traces, effective config, and GitHub settings snapshots. Complete CAD files, previews, and failure logs reside in the local archive; large binaries were neither committed to Git nor uploaded to remote CI. Both prior historical evidence stages remain untouched.

**Merge recommendation remains BLOCKED**: local acceptance and code regressions passed, but required GitHub settings, runner isolation evidence, and live remote execution for controlled remote CI are still missing; keep the PR in Draft. Scope limitations also remain for Core terminal-adaptation-only coverage, permanent COM hang recovery, and unverified unattended automated review.
