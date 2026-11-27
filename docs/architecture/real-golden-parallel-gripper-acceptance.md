# P0-2: Two-Finger Parallel Gripper Native Assembly Golden

This case verifies structural geometry, native assembly mating, and delivery consistency only. It makes no claims regarding motors, leadscrews, timing belts, synchronized actuation, load capacity, or manufacturing release. Neither P0-1.2's mounting-bracket acceptance scope nor production Review / Execution Core security gates are expanded.

## Branch and Execution Boundaries

- Working branch: `test/p0-real-assembly-gripper-2026`.
- Stacked Base: `818087a366efdd830d85b37d0705dd2d873464eb` from the latest P0-1.2 development branch.
- Draft PR targets `test/p0-real-golden-mounting-bracket-2026`; does not merge #39 and modifies neither `main` nor GitHub settings.
- COM write operations run serially; the original engineering DAG is stored in per-run `engineering_plan.json`, excluding Motion, manufacturing drawings, and drive transmission.
- Core performs terminal adaptation only after CAD execution and safe cleanup: `core_scope=terminal_adaptation_only`.

## Unified Specification (mm)

The single source of truth is `parallel_gripper_assembly` in `golden-workflows.yaml`; dimensions, tolerances, version, and approval rules cannot be overridden at runtime.

| Part File | Qty | Native Geometry and Placement |
| --- | --- | --- |
| `base.SLDPRT` | 1 | 60×12×140; local profile center (0,-32), bottom face z=0; instance origin z=-70 |
| `rod.SLDPRT` | 2 | Ø8×140 cylinder along Z; instances at X=-18/+18, Y=0, Z=-70 |
| `support.SLDPRT` | 2 | 60×34×12, profile center (0,-9); two Ø8.02 through-holes at X=-18/+18, Y=0; instances at Z=-70/+58 |
| `slider.SLDPRT` | 2 | 52×20×18, profile center (0,0); two Ø8.1 through-holes at X=-18/+18, Y=0; instances at Z=-43/+25 |
| `finger.SLDPRT` | 2 | 12×30×18, profile center (0,25); follows corresponding slider, origin Z=-43/+25 |

All five parts are parametric bosses; supports and sliders add hole sketches and through-cuts. Fully defined sketches, editable depth parameters, library material `6061-T6 (SS)`, density, and B-Rep readback are all verified. Materials and clearances here are nominal structural Golden parameters and do not replace material certification, guide-rod hardness/wear requirements, bearing selection, tolerance chains, or fastener design.

Guide-rod center distance is 36 mm; initial jaw opening along Z is 50 mm. Support bottom faces mate against the base at y=-26, and fingers join sliders at y=10. Manufacturability still requires mounting/clamping fasteners, travel stops, axial retention, lubrication, actuation, and load engineering.

## Native Mates and Degrees of Freedom

Only the base is fixed; no other component uses the `Fixed` attribute in place of Mates:

- Each support has 3 reference-plane Mates; right end uses axial distance 128, all others coincident.
- Each guide rod has 1 concentric Mate (to left support bore), 1 axial coincident plane Mate, and 1 angular parallel Mate.
- Each slider has concentric Mates to both guide rods; two non-coaxial concentric constraints jointly lock rotation, leaving only axial translation along Z.
- Each finger has 3 coincident reference-plane Mates to its slider.

22 genuine Mates in total. Initial transforms are used solely for insertion placement; acceptance reads back `MateGroup`, `Mate2` types, suppression/health, `MateEntity2` component IDs and entity parameters, plus component transforms, fixed flags, constraint status, and unique instance IDs.

`GetConstrainedStatus` proves overall constraint state only and cannot by itself prove DOF counts. Target DOFs are proven jointly by the two associated axes of the dual-rod concentric Mates, rigid planar finger Mates, fully constrained static parts, and a native 6-axis `SetTransformAndSolve2` probe. Each slider runs ±2 mm Z translation plus X/Y translation and X/Y/Z rotation requests (14 probes total): only Z translation with finger follow-through is permitted, the opposing group and static parts must remain stationary, all five other axes must remain constrained, and each probe restores position afterward. Constrained-axis requests may be projected by the native solver into valid Z sliding, but lateral shift and rotation must remain zero. Every probe builds a `MathTransform` via `SAFEARRAY(double)` and reads back all 16 elements so invalid `ArrayData` writes are never mistaken for valid requests. Motion probing never falls back to raw `Transform2` assignment; unreadable or unproven states fail acceptance rather than substituting visual inspection.

Because online docs for `GetRemainingDOFs` are incomplete, its 12 `out` parameters were verified against local `sldworks.tlb` / Interop assemblies with raw signatures saved offline. First-run empirical testing showed its return value is not a DOF count and its status does not map directly to `swDofStatus_e`; therefore only raw SDK diagnostics and consistency checks are recorded without reporting it as a direct DOF count. Kinematic constraint verdicts rely on the native Mates and 6-axis probes above, still require human engineering review, and claim no cross-version support for undocumented private semantics.

## Assembly, Interference, and Delivery Acceptance

Each run creates a fresh directory and fresh SolidWorks instance after rejecting any pre-existing or unknown SolidWorks process. Parts are saved, closed, and reopened individually before building the assembly; the assembly and loaded references are saved, closed, and reopened from disk, asserting that every reference resides in the current run's `parts` folder with matching hashes.

Interference reuses `sw_measure.inspect_interference`: calls `InterferenceDetectionManager.GetInterferences`, reads counts, volumes, and component pairs, and calls `Done` only after reading. Coincidence-as-interference is disabled without ignoring hidden bodies; bounding boxes never replace native interference checks. Each run also injects genuine slider/finger penetration and suppresses a slider Mate inside its own assembly, verifying detection before restoring and saving the clean deliverable.

STEP is re-imported into live SolidWorks to verify all 9 solid bodies by volume, world center of mass, cylindrical bore diameter/axis, and area while handling split cylindrical seams after import. BOM CSV reuses `sw_delivery` and cross-checks against live component references, quantities, and on-disk bytes. Native part custom properties record part number, material, and spec-derived dimension/hole/function notes that must match BOM readback; no filler text is padded into CSV and generic Review file-size checks remain active. Raw Review uses `sw_review` without altering its manual-review flag. Part-hole measurement fields unsupported on assemblies are never claimed covered by generic Review, and are instead enforced by this case's standalone part and assembly B-Rep rules.

All artifact hashes, Artifact Ledgers, raw Reviews, snapshots, and unique Core traces are re-read at suite end. Only when every check passes and human review is the sole blocker are `acceptance_status=passed` / `task_status=blocked` / `manual_review_required=true` permitted. Default `completed` mode strictly exits non-zero.

## Commands

Run from the repository root with a non-existent output directory:

```powershell
$env:PYTHONUTF8 = '1'
python -m pytest -q -rs
python tests/evals/runner.py --output-dir output/p0-2-eval-unique
python tests/solidworks_golden_workflow.py --case parallel_gripper_assembly --output output/p0-2-real-unique --runs 5 --expected-terminal blocked
```

`--runtime-config` inherits template/material-library/bounded-timeout keys and adds a case-specific `assembly_template` (`.asmdot`); relative paths resolve against the config file and defaults reuse existing discovery. `mounting_bracket` rejects `assembly_template` so configuration cannot broaden its capability scope.

Offline fault injections are synthetic and excluded from live stats. Development failures, unknown evidence, and abnormal cleanups are preserved. P0-1.2 security blocks on remote CAD CI remain unchanged; no Runner, Environment, permission, or workflow trigger was altered in this stage.

## API Verification References

- [`AddMate5` parameters](https://help.solidworks.com/2025/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IAssemblyDoc~AddMate5.html)
- [Component constraint status](https://help.solidworks.com/2022/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IComponent2~GetConstrainedStatus.html)
- [DOF status enum](https://help.solidworks.com/2026/English/api/swconst/SolidWorks.Interop.swconst~SolidWorks.Interop.swconst.swDofStatus_e.html)
- [Native interference calculation](https://help.solidworks.com/2026/English/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IInterferenceDetectionMgr~GetInterferences.html)
- [`Body2` mass properties and world transform](https://help.solidworks.com/2024/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.ibody2~getmassproperties.html)

Actual execution outcomes follow below; acceptance contracts, historical diagnostics, and the official five-run suite are tracked separately.

### Preserved Development Findings

1. First targeted offline test run hit 26 failed / 33 passed: synthetic fixtures pre-populated trace text mixed with Core JSONL. Fixed fixtures to generate traces solely via real Core adaptation; targeted and full regressions passed without launching CAD.
2. First live diagnostic (`pilot-01`, PID 46796) passed all five native parts, but initial Z assembly transforms did not take effect, causing sliders to overlap with 4 native interferences (max 16,864.920954 mm³). Both task and acceptance failed (exit 1); SLDASM, STEP, BOM, previews, and full evidence were preserved and cleanup passed.
3. The same run revealed that `GetRemainingDOFs` return/status values cannot be interpreted as originally assumed, and empty BOM properties produced a 765-byte CSV triggering a generic Review `WARN`. Resolved by introducing native 6-axis probes with explicit SDK diagnostic scope and populating genuine part numbers, materials, and dimension/hole/function properties—without modifying production Review or rewriting `WARN` to `PASS`.
4. In assembly probe `probe-02`, parameterized `MathUtility` methods were bound as properties by `pywin32`, raising member-not-found; adding explicit `_FlagAsMethod` allowed a minimal document-free API probe to read back all 16 transform entries cleanly. An early auxiliary probe script failed to map errors to non-zero exit codes and was fixed afterward; that script is not a Golden entry point and diagnostic failures were never counted as acceptance passes.
5. `probe-03` (PID 40144) achieved native Review PASS/100 and zero interference, yet placed the right support at the wrong negative distance, and a single concentric Mate—even reading back `LockRotation=true`—allowed slider rotation under the native rotation probe, causing acceptance to fail as intended. Added the second guide-rod concentric Mate, explicit angular Mate on fixed rods, and corrected distance direction without removing any checks. Original failed SLDASM/STEP and previews are preserved.

Subsequent assembly API diagnostics may reuse the verified part files above only when marked `native_assembly_diagnostic_only`; they are not from-scratch Golden runs and do not count toward the consecutive five-run success rate.

## 2026-10-26 Local Live-Machine Results

All five official runs used frozen commit `b2d0bc4bdc4067f9656b8b41321bbd2efd783d31`, SolidWorks 2026 SP01.1 (revision 34.1.1), Windows 11, and Python 3.12.10. Final wrap-up commits added only the evidence index, docs, and `GetRemainingDOFs` comment clarifications without changing execution or acceptance logic. See the stacked Draft PR `HEAD` for the final delivery commit.

Full offline regression ran first, followed by the official live suite; each run built all five parts from scratch in a dedicated process, output directory, and trace:

| Run | PID | Part Files / Instances / Mates | SLDASM Reopen / STEP Readback / BOM | Native Interference | Acceptance / Task / Cleanup |
| --- | --- | --- | --- | --- | --- |
| run-01 | 51052 | 5 / 9 / 22 | PASS / PASS / 9 | 0 | passed / blocked / pass |
| run-02 | 6576 | 5 / 9 / 22 | PASS / PASS / 9 | 0 | passed / blocked / pass |
| run-03 | 48788 | 5 / 9 / 22 | PASS / PASS / 9 | 0 | passed / blocked / pass |
| run-04 | 35240 | 5 / 9 / 22 | PASS / PASS / 9 | 0 | passed / blocked / pass |
| run-05 | 5276 | 5 / 9 / 22 | PASS / PASS / 9 | 0 | passed / blocked / pass |

- Geometry & assembly pass rate 5/5, expected human-gate accuracy 5/5, Test Acceptance=5, Task Completion=0, False Completion=0.
- All five raw Reviews scored PASS/100 with zero issues and `manual_review_required=true`; Core terminal state was `blocked`, `verification=PASS`, `recovery=user_action_required`, sole blocker `EXPECTED_MANUAL_REVIEW_REQUIRED`, command exit code 0.
- Re-evaluating the same raw evidence under default `completed` mode rejected acceptance without running extra CAD or fabricating evidence; recorded separately in offline control files.
- Each run verified 22 healthy, unsuppressed native Mates (13 coincident, 6 concentric, 2 parallel, 1 distance); full names, types, entity params, and unique component IDs are in `built.json` / `reopened.json`. Fixed/moving constraint states and both independent Z travel axes passed all 14 probes.
- Clean assemblies had 0 native interferences and 0 volume. Each run's live penetration control detected 2 interferences (16,864.920954 and 6,480.0 mm³); slider Mate suppression was also caught via real readback, and clean snapshots re-passed after restoration.
- Every native and re-imported STEP read back 9 bodies totaling ~208,099.355043 mm³; per-body centroids, cylindrical bore diameters, axes, and areas passed. All five native parts passed save-and-reopen verification for features, fully defined sketches, dimensions, holes, and materials.
- BOM had 5 rows with quantities 1/2/2/2/2 (total 9); CSV was 1,606 bytes with part numbers, materials, and dimension/hole/function properties matching components.
- All four-view live previews across all five runs were visually reviewed and structurally consistent. Orthographic views may show normal occlusion and should be read alongside isometric and companion views; no manufacturing drawing release is claimed.
- Cleanup pass rate 5/5, zero residual documents per run, owned processes exited cleanly; post-suite checks confirmed zero running SolidWorks processes and zero leftover Python entry processes.

Full offline suite: **999 passed / 1 skipped, 118.09 s** (skipped item is the unbuilt desktop bundled-skill release check, not counted as passed). 11 workflows generated **40 deterministic mock scenarios** with 100% expected accuracy and 0 escaped false completions; **26 synthetic CI policy tests** passed. None of these offline results count toward the five live CAD runs.

## Evidence and Review Entry Points

Machine-readable index: [p0-2-real-gripper-2026-10-26.json](evidence/p0-2-real-gripper-2026-10-26.json). It includes per-run PIDs/creation timestamps, trace IDs, material/template paths and hashes, Mate contracts, volumes, Reviews, cleanup, and failure/remediation logs. Each run directory contains native parts, SLDASM, STEP, BOM, four views, raw Review, logs, snapshots, Core trace, Artifact Ledger, and SHA-256 manifest (145 per-run hash entries total; original failures preserved without being replaced by later passes).

Local evidence paths:

```text
<worktree-p0-real-assembly-2026>/output/p0-2-real-five-01/summary.json
<worktree-p0-real-assembly-2026>/output/p0-2-real-five-01/run-01..05/report.json
<worktree-p0-real-assembly-2026>/output/p0-2-offline/pytest-full-final.log
<worktree-p0-real-assembly-2026>/output/p0-2-offline/eval-final/eval_report.json
<worktree-p0-real-assembly-2026>/output/p0-2-evidence-20261026.zip
<worktree-p0-real-assembly-2026>/output/p0-2-evidence-sha256.json
<worktree-p0-real-assembly-2026>/output/p0-2-independent-seal-verification.json
```

> These artifacts were produced in a dedicated P0-2 worktree (`p0-real-assembly-2026`); paths vary by local disk layout and use a placeholder. The archive is uncommitted and retained locally by the maintainer.

ZIP archive is **11,743,432 bytes / 258 items**, containing the five official runs, dev pilot, three assembly probes, offline logs, SDK signatures, runtime config, diagnostic/seal scripts, and evidence index. SHA-256:

```text
0cdd1d7287ca6fd0438ba555a547d155ff5f22bd62bb0ee1161bd66d8e2ca1ac
```

Post-archive independent verification checked ZIP CRCs, archive SHA-256, disk-vs-ZIP byte parity across all 257 manifest entries, and re-ran per-run Evidence/Core/Ledger/delivery semantic checks; all passed. The first offline failure's full console output was not captured to disk beforehand (explicitly noted in the index); all subsequent full regressions and live failure logs are preserved. `output/` is protected by `.gitignore`; large archives remain local without remote attachment uploads.

## Complete Change Manifest for This Stage

```text
golden-workflows.yaml                                     新增统一夹爪规格
scripts/sw_assembly.py                                    严格原生变换、Mate 和 SDK 诊断回读
tests/golden_workflow_support.py                          注册 SLDASM 用例及专用模板配置
tests/golden_workflow_harness.py                          共用双状态、证据/终态/隔离与失败停止壳
tests/solidworks_golden_parallel_gripper_2026.py            真实建模、装配、故障控制和交付回读
tests/test_solidworks_golden_parallel_gripper_2026.py       36 项离线故障及安全回归
tests/test_eval_runner.py                                 按 Golden 定义推导工作流和场景数
references/assembly.md                                    修正原生干涉 API 用法
docs/architecture/real-golden-parallel-gripper-acceptance.md 验收规格、运行和本机实测报告
docs/architecture/evidence/p0-2-real-gripper-2026-10-26.json  实际证据索引
```

## Unverified Scope and P0-2.1 Plan

Business task status remains `BLOCKED` with no auto-approval enabled. Core covers terminal adaptation only and does not claim step-by-step scheduling of live modeling. Private direct-count semantics of `GetRemainingDOFs` remain unverified; conclusions on the two independent travel axes apply only to this spec's native Mates and bounded 6-axis probes and do not certify full travel, stops, contacts, or other SolidWorks versions. Recovery from permanent hangs inside a single COM call is also unverified.

Early diagnostics revealed an `ArrayData` null-write risk in legacy `apply_component_transform_x` on this host; this stage introduced a strict helper with per-element readback for the gripper case without globally rewriting legacy functions, so other legacy callers were not re-tested live and do not inherit expanded verification scope.

P0-2.1 is recommended to prioritize guide-rod clamping/axial retention, support/base and finger fastening interfaces, bearings, and tolerance drawings before defining limit stops and full-travel native collision regressions. Motors, leadscrews, timing belts, synchronized drives, load/stiffness/wear analysis, and Motion Study require separate specifications and remain unimplemented.

Remote CAD CI remains **BLOCKED / unexecuted**, inheriting P0-1.2 prerequisites for Runner isolation, GitHub audit credentials, and approval security settings. Production Review, Core, `capabilities.yaml`, Windows CAD workflow, Runners, Environments, and repository permissions were untouched in this stage. Keep the stacked Draft PR open; merging into `main` is not recommended until human engineering review and prerequisite security gates are closed.
