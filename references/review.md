# Self-Review Reference

## Mandatory Checks

After generating, modifying, or exporting SolidWorks files, verify at least the following:

1. COM calls do not return `None`, and all critical feature objects are created successfully.
2. `save_document()`, `session.save()`, and `session.export()` return success.
3. Output `.sldprt` / `.sldasm` / `.slddrw` / `.step` / `.stl` files actually exist on disk with reasonable file sizes.
4. Model is rebuilt: `model.ForceRebuild3(False)`.
5. Model is zoomed to fit the viewport: `model.ViewZoomtofit2()`.
6. At least one isometric BMP preview is exported; for complex models, also export front, top, and right views.

## Structured Self-Review Report

```python
import sys
sys.path.insert(0, r"SKILL_DIR/scripts")

from sw_review import run_review

model.ForceRebuild3(False)
report, report_path = run_review(
    model,
    r"C:\temp\solidworks_review",
    basename="model",
    views=("isometric", "front", "top", "right"),
    expected_outputs=[r"C:\temp\model.sldprt", r"C:\temp\model.step"],
)
print(report_path)
print(report["checks"])
```

`run_review()` outputs:

- Multi-view BMP preview images.
- `*_review_report.json` structured report.
- `*_review_summary.md` human-readable summary suitable for delivery notes, Issues, or PRs.
- `evaluation.status`: `pass` / `warn` / `fail`.
- `evaluation.score`: Rule-based score out of 100.
- `evaluation.issues`: Machine-readable list of issues.
- `evaluation.recommendations`: Remediation suggestions.
- `checks.previews_created`: Whether preview images were generated.
- `checks.previews_not_blank`: Whether preview images appear non-blank.
- `checks.expected_outputs_exist`: Whether expected output files exist with size > 0.
- `checks.feature_summary_available`: Whether the FeatureManager tree summary was readable.

Note: Structured reports only catch obvious failures and cannot replace human or vision-model judgment of geometric design intent.

Manufacturing-grade tasks must also output standalone machine-readable specification evidence, for example:

```json
{
  "cad_spec": {
    "envelope_mm": {"length": 60, "width": 40, "thickness": 12},
    "holes": [
      {"diameter_mm": 10, "count": 1, "positions_xy_mm": [[0, 0]]},
      {"diameter_mm": 4, "count": 4, "positions_xy_mm": [[-24, -14], [24, -14], [-24, 14], [24, 14]]}
    ]
  },
  "measurement_source": "SolidWorks API/B-Rep/参数回读",
  "units": "mm"
}
```

When a task specifies explicit outer dimensions or hole diameters but the deliverables lack standalone JSON evidence, the Reviewer Gate must fail; prose summaries or "executor self-reported pass" cannot substitute for evidence. Hole counts, positions, edge distances, center distances, fillets, wall thicknesses, and assembly degrees of freedom should also be recorded per task requirements.

For complex holes and slots, `collect_geometry_measurements()` also outputs:

- `hole_groups`: Hole segments grouped by spatial axis.
- `compound_holes`: Coaxial multi-diameter counterbore/compound hole candidates.
- `slot_arc_candidates`: Internal cylindrical faces with multiple bounding edges representing slot end arcs, excluded from circular hole counts.
- `validate_hole_positions()`: Per-hole acceptance check by axis distance and diameter tolerance.

```python
from sw_review import collect_geometry_measurements, validate_hole_positions

measurements = collect_geometry_measurements(model)
position_checks = validate_hole_positions(
    measurements,
    [{"id": "H1", "diameter_mm": 8, "position_mm": [20, 20, 0]}],
    position_tolerance_mm=0.1,
    diameter_tolerance_mm=0.05,
)
assert position_checks["status"] == "pass"
```

Note: Cylindrical B-Rep faces prove hole diameter, axis, and cylinder length, but cannot reliably distinguish blind vs. through holes on their own. Blind depths, countersink angles, and hole types must be cross-verified against creation parameter evidence from `sw_hole_features.py` or feature definition readback.

## One-Click CLI Review

```bash
python scripts/sw_review.py ^
  --file C:\temp\model.sldprt ^
  --output-dir C:\temp\solidworks_review ^
  --basename model ^
  --expected C:\temp\model.sldprt ^
  --expected C:\temp\model.step
```

Exit codes:

- `0`: `pass` or `warn`, report generated.
- `1`: `--fail-on-warn` was passed and status is `warn`.
- `2`: `fail`, blocking issues must be fixed.

## Visual Self-Check Checklist

- Is the main body visible in frame, rather than blank or showing only sketches?
- Are all critical components present (e.g., wheels, holes, shafts, housings, brackets, BOM table)?
- Are cut features, holes, and slots that succeeded in the feature tree actually visible on the expected faces? (`feature is not None` does not guarantee correct geometric intent.)
- Are proportions obviously wrong (e.g., millimeters mistakenly passed as meters creating a giant model)?
- Are orientations correct (e.g., wheels mounted on the sides rather than the roof)?
- Are any components visibly overlapping, floating, intersecting, or missing mates/constraints?
- Do file names, output directories, and export formats match the user's request?

## When Issues Are Found

1. Do not simply report "file saved."
2. First diagnose whether the root cause is the sketch, selection, extrusion direction, units, reference plane, or export failure.
3. Update the script, regenerate the model, and re-export preview images.
4. Clearly state which preview views were checked and any remaining limitations in the final response.
