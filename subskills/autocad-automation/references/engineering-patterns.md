# AutoCAD Engineering Patterns

## Pre-Drafting Design

- Write a one-page drafting brief first: units, scale, coordinate origin, layers, linetypes, text height, dimension style, output paths, and acceptance criteria.
- For mechanical/architectural/electrical drawings, confirm industry standards and company templates first; without a template, use neutral layers and never fabricate a formal standard.
- Draft at true 1:1 scale in ModelSpace; handle borders, viewports, and plot scales in Layout.
- Choose the origin to support downstream referencing: mechanical parts typically use the lower-left corner or center; floor plans use the project datum point.

## Layers and Objects

- Create layers before drawing objects; at minimum separate `OUTLINE`, `CENTER`, `HIDDEN`, `DIM`, `TEXT`, and `CONSTRUCTION`.
- Place temporary guide lines on `CONSTRUCTION`, and delete or freeze them as required before task completion.
- Use blocks for repeated components; keep block names stable and use uppercase English attribute tags to avoid localization issues.
- External references (Xrefs), fonts, linetypes, and plot styles are delivery risk points; inspect them explicitly during batch processing.

## Dimensions and Annotations

- Dimensions, text, and lineweights should come from drawing standards; without a standard, add only essential text notes rather than pretending the output is a released production drawing.
- Dimension styles may depend on a template; verify `DIMSTYLE` before creating dimensions directly via COM.
- Base text height on drawing scale; writing fixed text heights in ModelSpace easily makes plots unreadable.
- Mechanical part drawings must establish dimension datums first, then dimension overall sizes, locating dimensions, and hole/slot specifications. Never treat a feature callout as a locating dimension.
- Cutout/slot features must provide "size + location + quantity": e.g., display openings need diameter/size and center distance to datum edges; screw holes need diameter and center-to-center spacing; port cutouts need width, height, and center elevation; spigots/gates need hole diameter, lateral position, and both center heights.
- For dense holes or slots, prefer a hole table, slot table, or hole/slot schedule; every table entry must tie back to datum dimensions in the views rather than merely stating "see drawing" or quantity only.
- Leaders are for brief callouts only, never substitutes for critical dimensions. Leaders must not cross other views, holes, centerlines, dimension text, or the title block.

## Mechanical Drafting Convention Checklist (TCVN/ISO Default; GB/T Reference Only)

By default (including when the user requests strict standards or standard mechanical drawings), load `references/tcvn_mechanical.md` (from the root skill directory) and follow the **TCVN/ISO** baseline (`ISO` drafting standard, `MMGS`, First-Angle projection). Treat `GB/T`, `GB`, and `JB/T` conventions below as **reference only** unless the user explicitly requests Chinese mechanical drafting / GB/T style:

- Sheet size and border: Under TCVN/ISO (`TCVN 7285:2003` / `ISO 5457`), A3 landscape (`420×297`) uses a `20 mm` left binding margin and `10 mm` top/bottom/right margins with a lower-right title block (max width `180 mm`). (GB/T reference only, when explicitly requested: left margin `25`, other margins `5`.)
- Fonts and text: Under TCVN/ISO, use Unicode-safe technical fonts (`ISOCPEUR`, `Arial`, or company template font); prefer FangSong (仿宋) only when Chinese GB/T text is explicitly requested. Do not mix arbitrary fonts across technical notes, title block, view labels, and hole/slot tables.
- Layers and linetypes: Separate thick solid lines, thin solid lines, centerlines, hidden lines, dimensions, text, borders, and cutouts/sections onto distinct layers; centerlines and hidden lines must not be drawn as plain continuous lines.
- Dimension entities: Linear dimensions must use real AutoCAD dimension entities such as `AcDbRotatedDimension`; do not fake dimensions with plain lines and text.
- Cutout deliverables: 3D-printed enclosures must clearly specify overall dimensions, wall/base thickness, screen cutout, port cutouts, spigots, ventilation slots, and screw hole/boss sizes and locations.
- Layout review: Dimension lines, text, and hole/slot tables must not intrude into the title block or collide with main view geometry; if space is tight, move views or split tables.

Typical anti-pattern postmortems:

- Writing only `4×screw boss φ8, pilot hole φ2.6` without boss center-to-center spacing and edge distances—unmachinable.
- Writing only `7×4×30 grille` without slot-array center, first-slot location, or pitch—cannot be positioned.
- Writing only `2×spigot through-hole φ13.5` without lateral location and both center heights—cannot be drilled/cut.
- Drawing a long leader across centerlines, hole outlines, or other views—looks like construction-line clutter and must be reworked into a dimension chain or hole/slot table.

## Automation Coding Practices

- Centralize dimensional parameters at the top of the script or in the JSON brief.
- Validate return objects after every COM call; check file existence and size after saving/exporting.
- Prefer object model methods for creating entities; reserve `SendCommand` for missing object model APIs, invoking existing commands, or legacy compatibility.
- `SendCommand` can execute asynchronously; wait, save, and verify afterward instead of assuming success once the command is sent.
- `SelectionSet` names persist inside the drawing; delete any existing set with the same name before creating one.
- During batch processing, never let one corrupt drawing abort the entire run; log the failed file and stage.

## Review Strategy

Minimum checks:

- File written to disk with reasonable file size.
- Entity count and types match the brief.
- Layers contain the expected objects.
- Global bounding box matches the expected order of magnitude.
- Primary geometry is visible in AutoCAD after `ZoomExtents`.

High-risk checks:

- Missing text, block attributes, Xrefs, linetypes, or fonts.
- Consistency between DXF/PDF exports and the source DWG.
- Correct border scale, plotter, CTB/STB plot style table, page orientation, and margins.
- Confirm batch edits did not overwrite original user drawings.

## Engineering Judgment

- Prioritize reproducibility before visual polish in drawing automation; visual refinement comes after functional correctness.
- A DWG is a rich database, not a flat raster image; screenshots alone cannot prove attributes, layers, or block references are correct.
- Use .NET for complex plugin development rather than cramming hundreds of lines of business logic into `SendCommand` strings.
- Major AutoCAD version upgrades affect the .NET target framework, ObjectARX SDK, and plugin loading; always verify on each major release.
- AutoCAD LT, educational editions, network licenses, or headless sessions may restrict automation capabilities; verify the environment first when exceptions occur.
