# SolidWorks VibeCAD

`solidworks-vibecad` is the parametric design planning subskill in the `solidworks-automation` repository, built to turn natural-language mechanical design requirements into structured design plans, manufacturing-rule checks, SolidWorks API execution outlines, and review gates.

## Why Keep It as a Subskill

The value of this direction lies not in generating one-off macros, but in distilling repetitive mechanical design work into reusable engineering assets:

```text
行业知识库 + 参数 schema + 提示词模板 + 稳定 API 封装 + 自动审查
```

Therefore, it belongs inside the main SolidWorks automation repository alongside CNC Fillet/Chamfer, threaded holes, Assemblies, and MCP capabilities.

## Current Capabilities

- Generates parametric design-plan JSON from natural-language requirements.
- Built-in rules for M3–M12 tap-drill diameters, clearance holes, CNC Fillets/Chamfers, and minimum wall thickness.
- Provides a strict planning prompt for LLMs so they avoid emitting fragile macros directly.
- Generates SolidWorks API execution outlines mapping each step to the parent skill's stable wrappers.
- Generates review gates requiring save, export, multi-view previews, and a review report.

## Directory Structure

```text
solidworks-vibecad/
├── SKILL.md
├── README.md
├── manifest.yaml
├── knowledge/
│   └── manufacturing_rules.yaml
├── prompts/
│   └── solidworks_parametric_planner.md
├── schemas/
│   └── design_plan.schema.json
├── scripts/
│   ├── plan_from_brief.py
│   └── sw_execution_outline.py
├── examples/
│   ├── motor_mount_brief.txt
│   ├── motor_mount_plan.json
│   └── motor_mount_execution.md
└── references/
    └── vibecad-roadmap.md
```

## Quick Run

Run from the `solidworks-automation` repository root:

```powershell
py subskills\solidworks-vibecad\scripts\plan_from_brief.py `
  --brief-file subskills\solidworks-vibecad\examples\motor_mount_brief.txt `
  --out subskills\solidworks-vibecad\examples\motor_mount_plan.json

py subskills\solidworks-vibecad\scripts\sw_execution_outline.py `
  --plan subskills\solidworks-vibecad\examples\motor_mount_plan.json `
  --out subskills\solidworks-vibecad\examples\motor_mount_execution.md
```

## Example Output

The sample brief extracts:

- Baseplate: `90 x 60 x 8 mm`
- Mounting holes: `M5` screw clearance holes, diameter `5.5 mm`
- Center bore: `22 mm`
- Outer-contour Fillet: `R6`
- Top-edge Chamfer: `C1`
- Review: `SLDPRT + STEP + parameters_json + review_report_json + isometric_preview`

## Next Steps

Prioritize wiring the `cnc_mount` executor into the parent skill:

1. Read `design_plan.json`.
2. Call `sw_preflight.py`.
3. Create a new Part with `SolidWorksSession()`.
4. Create the baseplate, holes, pockets, Fillets, and Chamfers per the plan.
5. Save `SLDPRT` and export `STEP`.
6. Run `sw_review.run_review()`.
7. On failure, degrade and retry according to `risk_register` in the plan.
