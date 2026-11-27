# SolidWorks 2026 Live Golden Workflow Acceptance

> **Historical Metric Note (2026-10-27)**: This document records P0-1 / P0-1.1 live-machine acceptance, where
> the "37 scenarios" deterministic eval reflects the metric scope **at that time**; the current suite has 12 workflows / 43 scenarios (baseline v4).
> Live-machine verdicts below (`mounting_bracket` dimensions, hole locations, material, tolerances) are unaffected by that count change.

Intended for automation maintainers and QA, this acceptance validates P0-1 / P0-1.1 `mounting_bracket`. Specifications are loaded from `real_acceptance_2026` in `golden-workflows.yaml`: 120 × 80 × 10 mm plate, 4 × Ø7 through-holes at X=±48, Y=±28 mm, stock library material `6061-T6`. Analytical volume is 94,460.619599741 mm³; linear tolerance 0.01 mm, volume tolerance 0.05 mm³.

## Build and Run

Requires Windows, Python 3.12, licensed SolidWorks 2026 (completed first launch), project `requirements.txt`, and `pytest`. Execute offline contract tests and the existing deterministic eval before running live CAD; the eval uses fixtures and does not prove CAD capability.

```powershell
python -X utf8 -m pytest -q -rs
python tests/evals/runner.py --output-dir output/p0-offline-eval
python tests/solidworks_golden_mounting_bracket_2026.py --output output/p0-golden-unique --runs 5
# P0-1.1：显式验收五轮正确人工门禁；业务任务仍然 blocked。
python tests/solidworks_golden_mounting_bracket_2026.py --output output/p0-11-golden-unique --runs 5 --expected-terminal blocked
```

The output root must not exist; each run uses an isolated directory and refuses overwrites. Every run saves preflight/doctor diagnostics first and verifies zero running SolidWorks processes host-wide. If a user instance is running or process status is indeterminate, the run records `BLOCKED` without modifying, closing, or killing existing instances, and never falls back automatically to Mock or OCCT.

## Acceptance Evidence

Reuses `sw_connect`, `sw_part`, `sw_sketch_quality`, `sw_measure`, `sw_review`, and `sw_export` without reimplementing COM connectors. Fully defined sketches retain driving dimensions and reject `Fix`; post-rebuild B-Rep independently verifies 1 solid body, 6 plate planar faces, 4 internal cylindrical faces, and 8 circular edges. Each hole verifies diameter, center, normal, axial length, and adjacency of circular edges to both plate faces to rule out blind holes. Because STEP import may split a cylindrical hole wall into two half-cylinders, acceptance preserves raw face/edge data while merging coaxial cylindrical areas and checking trimmed-arc lengths to prove both entrances form complete circles; missing any half-face or half-arc fails. Slot arcs are never miscounted as holes by edge count alone, and generic measurement helpers are unmodified. Also verifies analytical volume, bounding box, thickness parameter, native Boss/Cut features, and sketch health. Assigns exact stock library entry `6061-T6 (SS)` (`matid` 164), reading back material name/database and back-calculating density from real mass and volume—never treating a non-existent `6061-T6` entry or custom property as material assignment. When SW2026 Instant3D returns `ICE`, uses `GetTypeName` per official rules to read the underlying Cut type while preserving raw types and never assuming unknown types are cuts.

Saves `SLDPRT`, closes, reopens, and recaptures full evidence. `STEP` must be non-empty with an `ISO-10303-21` header and is re-imported in live SolidWorks to re-verify solid bodies and geometry. Review reuses four-view BMPs and existing rules without ignoring `WARN`/`FAIL`, unknown values, or human-review flags. After CAD completion, Execution Core adapts terminal state and trace, and Artifact Ledger records deliverables and hashes. `sha256.json` covers logs, diagnostics, geometric evidence, native part, STEP, previews, Review, report, trace, and ledger (manifest excludes self-hashing). Failures preserve artifacts and never delete logs.

Per-run cleanup closes only unsaved documents created during the run or documents located inside the run directory. `ExitApp` is called only when the run owns the PID and zero remaining documents exist, waiting for exit and comparing process snapshots. Never uses global `CloseAll`, kills by process name, or deletes user files. Failed cleanup cannot pass.

## Known Limitations

Generic `sw_review.evaluate_review_report` unconditionally returns `manual_review_required=True`. Even when all geometric checks and rule scores pass, terminal business state can only be `task_status=blocked`. Default strict `completed` mode exits non-zero; P0-1.1 explicit expected-blocked mode can report `acceptance_status=passed` and exit 0 when all independent evidence passes, without lifting the human-review requirement. Reaching unattended 5-run `completed` requires separately reviewed automated-review capability in the future.

This test does not prove other dimensions, assemblies, drawings, complex holes, mechanical material properties, or multi-version compatibility. STEP readback verifies delivered geometry without requiring native sketches or material retention. If COM hangs permanently, operators must inspect process ownership manually; the script never guesses ownership to force-kill processes.

## CI Boundaries

**Current P0-1.2 controls supersede the historical allowlist below**: protected-branch manual dispatch, hosted-runner API admission, Environment human approval, and dedicated runners. Missing configuration remains `BLOCKED`; see [Pre-Merge Readiness Report](real-golden-merge-readiness.md). The P0-1.1 constraints and outcomes below are retained as history.

Reused `windows-cad-regression.yml`, allowing access to self-hosted CAD runners solely via `workflow_dispatch` on the designated in-repo branch `test/p0-real-golden-mounting-bracket-2026`. No PR/`pull_request_target` triggers; checkout uses the triggering branch with read-only token, serial concurrency, and no cancellation of prior cleanup. Evidence is preserved by the existing `always()` upload step. Local evidence and offline results must be listed separately; 37-scenario deterministic PASS must never substitute for five live-machine runs.

The hard-coded branch acted as a safety allowlist during acceptance: even if merged into `main`, manual dispatch on `main` skipped due to job conditions, and deleting the test branch removed the live entry point. Future maintenance must explicitly review and update protected branch allowlists and runner protection rules rather than switching to arbitrary branch prefixes, PR triggers, or external checkout refs.

## P0-1.1 State Propagation Audit and Boundaries

Production code remained untouched: `sw_review.py` still outputs raw rule results and manual flags; `core/verification.py` adapts rule PASS while preserving manual requirements; `core/execution.py` reaches `completed` only on explicit `PASS` with `manual_review_required=false`, otherwise `blocked`/`failed`.

The earlier live script set summary status to `blocked` first and fed that status as the Core handler result, causing Core to classify it as a tool failure and skip Verification. Old records therefore proved zero false success at terminal state, but did not prove that Core's manual-review propagation path actually executed.

P0-1.1 separates live CAD execution facts from Review results in the test adapter: when CAD succeeds, handler reports `success=true`, raw Review is preserved intact, and adapted rule PASS + manual flag enter Verification. Expected trace is `tool.succeeded → verification.passed → run.blocked` with `Recovery=user_action_required`. Core is still called after the full CAD run and cleanup complete; reports explicitly mark `core_scope=terminal_adaptation_only` and **do not verify step-by-step CAD scheduling by Core** or introduce auto-review policies.

Schema 1.1 splits two independent outcomes: `task_status` (`completed`/`blocked`/`failed`) and `acceptance_status` (`passed`/`failed`), keeping legacy `status` as a compatibility alias for `task_status`. `--expected-terminal` defaults to `completed` (exiting non-zero while manual review remains required); explicit `blocked` mode enforces `--runs 5` and passes only when all five live runs, geometry/material/sketch/feature checks, reopen, STEP, raw Review rules, complete evidence, and cleanup pass AND Core's sole blocking reason is manual review. Unknown reasons, extra blocks, `WARN`/`FAIL`, missing files, incomplete hashes/ledgers, cleanup failures, Core/report mismatches, and duplicate instances all fail. Post-suite verification re-checks every run's on-disk artifacts so early files cannot vanish during later runs. Exit code follows `acceptance_status` and never alters `task_status`.

Evidence is sealed and verified prior to computing acceptance; after writing the final report, Ledger and hash manifest regenerate and verify without circular references. Ledger excludes itself; SHA-256 manifest includes Ledger and excludes itself. Sealing exceptions log failure and exit non-zero. Offline fault injections use synthetic contracts in temp directories and are never counted as live CAD results.

## Troubleshooting Log

- Initial offline test collection failed because `tests` is not a Python package; adopted the existing path-import convention from eval tests, after which offline tests passed.
- `output/p0-probe-01/run-01` live failure: no stock library entry named exactly `6061-T6` existed, leaving material empty with density 1000 (rejected by acceptance); also observed SW2026 feature types `Extrusion/ICE`. Fixed by resolving real stock entries and reading underlying `ICE` types via official API without altering core connection or measurement architecture.
- `output/p0-probe-02/run-01` live failure: native part and Review rules passed, but STEP readback split holes into 8 half-cylinders and 16 half-arcs, failing the original hole-count rule. Added area-merging and full-circle arc checks, with offline fault injections confirming missing half-faces/half-arcs still fail. Evidence and passing cleanup preserved for both failures.
- Generic Review's fixed manual-review flag remained enabled and continues blocking unattended completion.

## API Verification References

- [`IFeature.GetTypeName2` and Instant3D `ICE` underlying types](https://help.solidworks.com/2022/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IFeature~GetTypeName2.html)
- [`ICurveParamData` trimmed parameters](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ICurveParamData_members.html)
- [`ICurve.GetLength3` trimmed curve length](https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ICurve~GetLength3.html?format=P&value=)

## 2026-10-23 Local Execution Results

Base SHA: `f9d6efbecf297bcdfffc451de81ba3a7bdea6a0d`. Live execution SHA: `0f27516082f9df132cb42d43a2f5f9ea33b47471`. Documentation and evidence index were committed separately afterward. Environment: SolidWorks 2026 SP01.1, revision `34.1.1`, Python 3.12.10, Windows 11.

Full offline suite: **900 passed / 1 skipped** (61.43 s); skipped item is the unbuilt desktop bundled-skill release check and is not counted as passed. Deterministic mock eval matched expectations across all 37 scenarios with 0 escaped false completions; this is not a live CAD result.

| Run | Dedicated PID | Native / Reopen / STEP Geometry | Review Rules | Cleanup | Acceptance Terminal |
| --- | --- | --- | --- | --- | --- |
| 01 | 47484 | PASS | PASS / 100 | PASS | BLOCKED |
| 02 | 14168 | PASS | PASS / 100 | PASS | BLOCKED |
| 03 | 19516 | PASS | PASS / 100 | PASS | BLOCKED |
| 04 | 29352 | PASS | PASS / 100 | PASS | BLOCKED |
| 05 | 40840 | PASS | PASS / 100 | PASS | BLOCKED |

All five runs produced 1 solid body with native-reopen and STEP readback volume **94,460.6196 mm³**, four Ø7 holes at (±48, ±28) mm, two fully defined sketches with no `Fix` or dangling items, and material `6061-T6 (SS)` at 2700 kg/m³. Pre-launch and post-exit process snapshots were empty with 0 remaining open documents. All 17 file hashes per run (85 total) and Artifact Ledgers re-verified cleanly.

**P0-1 did not reach completion: 0/5 completed, 5/5 blocked.** The sole remaining acceptance blocker was generic Review's `manual_review_required=True`, which was neither disabled nor silently treated as passing; the live command exited 1 by design. No GitHub self-hosted runner was executed, and other versions, specifications, or unattended delivery were not verified. No merge was performed.

Working directory: `<repo>\p0-real-golden-2026`.

```text
output/p0-final-five-01/summary.json
output/p0-final-five-01/run-01 ... run-05/
output/p0-probe-01/run-01/              # 首次真机失败证据
output/p0-probe-02/run-01/              # STEP 分面排错证据
output/p0-offline/                     # 离线日志和 deterministic eval
output/p0-evidence-20261023.zip         # 全部报告、日志、CAD、预览、hash
```

Evidence archive SHA-256: `01b6f43954d6304c5f72c3de99a6ecf6206333347063cec3cae5dd1b1fd9071a`. Native/STEP binaries and BMPs are not committed to Git; the reviewable [structured index](evidence/p0-real-golden-2026-10-23.json) holds per-run report and manifest SHA-256 hashes. [Draft PR #39](https://github.com/wzyn20051216/solidworks-automation-skill/pull/39).

## 2026-10-23 P0-1.1 Re-Verification Results

Stage start: `13e22ca5244b808d04fde2a51346c800aa8a52d1`; execution SHA: `6e8903cdea3cdf36b0e4fe15e55779cdc663ac39`. Production Review, Verification, and Execution Core were untouched, and historical P0-1 reports and failure evidence remained intact.

Full offline regression: **942 passed / 1 skipped** (66.42 s); skipped due to unbuilt desktop bundled skill, accompanied by a UTF-8 log note. Deterministic mock eval passed all 37 scenarios with 0 escaped false completions (offline contract check only, not a substitute for live results below). Added fault injections cover wrong hole diameters/positions, STEP hole diameters, material/sketches, Review FAIL/WARN/unknown, missing manual flags, cleanup failures, residual documents/processes, user-instance ownership, license blocks, missing artifacts, incomplete hashes/ledgers, wrong terminal states, wrong manual flags, duplicate PIDs, fewer than 5 runs, and final sealing failures. CLI contract tests confirmed only expected blocking returns 0, critical injected faults exit non-zero, and default `completed` mode exits non-zero.

Actual command executed (output directory did not exist beforehand); exit code **0**:

```powershell
python -X utf8 tests/solidworks_golden_mounting_bracket_2026.py --output output/p0-11-real-five-01 --runs 5 --expected-terminal blocked
```

| Run | Dedicated PID | Geometry / Delivery / Evidence / Cleanup | `task_status` | `acceptance_status` | Manual Review |
| --- | --- | --- | --- | --- | --- |
| 01 | 39596 | PASS | blocked | passed | true |
| 02 | 46956 | PASS | blocked | passed | true |
| 03 | 41440 | PASS | blocked | passed | true |
| 04 | 22712 | PASS | blocked | passed | true |
| 05 | 20972 | PASS | blocked | passed | true |

Five-run live geometry pass rate **5/5 (100%)**; expected-gate accuracy **5/5 (100%)**; Task Completion **0**; Test Acceptance **5**; False Completion **0**; safe cleanup **5/5 (100%)**. All five runs used SolidWorks 2026 revision 34.1.1 with native-reopen and STEP volume 94,460.6196 mm³. All five traces contained `tool.succeeded → verification.passed → run.blocked`, `Verification=PASS`, `manual_review_required=true`, `Recovery=user_action_required`, and no `tool.failed` or `run.completed`. Every run recorded only `EXPECTED_MANUAL_REVIEW_REQUIRED` with raw Review rules at PASS / 100.

All evidence re-verified at suite end and pre-delivery: 85 file SHA-256 hashes and Artifact Ledgers passed, process snapshot empty, 0 residual documents. Running the strict `completed` gate against the same live evidence yielded `acceptance_status=failed` and `task_status=blocked` without modifying original live records. Zero live-run failures occurred in this stage; all fault injections ran in offline temp directories without altering live CAD or raw evidence.

```text
output/p0-11-real-five-01/summary.json
output/p0-11-real-five-01/run-01 ... run-05/
output/p0-11-real-console.log
output/p0-11-real-exitcode.txt
output/p0-11-offline/pytest-full.log
output/p0-11-offline/eval/eval_report.json
output/p0-11-offline/real-evidence-strict-control.json
output/p0-11-evidence-sha256.json
output/p0-11-evidence-20261023.zip
```

Full evidence archive SHA-256: `bc8c055c7ce314f3d148a43ce3d7dbd5ff8b9ef3a4c6519ddd3a234dd26a01c0`. The [P0-1.1 structured index](evidence/p0-11-real-golden-2026-10-23.json) records per-run report and manifest hashes. This stage completed **test-status stratification and expected-gate acceptance**; unattended review was not enabled, step-by-step Core scheduling of live CAD was not verified, and remote self-hosted CAD runners were not executed. See above for merge-maintenance limitations of the hard-coded branch.
