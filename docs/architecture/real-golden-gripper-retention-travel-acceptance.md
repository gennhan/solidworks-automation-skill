# P0-2.1: Gripper Mechanical Retention, Tolerances, and Static Full-Travel Acceptance

This stage adds an independent Golden case `parallel_gripper_retention_travel` on top of P0-2 without altering original P0-1 or P0-2 cases or their historical evidence.
Working branch: `test/p0-real-gripper-retention-travel-2026`, stacked base `e5c242175c0a1d7e0fa4fabc90839f6d9fbc74ac`,
Draft PR targeting `test/p0-real-assembly-gripper-2026`. Neither #39 nor #42 is merged, and `main`, production Review, Verification,
Execution Core, and GitHub security settings are untouched. Core continues verifying terminal adaptation only.

## Original Structure Audit and Minimal Mechanical Changes

P0-2 had dual guide-rod concentric mates and two independent Z translations, but the Ø8 guide rods, Ø8.1 slider bores, and Ø8.02 support bores were nominal geometry only
without tolerance bands; support/base and finger/slider relied solely on Mates without fastening interfaces; and unbounded travel could slide off the guide rods.

P0-2.1 retains the dual-rod, dual-slider, independent-finger, dual-end-support topology while adding the following functional solids and interfaces:

| Component | Native Qty | Changes and Function (mm) |
| --- | --- | --- |
| Base | 1 | 60×12×116, Y=-38..-26, Z=-58..58; integrated 52×36×8 center stop block, Y=-26..10, Z=-4..4 |
| Support | 2 | 60×46×12, Y=-38..8; Z=-70..-58 and 58..70; inner end faces also act as outer travel stops |
| Guide rod | 2 | Modeled diameter 7.9905, length 139.8, Z=-69.9..69.9; two axes at X=±18, Y=0 |
| Slider | 2 | 52×20×18; retains dual guide bores, adds two Ø3.2 connecting holes along Y |
| Finger | 2 | 12×30×18, Y=10..40; adds two connecting holes coaxial with the corresponding slider |
| End retainer plate | 2 | 60×46×4; Z=-74..-70 and 70..74, closing axial guide-rod exits |
| Tie rivet rod | 2 | Ø4×148 shank, Z=-74..74; Ø8×3 formed heads at both ends, real interface through end plates/supports/base |
| Finger rivet | 4 | Ø3×50 shank, Y=-10..40; Ø5.5×3 formed heads at both ends; 0.5 nominal clearance between adjacent same-side heads; two non-coaxial rivets retain each finger |

Eight native SLDPRT files and 17 component instances in total. Rivets are modeled as genuine double-headed post-forming solids with through-holes and seated head faces—not bolts, cosmetic geometry, or certified standard fasteners. Assembly sequence requires inserting shanks/rivets before forming the tail head; forming process, tool accessibility, clamping preload, head sizing, and strength must be reviewed by an engineer. This stage proves neither riveting manufacturability nor load capacity, and does not claim production readiness.

Nominal axial clearance between each guide rod and end plate is 0.1 mm (0.2 mm total axial float); travel stops keep the entire slider within the effective guide-rod length at both endpoints. Axial tolerance stack-up has not been signed off, so 0.2 mm is a nominal design clearance rather than a manufactured guarantee.

## Hole and Locating Schedule

All items below are native cuts, never cosmetic marks. Locations come from the unified Golden specification and cannot be overridden by runtime config.

| Part / Interface | Qty | Axis, Size, and Locating Datum |
| --- | --- | --- |
| Base integrated stop / guide | 2 | Along Z, modeled Ø8.0075; X=±18, Y=0, through stop 8; local base Z=54..62 |
| Support / guide rod | 2 each | Along Z, modeled Ø8.0075; X=±18, Y=0, through 12 |
| Slider / guide rod | 2 each | Along Z, modeled Ø8.0075; X=±18, Y=0, through 18 |
| Base, support, end plate / tie rivet | 2 each | Along Z, Ø4.1; X=±22, Y=-32, through 116 / 12 / 4 respectively |
| Base / external mounting | 4 | Along Y, Ø4.5; X=±12, world Z=±40 (local base Z=18/98), through base 12 |
| Slider & finger / rivets | 2 each | Along Y, Ø3.2; X=±3, local part Z=9, through slider 20 / finger 30 |

Aside from the guide bore/shaft fit, tolerances on the mounting holes and rivets above are **engineering proposals pending confirmation**. External mating hardware and fasteners are unmodeled, so complete system mounting is not claimed. Functional penetration of tie rods through base/supports, double-head retention, and finger-rivet seating must all be verified via native geometry readback.

## Tolerance Basis and Scope Boundaries

Proposed nominal fit: Ø8 H7/g6. Manufacturer references:

- [MISUMI linear shaft g6 chart](https://sg.misumi-ec.com/pdf/fa/2013/p226.pdf): g6 for Ø8/10 is -0.005/-0.014 mm.
- [MISUMI H7 shaft accessory datasheet](https://jp.misumi-ec.com/vona2/detail/110300223240/?HissuCode=ADKR8-10): Ø8 H7 is 0/+0.015 mm.
- [MISUMI fits technical reference](https://pt.misumi-ec.com/pdf/fa/2014/P1_2287-2288_F80_EN.pdf): hole/shaft tolerance zones and fit classes.

This yields shaft 7.986..7.995 mm and bore 8.000..8.015 mm (diametral clearance 0.005..0.029 mm). CAD uses mid-band values 7.9905 / 8.0075 mm (nominal modeled diametral clearance 0.017 mm) so running clearances remain separable from intentional end-face contact; mid-band dimensions are never mislabeled as basic nominal sizes. Actual mating dimensions still require drawings and inspection. This stage does not claim full compliance with ISO/TCVN (or secondary `GB/T`) manufacturing standards.

Dual-rod bore position, parallelism, coaxiality, surface finish, lubrication/wear/thermal expansion, and axial stack-up remain open; H7/g6 alone cannot guarantee freedom from binding on dual rods. Library material proposals are `AISI 1020` for rods/rivets and `6061-T6 (SS)` for remaining parts; these are CAD properties only, not heat-treatment, hardness, material certification, or riveting performance qualification.

## Travel and Native Computation Contract

- Left slider origin Z min/mid/max: -58 / -40 / -22; right slider: 4 / 22 / 40; independent travel per side: 36 mm.
- Outermost endpoints seat against support inner end faces; innermost endpoints seat against the base's integrated center stop. Required contacts are neither removed nor artificially gapped to fake zero interference.
- 48 native Mates (including two real limit-distance Mates): left side 16..52 relative to left end plate, right side 62..98 relative to base. Reads back `IsAdvancedMate`, `Distance`, `MinimumDistance`, and `MaximumDistance` from limit `FeatureData`.
- Executes all 3×3 = 9 static poses across the two three-position sets; each pose sends a real transform readback and persists the static state via native Mate current distance + `ModifyDefinition`, verifying all components, Mates, references, current distances, and min/max limits after rebuild—never simulating mates by raw matrix writes.
- Each pose runs `InterferenceDetectionManager.GetInterferences` once for volumetric interference and a second pass with `TreatCoincidenceAsInterference=True` for intentional contacts, calling `Done` only after reading results. Missing, unknown, API-error, or uncomputed results fail; bounding boxes are never used as collision evidence.
- Static fastener head contacts and endpoint stop contacts must both be genuinely detected; volumetric penetration is judged separately rather than conflating non-zero contact counts with penetration.
- Retains four transform requests that do not commit Mate current distances; valid poses must be read back without treating a successful API call as proof of reaching the target travel.
- Adds four real over-travel / bound-expansion penetration injections: 2 mm past each min/max limit on both sides, verifying both native volumetric interference with the corresponding support/center stop and normal-rule rejection, followed by restoration of each case. Independently tests limit-Mate suppression and slider/center-stop penetration controls, requiring detection and restoration. Normal files are saved only after restoration.
- Saves, closes, and reopens the native assembly and references, verifying identities/poses of all 17 instances, Mates/limits/references, and BOM; re-imports STEP in SolidWorks to verify every body individually.

The 9 static combinations cover the requested endpoints and midpoints; they do not equate to continuous swept collision checking or Motion Study, and make no claim of synchronized actuation. No motor, leadscrew, timing belt, power transmission, or load claims are made.

Live testing revealed that without committing a native limit Mate's current distance, transform requests may return success while rebuild reverts to the initial distance; free dragging, driven dimensions, `SetTransformAndSolve3`, or switching to `CreateMate` alone cannot prove persistent motion. Accordingly, this case validates static poses controlled by real Mate parameters and claims neither free dragging nor native contact dynamics, nor does it expand P0-2's DOF certification scope. Modifying `Distance` can also cause SolidWorks to auto-expand limits; therefore normal entry points permit only non-configurable valid poses and assert unchanged min/max limits, while limit expansion and actual over-travel penetration are tested as mandatory rejected fault injections. The CAD solver itself is not claimed to simulate physical stops automatically.

## Execution and Dual-Status Semantics

Run from the repository root with a non-existent output directory:

```powershell
$env:PYTHONUTF8 = '1'
python -m pytest -q -rs
python tests/evals/runner.py --output-dir output/p0-2-1-eval-unique
node --test tests/test_cad_ci_guard.cjs
python tests/solidworks_golden_workflow.py --case parallel_gripper_retention_travel --output output/p0-2-1-real-unique --runs 5 --expected-terminal blocked --runtime-config config/runtime.example.json
```

Controlled runtime config permits only existing templates, material library paths, and bounded timeouts. `config/runtime.example.json` is the committed portable template (`null` paths trigger auto-discovery); formal acceptance used local `output/p0-2-1-runtime.json` (with local absolute paths, uncommitted). Pre-run environment diagnostics, rejection of existing processes, per-run isolated directories/UUID traces, Session ownership, PID + creation-time checks, halting subsequent runs on cleanup failure, full-file SHA-256, Artifact Ledger, and Core trace all inherit P0-2 rules. Only when every rule passes and the sole block is human review from raw Review does the run report `acceptance_status=passed`, `task_status=blocked`, and `manual_review_required=true`. Default `completed` mode remains strictly failing. Remote CAD CI inherits prior security configuration `BLOCKED` status and is neither altered nor claimed verified here.

## API Verification References

- [FeatureExtrusion3 start offset](https://help.solidworks.com/2024/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.ifeaturemanager~featureextrusion3.html): `T0`/`StartOffset`/`FlipStartOffset`; local SW2026 enum `swStartOffset=3`.
- [FeatureCut4 bidirectional cut](https://help.solidworks.com/2024/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.ifeaturemanager~featurecut4.html): `Sd=False` with native `ThroughAll` in both directions so blind cuts never masquerade as through-holes.
- [Distance Mate FeatureData](https://help.solidworks.com/2025/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IDistanceMateFeatureData_members.html): raw readback of `IsAdvancedMate`, `MinimumDistance`, and `MaximumDistance`.
- [Limit Distance Mate creation and ModifyDefinition example](https://help.solidworks.com/2022/english/api/sldworksapi/Create_Limit_Distance_Mate_Example_CSharp.htm): explicitly read back and verify `Advanced`, `Distance`, and limits after persisting current distance rather than trusting `ModifyDefinition`'s return code alone.
- [Intentional contact toggle](https://help.solidworks.com/2025/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IInterferenceDetectionMgr~TreatCoincidenceAsInterference.html): applies only to the active manager instance; set explicitly every time rather than assuming persistence.

## Actual Execution Log

This section logs actual execution outcomes; the sections above define the acceptance contract rather than a pass claim. All failures are preserved, and offline synthetic tests are kept separate from live-machine counts.

1. First live suite `p0-2-1-real-five-01/run-01` (commit `4aeccde`, PID 41276) failed at guide-rod material assignment, exited 1, and launched no subsequent runs. Base and supports passed save-and-reopen; guide-rod geometry passed but material read back empty with density 1000. All logs, snapshots, and generated CAD were preserved and cleanup passed. Because failure occurred before saving the guide rod, no nonexistent failed native part was claimed; failed native copy retention was added afterward.
2. Standalone live material API diagnostics are excluded from Golden counts. Applying `1045`, `1100-O`, and `Alloy Steel` failed and could leave prior material intact; `6061-T6` and `AISI 1020` read back cleanly. Mere presence of a name in XML does not prove material application. Switched to verifiable `AISI 1020` (7900 kg/m³ library density; aluminum parts 2700 kg/m³). Material suitability remains an engineering proposal rather than a certified equivalent.
3. Implementation review also reduced same-side rivet head diameter from 6 to 5.5 mm to avoid nominal tangency; head sizing and forming-tool accessibility remain subject to human review.
4. Second live suite `p0-2-1-real-five-02/run-01` (commit `bebfe83`, PID 5436) passed all eight parts, but all nine slider poses reverted to midpoint on rebuild and rivets landed on the opposite side of the slider due to reversed plane-distance sign. Despite zero native penetration and Review PASS, pose/contact/STEP rules failed as expected; full CAD/STEP/BOM/previews, logs, and hashes were preserved, cleanup passed, and run-02 was not launched.
5. Standalone assembly diagnostics copied SLDASM while opening historical parts read-only and verified all historical input hashes afterward; driven dimensions, `CreateMate`, `SetTransformAndSolve3`, and isolated Mates preserved raw outcomes. Probe #1's exit code 0 meant only API completion without checking post-rebuild motion; Probe #6 checked valid poses without checking bound expansion and also exited 0. Neither belongs to Golden or counts toward acceptance. Subsequent probes enforced strict pose/range exit checks, and the bound-expansion probe failed explicitly. The official Golden entry point always enforces strict rules and non-zero failure exits.
6. Corrected the reversed-normal distance sign for rivets and added a corresponding fault regression. Switched the 9 valid poses to native Mate current-distance control, retained original transform-request checks, and added four real mechanical over-travel interference fault controls without removing any pose, contact, Mate, limit, or cleanup check.
7. Assembly probe `assembly-probe-08` reused copies of the eight verified parts and passed assembly build, 9 poses, 4 over-travel penetrations, suppression/center penetration, restoration, save-and-reopen, STEP, Review, and cleanup with exit code 0 and unchanged input hashes. Four views were visually reviewed. Each 2 mm over-travel produced 1 native penetration (outer volume 1670.560902 mm³, inner volume 1878.560902 mm³). Because it did not rebuild parts from scratch, it does not count toward the official five-run suite; all 9 valid poses had 0 penetration and 18–22 native zero-volume contact entries (classified below).
8. Official suite `p0-2-1-real-five-03` on frozen commit `359959610a996b42066fc98e4bf313ddb0485aae` passed runs 1–4 cleanly; run 5 suffered COM disconnection right before creating the left slider limit Mate, leaving assembly and cleanup readback incomplete, and exited 1 truthfully. On 2026-10-27 the user confirmed this disconnect was caused by manually closing SolidWorks. The manually interrupted failure/unknown record is retained without retroactively marking it passed and without mislabeling it as a proven CAD crash or modeling bug. Zero residual processes afterward do not substitute for in-run document cleanup verification. Added three independent SLDASM checkpoints (post-insert, pre-limit, post-all-mates), per-Mate progress logging, and a fault test ensuring disconnects cannot pass acceptance. Checkpoints do not constitute recovery, success, or cleanup proof; no automatic exception retry or gate relaxation was added.
9. Discovered partial prior evidence in `p0-2-1-real-five-04/run-01` containing eight parts and a nine-pose report, but missing a terminal report, cleanup proof, and suite summary. The exact interruption cause of that unclosed run is unconfirmed and it is not counted as passed. A 2026-10-27 attempt reusing that directory was rejected by the entry point without launching CAD; however, an outer `Tee` command overwrote the old outer console log—an operational mistake whose prior content cannot be recovered. Original `run.log`, CAD files, and snapshots inside the directory remained untouched. The newly written `five-04-exitcode.txt` reflects only the duplicate-directory rejection and cannot be used to infer the prior run's terminal state. Subsequent launches verify that the directory, console log, and exit-code file are all absent before invoking `Tee`, and switched to `five-05`.

## 2026-10-27 Five-Run Results on Frozen Source

Source commit: `df4d4c9a4143602d5af7077a7be7b19cee4850c2`, SolidWorks 2026 SP01.1 / revision 34.1.1, Python 3.12.10 / Windows 11. All five runs generated all eight parts from scratch in fresh instances and isolated directories—not copying finished CAD, deterministic mocks, OCCT, or reusing assembly diagnostics. Actual command executed (reruns must use a new non-existent output directory):

```powershell
python -u tests/solidworks_golden_workflow.py --case parallel_gripper_retention_travel --output output/p0-2-1-real-five-05 --runs 5 --expected-terminal blocked --runtime-config output/p0-2-1-runtime.json
```

> The command above is the **exact command run at the time**, where `output/p0-2-1-runtime.json` was a local config (containing local absolute paths, excluded by `.gitignore` and uncommitted).
> For external reproduction, use the committed template `config/runtime.example.json` (auto-discovery) and specify a new non-existent `--output` directory.

| Run | Dedicated PID | Native Geometry, Assembly & Delivery | Test Acceptance | Task Status | Owned Docs / Process Cleanup |
| --- | --- | --- | --- | --- | --- |
| 01 | 35168 | PASS | passed | blocked | PASS / 0 residual |
| 02 | 25560 | PASS | passed | blocked | PASS / 0 residual |
| 03 | 35628 | PASS | passed | blocked | PASS / 0 residual |
| 04 | 39064 | PASS | passed | blocked | PASS / 0 residual |
| 05 | 16088 | PASS | passed | blocked | PASS / 0 residual |

Each run built 8 SLDPRTs, 17 component instances, and 48 Mates (14 coincident, 6 concentric, 2 parallel, 26 distance including 2 real limit Mates). Component IDs/names/paths remained identical after save, close, and reopen; every solid body and re-imported STEP matched volume, center of mass, and cylindrical bore/shaft size, location, and area. Total native and STEP solid volume was ~**244,414.832633 mm³**; BOM contained 8 rows totaling quantity 17. All 20 four-view previews across five runs were visually reviewed. Every raw Review scored PASS / 100 with `manual_review_required=true`, and Core actual terminal status and trace were `blocked`.

All normal combinations were computed and passed in every run; table shows volumetric penetration counts (independently verified 5 times per cell):

| Left Slider Z / Right Slider Z (mm) | 4 | 22 | 40 |
| --- | --- | --- | --- |
| -58 | 0, 5/5 | 0, 5/5 | 0, 5/5 |
| -40 | 0, 5/5 | 0, 5/5 | 0, 5/5 |
| -22 | 0, 5/5 | 0, 5/5 | 0, 5/5 |

All 45 normal poses had 0 volumetric penetrations and 0 mm³ penetration volume. Zero-volume contact counts in row-major order were `21, 19, 20, 20, 18, 19, 22, 20, 21`. The 18 nominal fastener contacts and endpoint stop contacts are tracked separately; at the inner limit, **co-edge contact** also occurs between the finger and the upper edge of the center stop—this must not be called a manufacturing clearance or approved bearing contact, and chamfers/tolerances remain under review.

Derived from actual transforms, saved part D1, and verified B-Rep stop planes: both guide rods maintain 18 mm engagement on each slider across all poses, stop clearances are >= 0, finger jaw opening spans 8 to 80 mm, and axial rod end clearances are ~0.1 mm each. Native cylindrical face readback measured shaft Ø7.9905 and base/support/slider bores Ø8.0075 (nominal diametral clearance 0.017 mm). These are nominal geometric derivations; collision verdicts still come exclusively from native Interference Detection rather than bounding boxes or manufacturing tolerance certification.

| Live Fault Control (Per Run) | Native Penetration Entries | Penetration Volume (mm³) | Detected & Restored (5 Runs) |
| --- | --- | --- | --- |
| Left past outer limit -60 | 1, slider / left support | 1670.560902 | 5/5 |
| Left past inner limit -20 | 1, slider / center stop | 1878.560902 | 5/5 |
| Right past inner limit 2 | 1, slider / center stop | 1878.560902 | 5/5 |
| Right past outer limit 42 | 1, slider / right support | 1670.560902 | 5/5 |
| Left center penetration -3 | 3, raw component/volume details in report | See raw report | 5/5 |
| Limit Mate suppression | Normal acceptor rejects suppressed state | Zero interference never replaces Mate checks | 5/5 |

Suite exit code **0**: live geometry/assembly pass rate 5/5, expected-gate accuracy 5/5, Test Acceptance=5, Task Completion=0, False Completion=0, cleanup pass rate 5/5. Re-evaluating the same live evidence in strict `completed` mode yields `failed` without counting extra CAD runs. Cumulative history retains 9 full passes (4 on old source, 5 on new source), 2 development failures, 1 manual interruption, and 1 unclosed run; none of the failed/interrupted/unclosed runs were retroactively marked passed, and auxiliary diagnostics do not count as Golden runs.

## Offline Regression, Evidence, and Post-Implementation Audit

- Full offline suite: **1034 passed / 1 skipped (128.19 s)**; 35 new tests cover missing limits, wrong travel, broken Mates, wrong clearances, lost stop contacts, full-travel penetration, bound expansion, bad BOM/STEP, Review WARN/FAIL, evidence tampering, cleanup failure, and COM disconnect. The sole skipped item remains the unbuilt desktop bundled-skill package check. Log: `output/p0-2-1-offline/pytest-full-05.log`.
- 43 deterministic mock scenarios (12 nominal, 31 robustness) matched expectations with 0 escaped false completions; 26 synthetic CI admission policy tests passed—both listed separately and distinct from live-machine or remote runner acceptance.
- All **190 per-run hashes**, Artifact Ledgers, and Core traces across five runs re-verified consistently. Post-implementation audit confirmed that the eight protected files covering production gates, CI, and prior mounting-bracket/gripper cases share identical Git blobs with Base; original cases remain intact and passed full offline regression while live re-verification targeted the new case.
- Post-run read-only checks confirmed zero residual main instances, monitored child processes, or test entry points; document count returned to zero across all five runs. Pre-existing `sldworks_fs.exe` (PID 27760, created 09:19:25) matched by PID + creation time was left untouched without terminating any unknown or user process.
- The [machine-readable evidence index](evidence/p0-2-1-real-gripper-travel-2026-10-27.json) records per-run config/asset hashes, trace IDs, Mate contracts, actual poses, contacts, engagement, clearances, faults, cleanup, and historical failure/log-overwrite limitations.

Local archive contains the five runs, historical failures/unclosed data, diagnostics, and offline logs (549 items, 26,746,788 bytes; not uploaded as a remote attachment):

```text
output/p0-2-1-evidence-20261027.zip        （相对仓库根目录）
SHA-256: 16a5e33383dd326d033ef316d4610c450a42676dbaed1758a963f2d612e8f3b4
```

> This ZIP is uncommitted (26.7 MB; `output/` is excluded by `.gitignore`) and retained locally on the maintainer's machine only.
> External reviewers can verify the published manifest and hashes, but **cannot independently replay raw binary evidence**.

ZIP CRC, whole-archive SHA-256, and disk-vs-archive byte comparisons across all manifest files passed; Python and PowerShell SHA-256 hashes matched. Independent seal verification is recorded in `output/p0-2-1-independent-seal-verification.json` with per-file manifest `output/p0-2-1-evidence-sha256.json`. Neither the archive itself nor its sidecar participates in circular self-hashing.

The seven project files changed relative to P0-2 Base:

```text
golden-workflows.yaml
scripts/sw_part.py
tests/golden_workflow_support.py
tests/solidworks_golden_gripper_travel_2026.py
tests/test_solidworks_golden_gripper_travel_2026.py
docs/architecture/real-golden-gripper-retention-travel-acceptance.md
docs/architecture/evidence/p0-2-1-real-gripper-travel-2026-10-27.json
```

`sw_part.py` adds only backward-compatible boss start-offset and bidirectional cut options without duplicating COM infrastructure. Auxiliary diagnostic, checkpoint, process-audit, and sealing scripts remain with local evidence without altering production architecture.

## Unreleased Scope and Pending Engineering Review

Local static Golden Test Acceptance is `passed`, whereas business Task Status remains `blocked` and both manufacturing release and merge readiness remain **BLOCKED**. [Stacked Draft PR #43](https://github.com/wzyn20051216/solidworks-automation-skill/pull/43) targets the P0-2 branch, stays Draft, and does not merge into `main` or #39/#42.

Engineers must still review H7/g6 suitability for these materials and operating conditions, dual-rod position/parallelism, axial tolerance chains, wear/lubrication, inner finger co-edge contact and chamfers, machining feasibility of the 116 mm deep Ø4.1 holes, and rivet forming sequence, accessibility, clamping, and strength. CAD guide-rod orientation Mates do not certify physical anti-rotation or joint stiffness; external mating equipment, material certificates, and manufacturing drawing sign-off remain incomplete. Free dragging, continuous swept collision, contact dynamics, actuation/synchronization, loads, and Motion Study were not tested on the new assembly, nor was original P0-2 capability scope expanded. Core covers terminal adaptation only; step-by-step CAD scheduling and recovery from permanent COM hangs or abnormal termination remain unverified. Cross-machine reference relocation after archive extraction is unverified; the historical outer console log overwrite is an unrecoverable evidence limitation. Remote CAD CI was neither run nor configured in this stage, and prerequisite security configurations remain unresolved; remote security acceptance must not be claimed complete.
