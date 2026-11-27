# Controlling SolidWorks with OpenClaw

This guide targets agent instances invoking this skill, aiming to reliably reuse the existing `scripts/` wrappers inside OpenClaw rather than rewriting COM automation code from scratch on every run.

## Pre-Run Checks

1. Operating system must be Windows.
2. SolidWorks must be installed, and ideally launched manually at least once to confirm COM availability; if SolidWorks is not detected, stop immediately and instruct the user to install SolidWorks manually.
3. `python` or `py` must be executable on `PATH`.
4. `pywin32` / `comtypes` must be installed. Run the preflight check first:

```bash
python {baseDir}/scripts/sw_preflight.py
```

Preflight rules:

- If `comtypes` / `win32com` / `pythoncom` is missing, prompt the user first: `The current Python environment is missing comtypes / win32com libraries. Authorize the AI to automatically configure the local environment? [Y/N]`
- Only after user confirmation, execute `python -m pip install "pywin32>=305" "comtypes>=1.2.0"`.
- If the user declines, stop and provide the manual installation command.

5. This skill resides in either of the following directories:

```text
~/.openclaw/skills/solidworks-automation/
~/.agents/skills/solidworks-automation/
```

## Recommended Execution Workflow

1. Gather missing constraints first: SolidWorks version, UI language, intermediate file paths, final output paths, dimensional units, and target formats.
2. Run `sw_preflight.py` first, then prefer calling `scripts/sw_connect.py`, `scripts/sw_part.py`, `scripts/sw_assembly.py`, `scripts/sw_drawing.py`, and `scripts/sw_export.py`.
3. If an LLM must generate a VBA macro, always route it through `scripts/sw_macro_guard.py` for model-specific prompting, output validation, retries, and template fallback.
4. Break tasks into small steps: connect, open/new, model/assemble, save, export, and screenshot/preview self-review.
5. Check return values at every step; never assume a COM call succeeded.
6. After saving or exporting, verify that the target file actually exists on disk.
7. After creating or modifying a model, export at least one isometric preview image; if desktop screenshot capability is available, also capture the active SolidWorks window for verification.

## Minimal Import Template

When executing Python inside OpenClaw, use `{baseDir}` to reference the skill root directory:

```python
import sys
sys.path.insert(0, r"{baseDir}/scripts")

from sw_connect import connect_solidworks, mm, deg, new_document, open_document, save_document
from sw_preflight import run_preflight
from sw_part import start_sketch, end_sketch, sketch_rectangle, sketch_circle, extrude_boss, extrude_cut
from sw_export import export_to_step, export_to_stl, export_to_pdf
from sw_review import run_review

run_preflight()
```

## Multi-Model VBA Macro Guard

When invoking GPT / Kimi / Claude to generate VBA macros, never feed raw model output directly to SolidWorks. Use `sw_macro_guard.py`:

```python
from sw_macro_guard import build_prompt, generate_macro_with_guard, validate_vba_macro

prompt = build_prompt("画一个 50mm 圆柱", model_name="kimi")
```

Execution conventions:

1. GPT-series models use concise prompts.
2. Kimi / Claude / unknown models automatically use strict format-constrained prompts.
3. Macros must pass `validate_vba_macro()` before execution, checking for `SldWorks`, `ModelDoc2`, `Sub`, and `End Sub`.
4. Parse failures automatically retry `1–2` times with stricter formatting instructions appended.
5. If retries still fail, fall back to local templates matched by keywords such as box / cylinder / extrude / sketch (`"立方体"` / `"圆柱"` / `"拉伸"` / `"草图"`).

## Recommended Prompts

User requests suited to directly triggering this skill in OpenClaw:

- "Model a 120x80x10 mm mounting plate in SolidWorks with four Ø6 holes at the corners, save to `C:\\temp\\plate.sldprt`, and export STEP."
- "Open `C:\\parts\\gearbox.sldasm`, run interference detection, and report the results."
- "Export `C:\\parts\\bracket.sldprt` to STL and STEP in `C:\\output\\`."

## Execution Notes

- `SolidWorks API` uses meters for lengths; always convert millimeter inputs with `mm()`.
- `start_sketch()` has built-in English/Chinese reference plane fallbacks; pass `"Front Plane"`, `"Top Plane"`, `"Right Plane"`, or their Chinese equivalents directly.
- Before operating on features, faces, or edges, confirm exact entity names and types prior to calling `SelectByID2`.
- For large tasks, save native `.sldprt` / `.sldasm` / `.slddrw` files first and treat format exports as the final step.

## Self-Check Checklist

After execution completes, verify at least:

1. `connect_solidworks()` returned a valid `sw` object.
2. After creating or opening a document, `model` is not `None`.
3. Feature calls (e.g., `extrude_boss()`) returned valid feature objects.
4. `save_document()` / export calls returned success.
5. Target files actually exist on disk.
6. `run_review()` successfully exported preview images and wrote `*_review_report.json`.
7. The model in preview images matches the task specification without blank frames, wrong scale, missing components, inverted orientation, overlaps, or floating parts.

## Self-Review Example

```python
model.ForceRebuild3(False)
report, report_path = run_review(model, r"C:\temp\review", basename="result")
print(report_path)
print(report["evaluation"])
```

If preview images show defects, fix the script and regenerate—never simply report "file saved successfully."
