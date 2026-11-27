---
name: solidworks-vibecad
description: SolidWorks VibeCAD parametric design planning subskill. Converts natural-language mechanical design requirements into structured design plans, manufacturing-rule checks, SolidWorks API execution outlines, and review gates; use for text-to-CAD, codifying vibecoding workflows, domain knowledge bases, prompt templates, parametric modeling plans, and batch generation of CNC mounts, connector blocks, and brackets.
---

# SolidWorks VibeCAD

## Core Positioning

This subskill turns natural-language design ideas into executable, reviewable SolidWorks parametric design plans. Rather than generating throwaway VBA macros, it codifies repetitive mechanical design into:

```text
行业知识库 + 参数 schema + 提示词模板 + 稳定 API 封装 + 自动审查
```

The LLM interprets intent and fills in parameters; SolidWorks APIs handle deterministic execution; the knowledge base enforces engineering soundness; and the review pipeline prevents "looks successful but geometrically wrong" deliverables.

## Applicable Tasks

- Users describe a part in natural language and want a parametric modeling plan.
- Standardizing high-frequency mechanical parts such as CNC mounts, connector blocks, L-brackets, baseplates, and hole patterns.
- Capturing domain knowledge such as tap-drill diameters, clearance holes, counterbores, Chamfers, Fillets, and minimum wall thicknesses.
- Supplying JSON plans and risk gates to a SolidWorks automation executor.
- Turning successful cases into reusable templates instead of rewriting macros from scratch each time.

## Workflow

1. Read user requirements and confirm part family, manufacturing process, material, output formats, and constraints.
2. Consult `knowledge/manufacturing_rules.yaml` to fill in conservative defaults.
3. Use `prompts/solidworks_parametric_planner.md` to constrain the LLM to emit a structured plan.
4. Validate plan fields against `schemas/design_plan.schema.json`.
5. Run `scripts/plan_from_brief.py` to generate a local rule-based plan, or save LLM output as JSON matching the same schema.
6. Run `scripts/sw_execution_outline.py` to generate the SolidWorks execution outline.
7. Hand off actual execution to the parent skill's `scripts/sw_session.py`, `scripts/sw_part.py`, `scripts/sw_review.py`, and relevant specialized subskills.

## Quick Commands

```powershell
py subskills\solidworks-vibecad\scripts\plan_from_brief.py `
  --brief-file subskills\solidworks-vibecad\examples\motor_mount_brief.txt `
  --out subskills\solidworks-vibecad\examples\motor_mount_plan.json

py subskills\solidworks-vibecad\scripts\sw_execution_outline.py `
  --plan subskills\solidworks-vibecad\examples\motor_mount_plan.json `
  --out subskills\solidworks-vibecad\examples\motor_mount_execution.md
```

## Relationship to the Parent Skill

- `solidworks-automation`: main skill for SolidWorks connection, modeling, export, and review.
- `solidworks-vibecad`: natural language -> parametric design plan.
- `solidworks-fillet-chamfer-cnc`: complex CNC Fillet/Chamfer execution experience.
- `solidworks-threaded-holes`: threaded holes, tap-drill holes, and thread-representation execution experience.

When the plan involves CNC parts with dense Fillets/Chamfers, continue by reading:

```text
subskills/solidworks-fillet-chamfer-cnc/SKILL.md
```

When the plan involves M3/M4/M5/M6/M8 threaded holes, continue by reading:

```text
subskills/solidworks-threaded-holes/SKILL.md
```

## Pitfalls to Avoid

- Do not have the LLM directly output long-parameter SolidWorks COM calls.
- Never equate a valid plan JSON with geometric success; always run real SolidWorks execution and `sw_review` verification.
- Uncertain parameters may use conservative defaults, but must be recorded in `assumptions`.
- Distinguish clearance holes, counterbores, and tapped holes for screw mounting features; never default an "M5 screw mounting hole" to an M5 tapped hole by mistake.
- Output plans must include `review_plan`; otherwise they cannot enter automated modeling.

## Current Status

The current phase implements the minimal closed loop from requirement text to design plan and execution outline. The live SolidWorks executor should be wired to the parent skill's stable APIs in the next phase.
