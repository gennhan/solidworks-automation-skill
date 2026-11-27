---
name: solidworks-threaded-holes
description: SolidWorks ISO metric internal threaded-hole automation subskill. Creates and reviews M3–M12 coarse or custom metric internal threads with explicit tap-drill diameters, covering tap-drill cuts, blind/through-all end conditions, hole-mouth Chamfers, right/left-hand threads, ThreadFeatureData/CosmeticThread fallbacks, and delivery evidence. Read this skill whenever the user asks for Hole Wizard, editing existing parts, external threads, imperial/pipe threads, or explicit thread profiles, while marking those capabilities as pilot or requiring manual review per the roadmap rather than claiming stable support.
---

# SolidWorks Threaded Holes

## Determine Capability Tier First

The current stable script is `scripts/create_threaded_hole_template.py`, which generates ISO metric internal threaded holes on a newly created rectangular coupon.

- `verified`: M3/M4/M5/M6/M8/M10/M12 coarse internal threads, blind or true `Through All` tap-drill holes, hole-mouth Chamfers, right/left-hand orientation, tolerance class properties, genuine `Metric Tap` `Thread` features, STEP export, and review evidence. Live-verified for both blind and through-holes on SolidWorks 2026.
- `reviewed`: Non-table ISO metric sizes; the user must explicitly provide `--tap-drill` rather than guessing the tap-drill diameter.
- `pilot`: Locating and modifying holes on existing parts, Hole Wizard/Advanced Hole, external threads, imperial/UN/UNF/NPT/BSP, multi-start threads, explicit swept thread profiles, and drill points/relief undercuts. Read the [Expansion Roadmap](references/threaded-hole-roadmap.md) before executing.

## Stable Workflow

1. Run `python scripts/sw_preflight.py` from the repository root.
2. Confirm thread callout, internal vs. external, tolerance class, handedness, blind vs. through, thread depth, tap-drill depth, hole coordinates, and whether an explicit physical thread profile is required.
3. Validate before COM that all values are finite, tap-drill diameter is strictly smaller than nominal diameter, thread depth does not exceed tap-drill depth or plate thickness, and hole location retains edge margin for the major diameter and Chamfer.
4. Create real tap-drill Cut geometry first: use `swEndCondBlind=0` for blind holes and `swEndCondThroughAll=1` for through-holes—never fake a through-hole with a "thickness + 1 mm" blind Cut.
5. Enumerate circular edges by center, radius, and entry plane rather than relying on `Edge1` or screen coordinates.
6. Attempt a real `Thread` feature: set `Type="Metric Tap"`, select the planar circular edge with selection mark `1`, do not assign the same circular edge to `StartEntity`, do not call the nonexistent `LoadReferences`, and do not override the tap-drill cylindrical diameter with the nominal major diameter.
7. If `Thread` fails, attempt `InsertCosmeticThread3`; use `swEndConditionThrough=2` for through cosmetic threads. A non-null COM return does not prove persistence—rebuild and traverse the FeatureManager tree.
8. Only when neither real nor cosmetic threads persist in the FeatureManager tree does `--visible-thread fallback` create a 3D Sketch helix. The helix allows fractional turns to preserve true pitch; export `*_thread_evidence.bmp` separately and then hide the Sketch so it does not pollute standard previews.
9. Add the hole-mouth Chamfer and write thread specification, tap-drill diameter, depth, tolerance class, handedness, end condition, and final representation status to custom properties.
10. Hide reference planes, save `SLDPRT`, export `STEP`, run `sw_review.run_review()`, and visually inspect the isometric and orthographic views.

## Template Usage

Default M6×1 right-hand 6H blind hole:

```powershell
python subskills/solidworks-threaded-holes/scripts/create_threaded_hole_template.py `
  --thread M6 `
  --output-dir C:\CADAutomationWorkbench\solidworks_threaded_hole_output
```

Non-table fine-pitch M8×1, left-hand, through-hole:

```powershell
python subskills/solidworks-threaded-holes/scripts/create_threaded_hole_template.py `
  --thread M8x1 `
  --tap-drill 7.0 `
  --through `
  --handedness left `
  --thread-class 6H `
  --output-dir C:\CADAutomationWorkbench\m8x1_lh_output
```

`--visible-thread` supports `fallback` (default), `always`, and `never`. Keep `fallback` for normal deliveries; use `always` only when debugging the helix.

## Delivery and Verification

Must generate:

- `*.SLDPRT`
- `*.step`
- `*_parameters.json`
- `*_review_report.json`
- `*_isometric.bmp` and three orthographic views
- `*_thread_evidence.bmp` only when a visible helix was created

Check `thread_attempts`, `thread_evidence`, and `thread_status` together in `*_parameters.json`. Deliver only when all of the following hold:

- `has_tap_drill_cut=true` and `has_mouth_chamfer=true`.
- `representation` is `real-thread`, `cosmetic-thread`, or an explainable `visible-helix`; `metadata-only` must block template delivery.
- Review flags `expected_outputs_exist` and `previews_not_blank` are `true`.
- Standard previews hide reference planes, show no 3D Sketch dashed lines bleeding through the solid, and display accurate hole location and Chamfer.

For detailed live-verified APIs, root causes, and official doc links, see [Threaded Hole Live Lessons](references/threaded-hole-lessons.md); for unimplemented capabilities and acceptance gates, see the [Expansion Roadmap](references/threaded-hole-roadmap.md).
