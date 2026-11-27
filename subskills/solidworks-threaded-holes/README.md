# SolidWorks Threaded Holes

`solidworks-threaded-holes` is the ISO metric internal threaded-hole subskill of `solidworks-automation`. Rather than merely generating geometry that "looks like a hole", it validates tap-drill diameters, end conditions, thread depths, and hole-position margins, and reads back the FeatureManager Design Tree after rebuild.

## Current Capabilities

- M3/M4/M5/M6/M8/M10/M12 coarse-pitch ISO metric internal threads.
- Non-table ISO metric sizes: require an explicitly supplied tap-drill diameter rather than automatic guessing.
- Blind holes and true `Through All` through-holes.
- Three-tier fallback: genuine `Metric Tap` `Thread`, `CosmeticThread`, and an exact-pitch 3D evidence helix.
- Right-hand/left-hand threads, thread tolerance class properties, hole-mouth Chamfers, STEP export, multi-view previews, and structured review evidence.

Live-verified on SolidWorks 2026 for both M6×1 6H right-hand blind and through-holes, both confirming genuine `Thread` features after rebuild and passing delivery review.

## Quick Start

```powershell
python scripts\sw_preflight.py

python subskills\solidworks-threaded-holes\scripts\create_threaded_hole_template.py `
  --thread M6 `
  --output-dir C:\CADAutomationWorkbench\solidworks_threaded_hole_output
```

Through-hole and left-hand example:

```powershell
python subskills\solidworks-threaded-holes\scripts\create_threaded_hole_template.py `
  --thread M8x1 `
  --tap-drill 7.0 `
  --through `
  --handedness left `
  --thread-class 6H `
  --output-dir C:\CADAutomationWorkbench\m8x1_lh_output
```

## Delivery Evidence

Outputs `SLDPRT + STEP + parameters.json + review_report.json + isometric/orthographic views` by default. If neither a real `Thread` nor a `CosmeticThread` persists in the FeatureManager tree, an isolated `*_thread_evidence.bmp` is also generated; the 3D helix Sketch is then hidden so it does not pollute standard previews.

## Capabilities Not Yet Claimed Stable

Hole Wizard / Advanced Hole, modifying existing parts, external threads, UNC/UNF/NPT/BSP, multi-start threads, drill-point angles and thread relief undercuts, and automated Engineering Drawing hole-callout acceptance are planned extensions—see [threaded-hole-roadmap.md](references/threaded-hole-roadmap.md).

## Directory Structure

```text
solidworks-threaded-holes/
├── SKILL.md
├── README.md
├── manifest.yaml
├── agents/
├── references/
│   ├── threaded-hole-lessons.md
│   └── threaded-hole-roadmap.md
└── scripts/
    └── create_threaded_hole_template.py
```
