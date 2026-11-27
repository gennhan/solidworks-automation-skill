# AutoCAD Automation Subskill

> Headless DXF preview and structural review are currently available; the AutoCAD 2024 .NET allowlisted backend has passed consecutive regressions for real DWG/PDF/PNG generation, reopening, and entity/layer/dimension checks, reaching `verified` status after runtime re-verification of the last three evidence runs. Native ActiveX/COM writing remains gated by live-machine verification and must not be advertised as a stable capability.

This subskill provides specialized AutoCAD / DWG / DXF capabilities within the `solidworks-automation-skill` library. The parent skill handles SolidWorks 3D modeling, Assembly, Drawing, and export; this subskill handles Python COM automation for Windows desktop AutoCAD, including 2D drafting, batch drawing modification, layer/text/dimension handling, DWG/DXF/PDF export, line-art vectorization, and drawing self-inspection.

## Applicable Scenarios

- The user asks to "draw a DWG / DXF / AutoCAD drawing".
- Converting raster line art into CAD lines and saving as DWG/DXF.
- Batch-inspecting layers, entity counts, bounding boxes, text, blocks, external references (Xrefs), or output files.
- Visibly drawing step-by-step in AutoCAD and exporting native previews for review.
- Supplementing SolidWorks engineering workflows with 2D AutoCAD drawings, machining profiles, laser-cutting DXFs, or drawing cleanup.

## Relationship to the Parent Skill

- `solidworks-automation`: SolidWorks COM connection, Part/Assembly/Drawing modeling, STEP/STL/PDF export, and 3D review.
- `autocad-automation`: AutoCAD COM connection, 2D DWG/DXF drawing generation, layer/dimension/block handling, AutoCAD native preview, and drawing self-inspection.

When a task requires native SolidWorks Parts, Assemblies, or Drawings, prioritize the parent skill; when a task explicitly involves AutoCAD, DWG, DXF, 2D CAD drawings, line-art-to-CAD tracing, or batch DWG modification, read this subskill.

## Quick Commands

Check and run regression tests for the AutoCAD .NET backend:

```powershell
python subskills\autocad-automation\scripts\acad_dotnet_preflight.py
python subskills\autocad-automation\scripts\acad_dotnet_regression.py --real-cad
```

The regression script launches only the AutoCAD Core Console process it owns and executes only the fixed commands `CADSTUDIOPROBE` and `CADSTUDIOCREATE`. Desktop AutoCAD deployments must use trusted paths or signed plugin bundles and must not expose arbitrary code execution entry points.

```powershell
python subskills\autocad-automation\scripts\acad_preflight.py --launch
```

```powershell
python subskills\autocad-automation\scripts\acad_draw.py `
  --input C:\temp\plan.json `
  --output C:\temp\result.dwg `
  --new
```

```powershell
python subskills\autocad-automation\scripts\acad_review.py C:\temp\result.dwg `
  --launch `
  --json C:\temp\review.json
```

```powershell
python subskills\autocad-automation\scripts\acad_preview.py `
  --source C:\temp\result.dwg `
  --output C:\temp\preview.png `
  --launch
```

## Hard Rules for Line-Art-to-CAD Tracing

The final deliverable for a standard "trace image to CAD" task must retain only the vectorized lines from the source image. Do not leave manually guessed outer outlines, facial ellipses, logo triangles, water-splash curves, placeholder text, or in-drawing review notes in the final DWG/DXF.

During final review, verify that all of the following auxiliary layers have 0 entities:

```text
PORTRAIT_OUTLINE, BODY_OUTLINE, JERSEY_OUTLINE,
OUTER_GUIDE, CONSTRUCTION, FACE_FEATURES,
LOGO_GEOMETRY, WATER_SPLASH, JERSEY_STRIPE,
TEXT_LOGO, TEXT_BRAND, REVIEW_NOTES
```

This rule comes from a real line-art demo postmortem: contour lines, ellipses, triangles, and colored wave lines added by AI to "enhance recognition" appear as stray entities to CAD users. For subsequent standard line-art tasks, cleanliness, fidelity, and zero extraneous entities are the top priority.

## Reference Documents

- `SKILL.md`: AI invocation entry point and complete workflow.
- `references/api-lookup.md`: AutoCAD API verification path.
- `references/engineering-patterns.md`: Best practices for layers, units, blocks, dimensions, and batch processing.
- `references/troubleshooting.md`: Troubleshooting local COM, DXF/BMP export, line-art contamination, and verification pitfalls.
## DXF Project Template Review

Copy the [A4 Landscape Sample](examples/dxf-checklist-a4.json) as your project configuration, then check drawing outputs using the same rule set.

```powershell
python subskills/autocad-automation/scripts/acad_headless.py drawing.dxf --template project-drawing.json --json drawing-checklist.json
```

- `sheet.size` supports A0–A4, and `orientation` selects landscape or portrait. `insetsMm` specifies the drawing border insets relative to the sheet edges in left, bottom, right, top order. The template measures closed rectangular borders from `frameLayers`.
- `layout` defaults to `Model`, or a Paper Space layout name can be specified. Only entities in the selected space are checked; Model Space entities displayed inside Paper Space viewports must be reviewed separately. Borders and title blocks built from closed lightweight polylines are supported, and text and visible attributes inside standard blocks are included in the check. External references (Xrefs) should be reviewed separately per project workflow.
- `titleLayers` specifies the layers containing the title block; `titleSizeMm` and `titleAnchorMm` configure the outer frame width/height and its position relative to the lower-left corner of the drawing border. Field text is read from inside that outer frame.
- Configure per-project rules for real dimension count, expected dimension values and tolerances, layer lineweights, minimum title text height, as well as scale, projection, or technical requirement text. Dimension values use each entity's raw measured units; scale and projection labels only check whether the text appears.

The report's `drawingChecklist` records the actual check template, input SHA-256 hash, measurement conclusions, and manual review items. Automated check failure exits with code 1; passing exits with code 0 and sets the report status to `review_required`. Dimension overlap avoidance, plot readability, dimension chains, BOM, and archive revision must be verified manually.
