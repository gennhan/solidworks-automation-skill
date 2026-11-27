---
name: autocad-automation
description: "AutoCAD automation skill. Enables Codex/Claude on Windows to connect directly to local AutoCAD via Python COM/ActiveX for 2D drafting, layer/text/dimension/block handling, DWG/DXF/PDF export, batch modification, drawing self-inspection, and switching to AutoLISP/SCR or AutoCAD .NET plugin workflows when COM is insufficient. Prioritize this skill whenever the user mentions AutoCAD, CAD, DWG, DXF, 2D drafting, plotting, layers, dimensions, blocks, batch drawing edits, AutoLISP, ObjectARX, .NET plugins, or integrating Codex with CAD software."
metadata: { "os": ["win32"], "requires": { "anyBins": ["python", "py"], "pythonPackages": ["pywin32"] } }
---

# AutoCAD Automation Skill

> This directory serves as the AutoCAD/DWG subskill of `solidworks-automation-skill`. The parent skill handles SolidWorks modeling, Assembly, Drawing, and 3D export; this subskill handles AutoCAD 2D DWG/DXF drafting, batch drawing modification, line-art vectorization, plot preview, and drawing self-inspection. Return to the parent skill for native SolidWorks Part/Assembly modeling, and read this subskill for AutoCAD drawings or DWG/DXF tasks.

## Objective

Enable agents to reliably control AutoCAD in a local Windows desktop environment instead of assembling ad-hoc commands from memory. The default route is Python + COM/ActiveX, but native writing must first pass the `capabilities.yaml` gate and live-machine regression tests; currently, AutoCAD 2024's `Documents`/`Layers`/`SelectionSets` dynamic proxies are unstable, so native COM DWG drafting is treated as `not_implemented`. Headless DXF reading, preview, and structural inspection can be used directly. The AutoCAD 2024 .NET allowlisted backend has passed consecutive regressions for real DWG save/reopen, PDF/PNG export, and entity/layer/dimension checks, reaching `verified` status when runtime evidence is complete; only fixed commands are permitted, and it must never be generalized into arbitrary code execution.

## Applicable Scenarios

Use this skill for:

- Creating or modifying DWG/DXF drawings, drafting lines, circles, arcs, polylines, rectangles, text, blocks, layers, and basic dimensions.
- Batch-opening DWGs to inspect layers, entity counts, text, block references, external references (Xrefs), or output files.
- Having Codex connect directly to local AutoCAD, save DWGs, export DXF/PDF, and generate review reports.
- Writing AutoLISP, `.scr` command scripts, or C# AutoCAD .NET plugins.
- Looking up official Autodesk APIs, ADN/GitHub samples, ObjectARX SDK, or APS Design Automation patterns.

Do not use this skill for pure photorealistic rendering, BIM/Revit models, mechanical STEP-first 3D modeling, CAM toolpaths, or engineering certification sign-off; route those requests to the appropriate CAD, BIM, simulation, or manufacturing workflows.

## Default Assumptions

- Operating system: Windows.
- AutoCAD: Installed locally on the user's machine, ideally launched manually at least once to complete COM registration.
- Automation entry point: `AutoCAD.Application` COM ProgID.
- Visual default: For new drafting tasks, show and activate AutoCAD first, then draw entities step-by-step; disable live preview only for batch jobs or when the user explicitly requests faster execution.
- Drawing units: Assumed to be millimeters by default; the AutoCAD database itself stores unitless numeric values, so units must be recorded in drawing notes.
- Space: Geometry defaults to ModelSpace; layouts, title blocks, and plot configurations are handled separately.
- Coordinates: WCS by default; 2D objects use `Z=0`.
- Output: Save DWG first, and export DXF/PDF per user requirements; use absolute paths for all output paths.
- File safety: Save a copy before modifying an existing DWG unless the user explicitly authorizes overwriting.

If version, units, drawing standard, output path, or overwrite permission is missing, ask briefly to confirm. For simple sketches, assume millimeters, ModelSpace, and a new DWG, and state those assumptions in the result.

## Entry Preflight Check

Before running AutoCAD automation, run:

```powershell
python subskills\autocad-automation\scripts\acad_preflight.py
```

If the user allows launching AutoCAD automatically:

```powershell
python subskills\autocad-automation\scripts\acad_preflight.py --launch
```

If the preflight check fails:

- Missing `pywin32`: prompt the user to install `python -m pip install pywin32`, and install only after explicit approval.
- AutoCAD COM not found: prompt the user to install AutoCAD, launch AutoCAD once manually, or confirm whether AutoCAD LT / a restricted environment is installed.
- AutoCAD is running with no active document: create a new document rather than misreporting a connection failure.

## Core Workflow

When a project provides sheet-size and title-block rules, run `scripts/acad_headless.py drawing.dxf --template project-drawing.json --json drawing-checklist.json`. See [DXF Project Template Review](README.md#dxf-项目模板复核) for template fields and the A4 sample; the report preserves manual review items for dimension clearance and plot readability.

1. **Classify the task**: Determine whether it is new drafting, modifying an existing DWG, batch processing, plotting/export, API development, plugin development, or troubleshooting.
2. **Confirm key constraints**: Units, version, target file, output formats, overwrite permission, layer/linetype/dimension standards, and whether a company template is required.
3. **Run preflight**: Use `acad_preflight.py` first to verify Python COM and AutoCAD status.
4. **Verify APIs**: For unwrapped APIs, read `references/api-lookup.md` first, then consult official Autodesk documentation or trusted GitHub examples; never guess long parameter lists, enum values, or command behaviors.
5. **Create a drafting plan**: Specify layers, coordinate datums, entity list, dimensions, text, output paths, and review checkpoints.
6. **Launch the application first**: Connect to or launch AutoCAD, ensure the window is visible and brought to the foreground where possible, then start creating entities.
7. **Reuse existing scripts first**: Use `scripts/acad_draw.py` with JSON input for simple geometry; compose COM calls via `scripts/acad_session.py` for complex logic.
8. **Run COM serially**: Never run desktop AutoCAD COM operations in parallel; use a single script to connect, draw incrementally, save, verify, and exit.
9. **Save and export**: Ensure target directories exist before saving DWG/DXF/PDF; keep a backup or save a copy when modifying existing drawings.
10. **Verify results**: Run `scripts/acad_review.py` to tally entities, layers, bounding boxes, and output files; then run `scripts/acad_preview.py` to export an AutoCAD native BMP/PNG preview and visually inspect it with an image viewer. OS window screenshots may supplement this, but cannot serve as pass evidence if occluded by other windows.
    If the input is a DXF and only headless read-only inspection is needed, run `scripts/acad_headless.py` first; it does not support DWG writing, so final DWG/PDF outputs still require AutoCAD COM.
11. **Capture lessons learned**: Record newly discovered pitfalls, command differences, version limitations, or stable wrappers in `references/troubleshooting.md` or the scripts.

### Hard Requirements for Mechanical Part Drawings and 3D-Printed Enclosure Cutout Drawings

When the user requests "strict adherence to standards", "standard Chinese engineering drawing format", "GB/T drawings", "machining drawings", "3D-printed enclosure cutouts", or similar mechanical drafting deliverables, treat the output as an engineering drawing rather than a schematic diagram:

1. Prioritize the user's or company's template; without a template, follow common Chinese GB/T conventions including at least an A3/A4 sheet size, binding margin, lower-right title block, FangSong (仿宋) Chinese font, and separate layers for thick solid lines, thin solid lines, centerlines, hidden lines, dimensions, text, and cutouts, and state clearly in the delivery notes: "Styled after GB/T conventions; does not replace formal company drawing review." Whenever the user requests TCVN or Vietnamese mechanical standards, load `references/tcvn_mechanical.md` (from the root skill directory) instead of GB/T defaults for sheet margins, title block/BOM layout, First-Angle projection, fits, GD&T, and weld symbols.
2. Every actual cutout, hole, slot, port, gate/spigot, screw hole, and screw boss must specify both size and locating dimensions. Writing only `4×φ3.4`, `7×4×30`, or `2×φ13.5` without distances from datum edges, center-to-center spacing, pitch, or height locations counts as incomplete.
3. When holes/slots are dense or would require long leaders crossing views, prefer a hole/slot schedule (hole table / slot table) listing at least feature location/ID, size, quantity, and coordinates; use on-view dimension lines for key datums, center distances, and overall dimensions.
4. Do not use arbitrary long leaders to replace dimension chains; leaders must not cross other views, centerlines, hole outlines, or dimension text. If clean annotation is impossible, reposition views, split views, or switch to a table.
5. 3D-printed enclosure drawings must clearly dimension wall thickness, base thickness, overall external dimensions, port cutout sizes, port center locations, mounting-hole center distances, and spigot/ventilation-slot locations; otherwise the user cannot cut or verify openings from the drawing.
6. Dimensions must use real AutoCAD dimension entities such as `AcDbRotatedDimension`; do not manually draw lines and text to mimic dimensions.
7. Visual acceptance cannot rely on entity counts alone. Export a preview and visually inspect for missing dimensions, overlapping text, dimension lines colliding with views, leaders crossing views, readable hole tables, and title-block intrusion. Fix all issues before reporting completion.

## Direct Drafting with Codex

For simple tasks, have Codex generate a drafting JSON and invoke:

```powershell
python subskills\autocad-automation\scripts\acad_draw.py `
  --input C:\temp\plate_plan.json `
  --output C:\temp\plate.dwg `
  --new
```

This entry point defaults to "visible step-by-step drafting" mode: it opens or activates AutoCAD first and draws entities incrementally. Add `--fast` only for batch tasks, slow playback, or when the user explicitly requests faster execution:

```powershell
python subskills\autocad-automation\scripts\acad_draw.py `
  --input C:\temp\batch_plan.json `
  --output C:\temp\batch.dwg `
  --new `
  --fast
```

JSON structure example:

```json
{
  "units": "mm",
  "live_preview": true,
  "live_zoom_every": 6,
  "layers": [
    {"name": "OUTLINE", "color": 7},
    {"name": "CENTER", "color": 1},
    {"name": "TEXT", "color": 3}
  ],
  "entities": [
    {"type": "rectangle", "origin": [0, 0], "width": 120, "height": 80, "layer": "OUTLINE"},
    {"type": "circle", "center": [20, 20, 0], "radius": 4.5, "layer": "CENTER"},
    {"type": "text", "text": "MOUNTING PLATE", "point": [8, 88, 0], "height": 5, "layer": "TEXT"}
  ]
}
```

Use Python for complex tasks:

```python
import sys
sys.path.insert(0, r"subskills\autocad-automation\scripts")
from acad_session import AutoCADSession

session = AutoCADSession(create_if_missing=True, visible=True).connect()
session.new_document()
session.activate_window()
session.create_layer("OUTLINE", color=7)
session.add_rectangle((0, 0), width=120, height=80, layer="OUTLINE")
session.live_update(step_delay_s=0.15, zoom=True)
session.save_as(r"C:\temp\plate.dwg")
```

## Technical Route Selection

| Requirement | Preferred Route | Notes |
|---|---|---|
| Rapid drafting, drawing edits, batch inspection | Python COM/ActiveX | Default route for this skill; executable directly by Codex via shell |
| Running AutoCAD commands, reusing command workflows | `SendCommand` / `.scr` / AutoLISP | Commands may run asynchronously; always save and verify results |
| Heavy database transactions, complex selection filters, plugin menus | AutoCAD .NET | Suitable for C# plugins; follow the official .NET Developer's Guide for transactions and document locking |
| High-performance native extensions, deep database/graphics access | ObjectARX C++ | High development cost and tight version coupling; confirm necessity first |
| Cloud batch processing of DWGs | APS Design Automation | Suitable for headless, bulk production, or CI, but requires Autodesk APS credentials |

## Engineering Rules

- Create layers before drawing entities, using ACI color indices; never dump all objects onto layer `0`.
- Specify units and scale explicitly; draw 1:1 in ModelSpace and configure plot scale in Layout/Plot.
- Store key parameters such as coordinates, dimensions, text heights, and hole diameters as variables rather than scattering magic numbers through code.
- For mechanical drawings, do not confuse "visually understandable" with "manufacturable". Cutouts and slots must have verifiable datums and complete locating dimensions; when drawing space is tight, use a hole/slot table instead of stray callout leaders.
- When generating line art from a reference image, a standard "trace image to CAD" deliverable must rely strictly on vectorized lines from the original image. Do not manually add guessed large arcs, long polylines, ellipses, triangles, colored splash waves, or placeholder text to fill in portraits, facial features, logos, folds, or splashes; users perceive these as erroneous CAD construction lines.
- If construction or enhancement layers such as `BODY_OUTLINE`, `JERSEY_OUTLINE`, `PORTRAIT_OUTLINE`, `OUTER_GUIDE`, `CONSTRUCTION`, `FACE_FEATURES`, `LOGO_GEOMETRY`, `WATER_SPLASH`, `JERSEY_STRIPE`, `TEXT_LOGO`, or `TEXT_BRAND` were created for positioning, debugging, or temporary recognition aid, they must be deleted, frozen, turned off, or set to non-plotting before final save, preview, and scoring, and verified as invisible with 0 entities in both preview and layer statistics.
- Retain manually enhanced layers only when the user explicitly requests creative edits such as "reconstruct logo", "enhance facial features", "add water splashes", or "add text/callouts"; clarify beforehand that they are not raw traced vectors and place them on dedicated layers for easy toggling.
- Put review notes, scores, and generation parameters into JSON/Markdown reports—never write them as visible text into final CAD ModelSpace unless the user explicitly asks for in-drawing notes.
- Validate COM return objects, and verify file existence and reasonable file size after every save/export.
- Treat `SendCommand` as a last resort; prefer object model methods, and prefix script commands with `_.COMMAND` to avoid UI-language localization issues.
- When the user explicitly says "I want to watch it draw", do not generate silently in the background; open and foreground AutoCAD first, then place entities step-by-step.
- `SelectionSet` names can persist in a drawing; delete any existing selection set with the same name before creating a new one.
- During batch DWG processing, wrap each drawing in its own `try/finally` block and log the filename, error, and stage on failure.
- Open existing user drawings read-only or save to a copy by default; explicit authorization is required before overwriting.
- Never expose arbitrary Python/VBA/AutoLISP execution as a generic MCP tool; if building an MCP server, expose only allowlisted drafting/export/review tools.

## GitHub & Official Documentation Policy

Preferred sources:

- Autodesk AutoCAD API Overview, ActiveX/VBA, Managed .NET, ObjectARX, and APS official documentation.
- ADN-DevTech / Autodesk Platform Services GitHub examples.
- Mature open-source projects such as `pyautocad` may be referenced for coordinate handling, iteration, and COM wrapper patterns, but do not copy code with unclear licensing.
- Forums, blogs, and Stack Overflow are supplemental for troubleshooting only; confirm key APIs against official documentation.

When sources conflict, defer to the official documentation for the target AutoCAD version and local machine test results.

## Progressive References

Read on demand rather than loading everything into context at once:

- `references/api-lookup.md`: Official documentation, GitHub samples, and API verification workflow.
- `references/engineering-patterns.md`: Senior engineering practices for drafting, layers, units, blocks, dimensions, and batch processing.
- `references/troubleshooting.md`: Troubleshooting COM, AutoCAD sessions, `SendCommand`, saving/exporting, and version issues.

## Acceptance & Reporting

After completing AutoCAD operations, the final report must include:

- Input assumptions: units, version, template, and whether a new drawing was created or an existing one modified.
- Output files: absolute paths to DWG/DXF/PDF/JSON reports and BMP/PNG previews.
- Verification actually performed: preflight, entity counts, layer counts, bounding box, save/export checks, and visual review of AutoCAD native preview images; for raster-to-CAD line art, also confirm that the final preview shows no extra outer guide contours, internal construction geometry, colored decorative lines, or in-drawing review notes; if OS window screenshots were used, state whether the window was unobstructed.
- Items still requiring manual confirmation: title block/border, plotter, company standards, lineweights, fonts, scale, and formal engineering drawing review.
