---
name: solidworks-engineering-drawing
description: "SolidWorks Engineering Drawing generation and manufacturing-delivery review subskill supporting GB/T first-angle Part Drawings, Assembly Drawings, dimension chains, hole tables, BOMs, PDF/BMP evidence, and sheet-metal capability gates."
metadata: { "openclaw": { "os": ["win32"], "requires": { "anyBins": ["python", "py"] } } }
---

# SolidWorks Engineering Drawing Generation & Review

This subskill focuses on 2D Engineering Drawings. It depends on the root `solidworks-automation` skill for SolidWorks COM sessions, models, exports, and general geometric evidence, while owning `DrawingSpec v1`, the drawing generation workflow, and manufacturing-delivery review.

## When to Invoke

- Generating Part Drawings or Assembly Drawings.
- Requiring GB/T sheet formats, first-angle projection, dimension chains, hole tables, BOMs, or title blocks.
- Checking drawing view overlaps, dimension text, PDF text, title-block intrusion, or delivery evidence.
- Reviewing flat-pattern evidence for sheet-metal tasks.

## Default Rules

- `standard=GB_T` defaults to `projection=first_angle`.
- GB/T combined with third-angle projection is blocked by `DrawingSpec` preflight validation.
- Whenever the user requests TCVN or Vietnamese mechanical standards (drawings, limits/fits, GD&T, surface roughness, or welding), load `references/tcvn_mechanical.md` (from the root skill directory) and apply its ISO-harmonized, MMGS, First-Angle baseline.
- Every hole, slot, and port must include specification, quantity, and locating information.
- Drawing delivery must export a PDF and correlate every COM dimension location one-to-one with vector text bounding boxes in the final PDF; missing PDFs, missing parsers, incomplete correlation, or text collisions block release or trigger mandatory review.
- This subskill does not implement reinforcement learning and never exposes arbitrary Python/VBA execution entry points.

## Workflow

1. Read and validate `schemas/drawing_spec.schema.json`.
2. Run the root skill's SolidWorks preflight and capability probe.
3. Select the sheet format, create the drawing sheet, and read back sheet size and projection method.
4. Create views, dimensions, hole tables, and BOMs according to executor capabilities, and read back real entities; never silently ignore `DrawingSpec` fields.
5. Save `.slddrw`, and export PDF and BMP/PNG.
6. Run `drawing_review.py` to generate machine evidence and manual review gates.

## Capability Boundaries

- Part and Assembly Drawings are in `pilot`: cross-version live-machine regressions are ongoing; however, when PDF dimension text boxes, view bounds, dimension chains, hole tables, and BOM evidence all pass, the tool returns `pass` instead of unconditionally downgrading due to missing native COM text boxes.
- The generic MCP generator supports `front`/`top`/`right` standard orthographic views with explicit placement, fitting scale, model dimension import or structured native dimensions, datums/GD&T, notes, and templated BOMs. Native dimensions/GD&T are restricted to SW2026 single parts; isometric, section, detail views, hole tables, thread callouts, business title-block fields, and sheet-metal-specific options still return `DRAWING_SPEC_CAPABILITY_UNSUPPORTED` prior to modification and are handled by specialized scripts.
- The reviewer performs structured verification by dimension ID/view/kind/value, hole size/quantity/location, genuine BOM type/data rows/configuration, and title-block field readback; template candidates, arbitrary tables, or fuzzy substrings do not count as pass evidence.
- `professionalAnnotations` can declare center marks, centerlines, hole callouts, datums, GD&T, surface finish symbols, and weld symbols. The reviewer accepts only readback from dedicated SolidWorks annotation entities; plain `Note` text cannot substitute.
- For SW2026 native GD&T, see [`references/native-gdt.md`](references/native-gdt.md): existing single-sheet, single-part A3 millimeter drawings can be annotated into a new copy; automated drawing generation from a part uses the existing `solidworks_generate_drawing` or `scripts/sw_drawing_package.py`, supporting A4..A0, structured dimensions/basic dimensions, datums, 14 symbols, stacked/composite frames, and datum M/L/S modifiers. Confirm geometric targets, design tolerances, and placement before execution; after save-and-reopen, verify persistent IDs, full-layer XML, actual entity types/attachments, styles, and positions, export PDF/BMP, and verify source and dependency hashes. Results remain `review_required` and require visual inspection rather than substituting for tolerance design; free-text GD&T is never guessed onto drawings, and assembly native annotations plus unimplemented professional fields remain blocked.
- For common datums/datum sub-groups, projected tolerance zones, unequal/offset profiles, CZ/SZ, unit zones/maximum tolerances, reciprocity, and other frame modifiers, read [`references/gdt-extended-options.md`](references/gdt-extended-options.md). Each member must be declared individually rather than treating `A-B` as a single letter datum; use structured `options` and never pass arbitrary XML. All extended semantics participate in save-reopen and native review; any missing or dropped option blocks release.
- The generic generator now supports automated `centerMarks` insertion: each entry must declare `id`, standard view, expected total count, and `targets` (`holes`/`fillets`/`slots`), verified via `GetFirstCenterMark2`/`GetNext` entity readback. Live SW2026 testing confirmed that newly created drawings must be saved once before inserting center marks; in an unsaved state, the API may return `True` while entities remain unreadable, so the wrapper treats that as a failure. Unimplemented professional annotations such as centerlines, surface finish, and weld symbols remain capability-blocked.
- Cross-version live-machine matrix uses `python tests/solidworks_drawing_version_matrix.py --years 2024 2025 2026`. The script launches only registered exact-version ProgIDs and verifies the actual read-back year; uninstalled versions are marked `unavailable` and must never be substituted with default ProgID results.
- Sheet-metal drawings proceed only when reliable local flat-pattern evidence exists; missing evidence returns `blocked` and never claims unattended completion.
- Full GD&T semantic solving is outside the scope of this release; only requirement presence and traceability are verified.

## Root Skill Dependencies

Prefer reusing: `scripts/sw_connect.py`, `scripts/sw_session.py`, `scripts/sw_export.py`, `scripts/sw_review.py`, `scripts/sw_document_data.py`, and `scripts/sw_capability_probe.py`.
