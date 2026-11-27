# Drilling Panel Analysis (pilot)

`drilling_panel_gdt.py` detects hole-pattern arrays on a panel, computes a candidate coordinate table, and proposes a datum scheme. The output is a **candidate proposal** for design-engineer review and does not automatically deliver a released Engineering Drawing. It references community contribution [PR #36](https://github.com/wzyn20051216/solidworks-automation-skill/pull/36).

By default, it does not guess hole functions or generate position tolerances, flatness, or material condition modifiers. When GD&T candidates are required, an engineer must explicitly supply a `--gdt-profile` JSON containing `positionToleranceMm`, `dowelPositionToleranceMm`, `flatnessMm`, `materialCondition`, and `datumRefs`. Computed results still require human review and cannot replace design inputs or standards-compliance sign-off.

The legacy helper `default_gdt_profile()` returns only an example tagged with `_exampleOnly`; it cannot be used directly for candidate generation—actual tolerances must come from engineering design inputs.

Analyze from a neutral document (requires a real model path and `metadata.plate` width, height, and thickness):

```powershell
python subskills/solidworks-engineering-drawing/scripts/drilling_panel_gdt.py panel.cadstudio.json --source-model C:\work\panel.SLDPRT --analysis-out panel_analysis.json --spec-out panel_spec.json
```

Read directly from a saved SolidWorks Part:

```powershell
python subskills/solidworks-engineering-drawing/scripts/drilling_panel_gdt.py --from-model C:\work\panel.SLDPRT --analysis-out panel_analysis.json --spec-out panel_spec.json
```

Output files use exclusive creation and never overwrite existing files. The real model path comes from the opened document; using a managed session ensures pre-existing user documents are not closed as documents opened by this run. Unsaved models, missing bounding boxes, or B-Rep read errors block drawing-spec generation.

The panel normal is inferred from the thinnest bounding-box axis; this heuristic applies only to simple axis-aligned panels. `GetPartBox` returns an [approximate bounding box](https://help.solidworks.com/2013/English/Api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IPartDoc~GetPartBox.html) and must not be treated as exact plate edges or machining dimensions; warnings are preserved in the output. When valid bounds are absent, the script no longer expands bounds from hole positions or fabricates plate thickness. When a neutral document omits the plate origin, the output explicitly notes that `(0, 0)` was assumed and must be confirmed by the designer.

Hole walls must have valid axes, and coaxial segments are merged within a 0.01 mm tolerance; geometry alone cannot prove through-holes, threads, counterbore functions, or dowel pins. Bounding boxes, datum planes, hole types, edge distances, and material conditions must all be verified against the real model and design intent. Tilted panels, multi-body parts, stepped holes, and complex geometry require separate verification.

SolidWorks 2026 SP1.1 has been verified on an 80×60×20 mm four-hole plate for save, reopen, and readback of the four hole axes and diameters. That proves only that the analysis path works on this sample—it **does not verify other SolidWorks versions or actual GD&T/hole-table placement onto drawings**. A candidate `drawing_spec` is not equivalent to a generated or manufacturable Engineering Drawing.
