# SolidWorks Engineering Drawing

Engineering Drawing generation and manufacturing-delivery review subskill. It can be invoked on demand by the root `solidworks-automation` skill, VibeCAD, hole/slot/CNC subskills, or an engineering orchestrator, without requiring other modeling subskills to reverse-depend on it.

## Live-Machine Case Study

<p align="center">
  <img src="../../assets/showcase/solidworks-engineering-drawing-demo.gif" alt="solidworks-engineering-drawing complex test artifact live case" width="900">
</p>

In this case study, SolidWorks 2026 SP01.1 reads the public-domain NIST Additive Manufacturing Test Artifact Ver3B, verifies the model bounding box first, and then generates a GB/T first-angle A1 Drawing. The actual deliverable includes:

- Native `SLDPRT` and `SLDDRW` files
- Three orthographic views, an isometric view, and Section View A-A
- 10 required dimensions along with hole-location and datum requirements
- PDF, BMP preview, `drawing_evidence.json`, and `drawing_review_report.json`
- 70 targeted drawing tests currently passing, with 0 overlapping extractable PDF text bounding boxes in the experimental artifacts

This case study demonstrates the end-to-end "code-driven SolidWorks → native Drawing → structured evidence" pipeline and does not represent unattended manufacturing release; final drawing borders, dimension chains, hole tables, and manufacturing semantics still require visual review by an engineer.

## Inputs

Described using `schemas/drawing_spec.schema.json`:

- Source `.sldprt` / `.sldasm` / sheet-metal model
- TCVN/ISO drafting standard by default (see `references/tcvn_mechanical.md` in the root skill directory; `GB/T` is reference only unless explicitly requested), sheet size, and projection method (First-Angle by default)
- Views, scale, section views, and detail views
- Required dimensions and hole/slot specifications, quantities, and locations
- Title block, technical notes, BOM, and delivery outputs

## Outputs

- `.slddrw`
- PDF
- BMP/PNG preview
- `drawing_evidence.json`
- `drawing_review_report.json`
- Markdown review summary

## Compatibility Entry Points

Writing native SW2026 datums and GD&T onto existing drawings uses the dedicated [drawing copy workflow](references/native-gdt.md), supporting exact geometric targets, 14 characteristic symbols, stacked/composite frames, and M/L/S datum modifiers, with save-and-reopen verification of persistent attachments.
For common datums, datum sub-groups, projected tolerance zones, profile offsets, CZ/SZ, unit zones, and maximum tolerances, see [extended GD&T inputs](references/gdt-extended-options.md).
The existing MCP tool `solidworks_generate_drawing` and `scripts/sw_drawing_package.py` also support automatically creating dimensions, basic dimensions, datums, and GD&T from structured single-part specs, followed by save-reopen and PDF/layout verification. The native path is limited to SW2026 and requires design tolerances plus exact geometric targets; free-text requirements are never guessed onto the drawing, results remain `pilot/review_required`, and visual review is mandatory.

Legacy callers can still import from the root path:

```python
from scripts.sw_drawing import plan_standard_view_layout
```

## Cross-Version Live-Machine Matrix

```powershell
$env:CAD_STUDIO_VISIBLE='false'
python tests/solidworks_drawing_version_matrix.py --years 2024 2025 2026
```

The matrix executes serially by exact version ProgID, outputting an independent drawing report per version and an aggregated matrix JSON. Unregistered versions are recorded as `unavailable`; a version is marked `pass` only when the read-back year matches the requested year.

New code should prefer this subskill's scripts and execute through the COM/session APIs provided by the root skill.

## Status

Currently `pilot`. On delivery, COM dimension locations are strictly correlated one-to-one against actual vector text bounding boxes in the SolidWorks-exported PDF; `pass` may be returned only when correlation is complete with zero collisions. Missing PDFs, missing PyMuPDF, incomplete matching, or detected overlaps block release.
