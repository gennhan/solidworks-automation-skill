---
name: solidworks-fillet-chamfer-cnc
description: Multi-Fillet and Chamfer automation subskill for SolidWorks CNC parts. Covers parameter pre-checks, semantic edge selection, multi-control-point variable-radius Fillets, Face/Full-Round/Setback Fillets, G2 surface combinations, width-width Chamfers, angle-distance Chamfers, hole-mouth Chamfers, CNC-friendly pockets, bounded degradation, and rebuild evidence for mounts, connector blocks, brackets, and counterbored plates.
---

# SolidWorks Fillet Chamfer CNC

## Determine the Task Mode First

For parts with many Fillets and Chamfers, the primary risks are topology changes, wrong edge selection, and unmachinable parameters—not the API parameters themselves.

- When creating a new CNC mount or validating parameters, run the template script with `--dry-run` first; connect to SolidWorks only after the plan passes.
- When modifying an existing part, read the "Edge Selection on Existing Models" section of [Detailed Lessons](references/cnc-fillet-chamfer-lessons.md) first rather than applying the template's fixed expected edge counts.
- When the user requests variable-radius, Face Fillet, Full Round, or Setback Fillets, run this subskill's advanced capability probe first; keep status at `pilot` whenever the SolidWorks version or input topology differs from verified samples—never claim cross-version stability without verification.
- Multi-control-point variable Fillets, surface combinations, and width-width Chamfers have independent live-machine evidence on SW2026 SP1.1, but must be re-run when changing version or topology. Hold-line Fillets were re-tested across Python, C# PIA, SWBasic, and in-process unmanaged C++, isolating the fault boundary to the `ISetHoldLines` call on local SW2026 SP1.1 rather than a Python-only limitation. This build must remain `pilot/blocked` and must never silently degrade into a plain Face Fillet and claim success.

## Template Entry Point

Run COM-free preflight validation first:

```powershell
python subskills\solidworks-fillet-chamfer-cnc\scripts\create_cnc_mount_template.py `
  --dry-run `
  --set base_corner_radius=6 `
  --set chamfer_angle_deg=30 `
  --output-dir C:\CADAutomationWorkbench\cnc_mount
```

Confirm that `validation.errors` in `*_plan.json` is empty and that semantic targets and `expected_edge_count` match design intent, then remove `--dry-run` to run native modeling. Put large parameter sets into a JSON file:

```powershell
python subskills\solidworks-fillet-chamfer-cnc\scripts\create_cnc_mount_template.py `
  --params-json subskills\solidworks-fillet-chamfer-cnc\examples\cnc_mount_precision_params.json `
  --failure-policy strict `
  --output-dir C:\CADAutomationWorkbench\cnc_mount
```

`strict` accepts only the requested dimensions; `progressive` attempts 100%/75%/50%. Whenever degradation occurs, the delivery summary must explicitly report the actual dimensions rather than claiming exact compliance with the original values.

## Non-Negotiable Gates

1. Run the parent skill's `scripts/sw_preflight.py` before native modeling; `--dry-run` does not require SolidWorks.
2. Parameter pre-checks must cover finite values, Fillet/Chamfer upper bounds, hole/slot collisions, minimum edge wall thickness, inter-feature clearances, counterbore/pocket floor thickness, and safe output basenames.
3. New templates execute in the order: "Base Body → Vertical Corner Fillets → Outer-Contour Chamfers → Holes/Slots/Pockets → Hole-Mouth Chamfers"; existing models follow their feature dependency order.
4. Edge selection relies on geometric signatures and expected counts as evidence. Stop immediately if the count mismatches—never widen coordinate tolerances, fall back to `Edge1`, or guess edges via screen clicks.
5. Every Fillet and Chamfer must be read back from the FeatureManager Design Tree after rebuild; a non-null COM return value does not guarantee persistence.
6. After generation, save the `SLDPRT`, export `STEP`, run `sw_review.run_review()`, and visually inspect the isometric and top previews.

## Advanced Fillet Entry Point

Probe the local type library read-only first without launching SolidWorks:

```powershell
python subskills\solidworks-fillet-chamfer-cnc\scripts\verify_advanced_fillets.py `
  --output-dir C:\CADAutomationWorkbench\advanced_fillet_probe
```

Run the six currently passing independent live-machine regressions:

```powershell
python subskills\solidworks-fillet-chamfer-cnc\scripts\verify_advanced_fillets.py `
  --verify-solidworks `
  --modes variable face surface_combo full_round setback width_width_chamfer `
  --output-dir C:\CADAutomationWorkbench\advanced_fillet_verified
```

Declare environment support only when the report's capability status is `verified` and the corresponding `SLDPRT`, `STEP`, reopen evidence, and review report all exist. Minimal samples currently verified on SolidWorks 2026 SP1.1:

- Single-edge endpoint variable-radius Fillet R2→R5, read back as feature type `VarFillet`.
- Three intermediate control points at 25%/50%/75% on the same edge read back as R3/R6/R4; `GetControlPointRadiusAtIndex` position values are interpreted as percentages `25/50/75`.
- R4 Face Fillet between two adjacent face sets, `ISimpleFilletFeatureData2.Type=2`.
- R3 G2 Face Fillet on a plane–cylinder surface combination, reading back `CurvatureContinuous=true` after reopen.
- Full Round Fillet across three face sets (1 face each), `ISimpleFilletFeatureData2.Type=3`.
- Three-edge corner R3 with per-edge 1 mm Setback, reading back 1 setback vertex.
- C2/C4 distance-distance Chamfer, `IChamferFeatureData2.Type=2`, with side `0/1` distances read back as `2/4 mm`.

Setback distance arrays must be explicitly wrapped as `VT_ARRAY | VT_R8`. A plain Python `tuple` may not raise a COM exception while causing `FeatureFillet` to return `None`; never degrade that outcome into a regular Fillet.

Hold-line mode uses a projected Split Line, two face sets with marks `2/4`, and a hold line with mark `8`, requiring `GetHoldLineCount=1`. Official `ISetHoldLines` supports only in-process unmanaged C++ inside SolidWorks, so the script provides an MSVC x64 DLL + SWBasic main-thread dispatcher while keeping C# PIA and Python paths for comparison. On local SW2026 SP1.1 / Revision 34.1.1, plain Python arrays read back as 0, explicit `SAFEARRAY` triggers a server fault, and C#, SWBasic, and native C++ also fail to yield persistent hold lines—with native calls faulting at the `ISetHoldLines` boundary. Therefore, the default returns structured `blocked/known_server_fault` without invoking the hazardous call.

Pass `--unsafe-native-hold-line` explicitly only when re-testing another service pack inside an isolated, self-owned SolidWorks instance; this switch can crash the instance and must never be used on a session with unsaved documents. The pass criterion remains `GetHoldLineCount=1` both immediately after creation and after reopening.

## Open-Source Complex Case Regressions

Added an MIT-licensed CadQuery `parametric-bracket-library/l_gusset` regression. This part includes two perpendicular mounting plates, a triangular gusset rib, and six mounting holes; the SW2026 import baseline is `1 solid / 18 faces / 49 edges`. On the same complex solid body, the script creates a 4-intermediate-control-point (20/40/60/80%) variable-radius Fillet and a C0.8/C1.4 width-width Chamfer:

```powershell
python subskills\solidworks-fillet-chamfer-cnc\scripts\verify_open_source_bracket.py `
  --source C:\CADAutomationWorkbench\sources\l_gusset.step `
  --source-commit 5b285130bff480cda282499e83604b295dd0aa4d `
  --version 2026 `
  --output-dir C:\CADAutomationWorkbench\opensource_l_gusset
```

The case is marked `verified` only when the pinned commit, CadQuery 2.8.0 output SHA-256, complexity gate, all four control-point percentages/radii, both asymmetric Chamfer distances, post-treatment topology, rebuild, `SLDPRT`, `STEP`, reopen, and 4-view review all pass. The input STEP can be generated with CadQuery 2.8.0 per that repo's README; the script never performs unpinned network downloads at runtime.

The existing FreeCAD-library complex corner bracket remains as a second independent Chamfer regression:

This complex-model regression pins FreeCAD-library's `2020_corner_bracket-Corner.step` with a fixed commit, SHA-256 hash, and CC BY 3.0 attribution, never using floating main-branch URLs:

```powershell
python subskills\solidworks-fillet-chamfer-cnc\scripts\verify_open_source_complex_case.py `
  --version 2026 `
  --output-dir C:\CADAutomationWorkbench\opensource_corner_bracket
```

The script selects the 24.041631 mm angled edge by its unique endpoint/length signature in the manifest and applies a real C0.2/C0.4 width-width Chamfer. The case is marked `verified` only when the download hash, exact source topology (`1 solid / 40 faces / 98 edges`), Chamfer `FeatureData` readback, post-treatment topology (`41 faces / 101 edges / 66 vertices`) preserved across reopen, `SLDPRT`/`STEP` exports, and 4-view review all pass. When offline, a cached file may be reused, but its SHA-256 must still be recomputed.

## CNC Geometry Defaults

- Lightening pockets default to `rounded_slot` to avoid delivering unmachinable zero-radius inside corners; use `rectangle` only when secondary corner-clearing operations are explicitly required, and preserve the DFM warning.
- Dowel holes, center slots, and lightening pockets must share a single parameter source for 2D envelope collision checking. Template v2 defaults dowel holes along the Y axis to prevent the legacy overlap with the center slot.
- Constant-radius Fillets and angle-distance Chamfers are the general stable paths; multi-control-point variable Fillets, Face/Full-Round/Setback Fillets, plane–cylinder G2 combinations, and width-width Chamfers have minimal live regressions on SolidWorks 2026 SP1.1, but must be re-verified with the capability script when applied to other topologies or versions. Complex transitions must record API, SolidWorks version, input topology, rebuild results, and preview evidence before upgrading capability status.

For detailed edge-selection signatures, failure semantics, existing-model strategies, and the expansion roadmap, see [CNC Multi-Fillet/Chamfer Lessons](references/cnc-fillet-chamfer-lessons.md).

## Verification Requirements

Output on every run:

- `*.SLDPRT`
- `*.step`
- `*_parameters.json`
- `*_review_report.json`
- `*_isometric.bmp` or converted PNG

During review, check at minimum:

- `evaluation.status` is `pass` or an explainable `warn`
- `expected_outputs_exist` is `True`
- `previews_not_blank` is `True`
- `validation.errors` is empty
- `treatment_evidence` records requested values, actual values, every attempt, and selected edge signatures
- `feature_evidence.missing_names` is empty
- The FeatureManager Design Tree contains the expected `Fillet` / `Chamfer` / `Cut` features
