# SolidWorks 2026 Native GD&T and Structured Drawing Generation (pilot)

Finished dimensioned drawings can have genuine `DatumTag` and modern XML `GTol` annotations added via `scripts/sw_gdt_copy.py`.
This entry point handles only **SW2026, single-sheet, single-part, landscape A3, millimeter-unit** drawings and never modifies the source drawing or source part.
The source model must already be saved with verifiable references. It is separate from the generic `solidworks_generate_drawing` capability preflight and never treats free-text requirements in legacy `DrawingSpec` files as executable GD&T.

## Execution Order for Natural-Language Requests

When a user asks to "add datums / position tolerances / other GD&T to a drawing", the agent should read this file first and perform a read-only target inspection:

```powershell
python scripts/sw_gdt_copy.py --source C:\work\plate.slddrw --inspect
```

The output includes `sourceSha256`, actual sheet/view names, dimension selection names and SI values, visible line endpoints, and circular edge centers/radii.
Edge coordinates are in **model coordinates in millimeters**, not sheet coordinates; `positionMm` is in sheet coordinates.
Ambiguous multi-candidate targets such as concentric or projection-overlapping edges are never guessed by nearest point, `Edge1`, or fuzzy scoring.
Dimension selection requires exact matching on both name and `systemValue`, where `systemValue` uses SolidWorks SI units.

Datum features, controlled features, tolerance values, material conditions, and datum precedence must come from the user's engineering requirements.
Consulting official API docs resolves how to call methods, but cannot substitute for design inputs. When design inputs are missing, remain in read-only analysis and never fill in production tolerances autonomously.

Build a plan conforming to `schemas/gdt_copy_spec.schema.json`, then execute:

```powershell
python scripts/sw_gdt_copy.py --source C:\work\plate.slddrw --plan C:\work\gdt-plan.json --output-dir C:\work\annotated-copy
```

The plan contains `schemaVersion="1.0"`, source SHA-256, actual `sheet`, `paperSize="A3"`, `datums`, and `geometricTolerances` arrays. Each entry requires a unique `id` and actual `view`.

- Datum: `label`, `displayStyle="square"` or `"round_gb"`, `positionMm`, and an unambiguous edge `target`.
- Tolerance: `characteristic`, positive decimal string `tolerance` (mm), boolean `diameter`, explicitly ordered `datums`, and `target`.
- Optional `materialCondition`: `null`, `"M"`, `"L"`, or `"S"`; currently enabled only for cylindrical position and axis straightness tolerances.
- Edge targets require `positionMm`; dimension targets are auto-anchored by SolidWorks and must not also specify a position.
- Line target: `{ "kind": "line", "startMm": [x,y,z], "endMm": [x,y,z] }`.
- Circular edge target: `{ "kind": "circle", "centerMm": [x,y,z], "radiusMm": r }`; a circular edge does not automatically prove hole type or a full 360° circle.
- Dimension target: `{ "kind": "dimension", "name": "actual selection name", "systemValue": 0.01 }`.

Form tolerances must not reference datums; tolerances requiring datums must not omit them; referenced datums must already exist or be created in the current plan, and duplicate datum labels are blocked.
Supported single-frame native symbols: `straightness`, `flatness`, `circularity`, `cylindricity`, `line_profile`, `surface_profile`, `parallelism`, `perpendicularity`, `angularity`, `position`, `concentricity`, `symmetry`, `circular_runout`, and `total_runout`. Being writable does not guarantee suitability for the chosen standard or controlled geometry.
Supports 1..8 stacked independent frames and composite frames. When using the `frames` array, legacy single-frame fields must not be supplied alongside it; each layer explicitly defines `characteristic`, `tolerance`, `diameter`, and `datums`, with subsequent composite layers setting `composite: true`.
The first layer must retain its characteristic symbol; subsequent composite layers share the same characteristic and tolerance-zone type with non-increasing tolerance values, may retain only a prefix of the previous layer's datums and modifiers in order, and may omit datums.
Datum references accept both `"A"` and `{ "label": "A", "materialCondition": "M" }` (`M`/`L`/`S`/`null`), independent of the tolerance value's own `materialCondition`. Whether a modifier is valid for the referenced feature of size must still be confirmed by the designer.
For common datums/datum sub-groups, projected tolerance zones, profile offsets, CZ/SZ, unit zones/maximum tolerances, reciprocity, and other frame modifiers, use the structured inputs in [gdt-extended-options.md](gdt-extended-options.md); arbitrary XML is rejected.

## Automated Drawing Generation from 3D Models

The existing MCP tool `solidworks_generate_drawing` shares the same generation and save-reopen verification pipeline as the following CLI without introducing new tools. Standard `DrawingSpec` views use `front`, `top`, and `right`, supporting both first-angle and third-angle projection.

```powershell
python scripts/sw_drawing_package.py --spec C:\work\drawing.json --output-dir C:\work\delivery
```

The native path requires SW2026, a millimeter-unit single part, explicit `modelSizeMm`, and a saved source model; supported sheet sizes are A4/A3/A2/A1/A0 (live-machine testing in this cycle covered A3 and A2; remaining sizes have not yet been individually verified).
`templateCandidates` provides local sheet-format candidates matching sheet size and standard, blocking explicitly if missing.
Source models and dependencies are opened read-only, with each hash recorded and verified.
Each `requiredDimensions` entry specifies a unique `id`, `kind` (`linear`/`overall`/`diameter`/`radius`/`angular`), standard `view`, `valueMm` (`valueDegrees` for angular), sheet coordinates `positionMm`, and an unambiguous `target` or pair of `targets`. Linear dimensions additionally require `axis: horizontal/vertical`.
`basic: true` creates a genuine basic-dimension box; hole counts may use `prefix: "4X "`.
Batch `insertModelDimensions: true` cannot be enabled when explicit dimensions are provided.
Views reserve default spacing for annotations, or may be placed explicitly via `views.front.positionMm`, etc.

`professionalAnnotations.datums` and `geometricTolerances` use the structured annotation fields above, except `view` uses standard view aliases. Tolerance frames can attach either to unambiguous edges or to dimensions created in the same run:

```json
{
  "id": "POSITION", "view": "front",
  "target": {"kind": "dimension", "dimensionId": "HOLES"},
  "frames": [
    {"characteristic": "position", "tolerance": "0.2", "diameter": true,
     "datums": [{"label": "A", "materialCondition": "M"}]},
    {"characteristic": "position", "tolerance": "0.1", "diameter": true,
     "datums": [{"label": "A", "materialCondition": "M"}], "composite": true}
  ]
}
```

The numbers here illustrate the API contract only and must not be used directly for production design. All datums must be declared in the current spec, and referenced dimension IDs must exist in the same view. Legacy free-text `text` fields remain review-only and are never guessed onto drawings.
Missing/ambiguous selectors, wrong values, cross-view references, missing datums, or invalid composite layers block execution rather than falling back to `Note`.
Unimplemented professional fields such as hole tables, threads, surface finish, and weld symbols remain explicitly blocked.

Persistent IDs, native types, basic-dimension flags, prefixes, full-layer XML, datum modifiers, and actual attachments for all dimensions and annotations are verified after save-and-reopen; the generated report also checks required dimensions, PDF values, and layout.
Even after native verification passes, the status remains `review_required`: dimension chains, leader crossings, and design tolerances must be manually reviewed, and automated manufacturing compliance must never be claimed.

## Meaning of Success and Failure

All targets are pre-resolved before creating the output directory; source-file changes, missing/ambiguous targets, or missing datums block execution.
Writes happen exclusively in a newly created copy. If a write fails, documents owned by the current run are closed and unsaved edits discarded; if an issue is detected after saving, the copy and failure manifest are retained for diagnosis and `outputs` will not report a successful delivery.
Pre-existing user edits are never undone in place, and user documents are never deleted.

After writing all annotations, the drawing is rebuilt and saved first, establishing the post-save layout as the reopen baseline; user-specified coordinates must still hold after saving and are never masked with post-save coordinates.
Upon reopen, every new annotation is checked for persistent annotation ID, persistent target ID, datum style/tolerance XML, and actual position; newly created annotations must not reuse old annotation IDs.
Even when `SetPosition` returns success on a dimension-attached `GTol`, SolidWorks may ignore it, so dimension targets use automatic position readback.
PDF/BMP files are then exported, dimensions are correlated with PDF text boxes, and layout plus source-file SHA-256 checks are run.
A successful run outputs `SLDDRW`, `PDF`, preview images, and `gdt-copy-manifest.json`, while keeping status at `review_required` (CLI exit code 2).
Newly added tolerance frames, datum leaders, dimension chains, and the title block must be visually inspected; automated layout checks cannot prove all GD&T leaders are crossing-free.
This entry point does not calculate appropriate tolerances, does not auto-complete all dimensions, and does not claim manufacturing or standards-compliance acceptance.

## Reproducible Verification

```powershell
python -m pytest -q tests/test_sw_gdt_annotation.py tests/test_sw_gdt_copy.py
python tests/solidworks_gdt_attachment_probe.py --copy-workflow
python tests/solidworks_gdt_symbol_matrix.py C:\test\attachment.slddrw
python tests/solidworks_gdt_advanced_live.py --source C:\test\attachment.slddrw --plan C:\test\gdt-plan.json
python tests/solidworks_gdt_generation_live.py
python tests/solidworks_gdt_generation_live.py --source C:\test\self-created-plate.sldprt --paper-size A2 --mcp
python tests/solidworks_gdt_generation_live.py --source C:\test\self-created-plate.sldprt --extra-dimensions
python tests/solidworks_drawing_failure_live.py --source C:\test\self-created-plate.sldprt
```

Live-machine scripts use only self-created temporary models. The symbol matrix requires a self-created test drawing containing Datum A and circular holes to verify writing, save-and-reopen, and non-dangling attachment for all 14 symbols plus `M`/`L`/`S` material conditions on position tolerances—**without validating the engineering soundness of those test tolerances**.
The full copy sample covers a four-hole plate, 8 dimensions, Datum A, and a position tolerance attached to a hole diameter dimension, plus missing-target and write-failure isolation tests.
Extended regressions cover independent dual frames, composite dual frames, and datum `M`/`L`/`S`; automated generation regressions verify 8 native dimensions, 4 basic dimensions, datums, and a dimension-attached composite frame across both the A3 script entry point and the A2 registered MCP function entry point (save-reopen/scale/PDF/layout). Extended samples additionally verify radius and angular dimensions (10 dimensions total), PDF recognition of degree symbols, and source-hash/owned-document cleanup on missing targets or wrong dimension values. Invoking registered MCP functions does not replace full client UI compatibility testing.
Live-machine scripts and `test_sw_read_guard` must not run concurrently because they share an inter-process mutex.

API references: [Modern Frame XML](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.interop.sldworks~SolidWorks.interop.sldworks.IGtolFrame~SetSymbolXml.html), [GTol XML Schema](https://help.solidworks.com/2026/english/api/sldworksapiprogguide/Overview/Gtol_Frame_XML_Schema.htm), [Datum Display Style](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IDatumTag~SetDisplayStyle.html).
