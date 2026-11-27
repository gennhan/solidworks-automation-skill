# SolidWorks Fillet Chamfer CNC

`solidworks-fillet-chamfer-cnc` is the dedicated CNC Fillet/Chamfer subskill in the `solidworks-automation` repository, built to generate machined parts with parameter pre-checks, semantic edge selection, size-degradation evidence, FeatureManager Design Tree readback, and STEP review.

## Applicable Scenarios

- CNC aluminum mounting bases, connector blocks, brackets, baseplates, and counterbored mounting plates.
- Large outer-contour Fillets, top/bottom edge Chamfers, and hole-mouth Chamfers.
- Environment probing and live-machine regressions for 3/4 intermediate-control-point variable-radius Fillets, Face Fillets, Full Round Fillets, three-edge-corner Setback Fillets, plane–cylinder G2 surface combinations, and asymmetric distance-distance (width-width) Chamfers.
- Safe capability probing and versioned blocking evidence across four Hold Line backends: Python, C# PIA, SWBasic, and in-process unmanaged C++.
- Round-trip regression on a pinned-commit, SHA-256-verified, CC BY 3.0-attributed FreeCAD-library complex corner bracket, applying a C0.2/C0.4 width-width Chamfer on an edge identified by a unique geometric signature.
- CNC-friendly rounded-slot pockets, center slots, counterbores, dowel holes, and inter-feature clearance checks.
- Deterministic edge selection, STEP export, and multi-view preview inspection.

## Core Principles

The main challenge in multi-Fillet/Chamfer parts is not API arguments, but stable topology, deterministic edge selection, and feature ordering:

1. Start with a simple base body.
2. Check hole/slot collisions, minimum edge wall thickness, feature clearances, and remaining floor thickness before calling COM.
3. Apply large Fillets and outer-profile Chamfers before hole and slot Extrude Cuts whenever possible.
4. Add holes, slots, and pockets after main body edge treatments, and place small hole-mouth Chamfers last.
5. Select edges using geometric signatures, `edge.Select2()`, and exact count assertions—never rely on `Edge1` or screen coordinates.
6. Read back features after rebuild and run `sw_review.run_review()`.

## Quick Commands

Run offline preflight validation from the repository root first:

```powershell
py subskills\solidworks-fillet-chamfer-cnc\scripts\create_cnc_mount_template.py `
  --dry-run `
  --set base_corner_radius=6 `
  --output-dir C:\CADAutomationWorkbench\solidworks_fillet_chamfer_output
```

After inspecting the generated `CNC_Mount_Template_plan.json`, remove `--dry-run` to run SolidWorks modeling. You can also supply a parameter file:

```powershell
py subskills\solidworks-fillet-chamfer-cnc\scripts\create_cnc_mount_template.py `
  --params-json subskills\solidworks-fillet-chamfer-cnc\examples\cnc_mount_precision_params.json `
  --failure-policy strict `
  --output-dir C:\CADAutomationWorkbench\solidworks_fillet_chamfer_output
```

`strict` forbids altering requested dimensions; `progressive` tries 100%/75%/50%, and any degraded result must be delivered with its actual dimensions clearly reported.

For advanced capabilities, probe interfaces first, then selectively run live-machine verification:

```powershell
py subskills\solidworks-fillet-chamfer-cnc\scripts\verify_advanced_fillets.py `
  --verify-solidworks `
  --modes variable face surface_combo full_round setback width_width_chamfer `
  --output-dir C:\CADAutomationWorkbench\advanced_fillet_verified
```

Reports use `interface_ready` to mean "the interface exists" and `verified` to mean "real modeling, rebuild, save, STEP export, reopen, and preview review all passed"—never conflate the two. All six samples above have completed closed-loop live verification on SolidWorks 2026 SP1.1. Hold-line Fillets are not merely a Python limitation: C# PIA, SWBasic, and officially required in-process unmanaged C++ were all re-tested and still fault at the `ISetHoldLines` boundary on the current build, so the default safely returns `blocked`. Other SolidWorks service packs must be re-verified in an isolated instance.

Complex open-source cases:

```powershell
py subskills\solidworks-fillet-chamfer-cnc\scripts\verify_open_source_bracket.py `
  --source C:\CADAutomationWorkbench\sources\l_gusset.step `
  --source-commit 5b285130bff480cda282499e83604b295dd0aa4d `
  --version 2026 `
  --output-dir C:\CADAutomationWorkbench\opensource_l_gusset

py subskills\solidworks-fillet-chamfer-cnc\scripts\verify_open_source_complex_case.py `
  --version 2026 `
  --output-dir C:\CADAutomationWorkbench\opensource_corner_bracket
```

## Directory Structure

```text
solidworks-fillet-chamfer-cnc/
├── SKILL.md
├── README.md
├── manifest.yaml
├── agents/
├── references/
│   └── cnc-fillet-chamfer-lessons.md
├── examples/
│   ├── cnc_mount_precision_params.json
│   └── open_source_corner_bracket_case.json
└── scripts/
    ├── cnc_strategy.py
    ├── advanced_fillet_strategy.py
    ├── create_cnc_mount_template.py
    ├── verify_advanced_fillets.py
    ├── verify_open_source_bracket.py
    └── verify_open_source_complex_case.py
```

## Related Capabilities

- Parent skill: `solidworks-automation`
- Upstream planning: `solidworks-vibecad`
- If the part contains real threaded holes, pair with `solidworks-threaded-holes`.
