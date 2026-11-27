---
name: solidworks-automation
description: "SolidWorks CAD automation skill prioritizing verified parts, holes and slots, assemblies, engineering drawings, exports, and delivery review; all capability tiers are governed by capabilities.yaml, and unverified capabilities require manual review."
metadata: { "openclaw": { "homepage": "https://github.com/wzyn20051216/solidworks-automation-skill", "os": ["win32"], "requires": { "anyBins": ["python", "py"] } } }
---

# SolidWorks Automation Skill

## Engineering Standards Priority (Mandatory Override)

- **Default Standard**: Default strictly to **TCVN (Vietnamese Mechanical Standards)** and **ISO** (`ISO` drafting standard, `MMGS` units, **First-Angle Projection**).
- **Mandatory Reference Loading**: Always load `references/tcvn_mechanical.md` before creating, configuring, or checking any 2D drawing, limit/fit, GD&T, surface roughness, or weldment.
- **GB/T, GB & JB/T Reference Only**: Treat all `GB/T`, `GB`, and `JB/T` standards in this repo as **reference only** unless explicitly requested by the user.
- **No Fabricated TCVN Codes**: Never guess or invent undocumented TCVN codes; fall back to the harmonized `ISO` equivalent and flag it for user verification.

## Live Inspection & SolidWorks 2024 Defaults (Mandatory Override)

- **Target SolidWorks 2024**: Default interactive desktop automation to **SolidWorks 2024** (`version=2024`, ProgID `SldWorks.Application.32`) unless the user explicitly specifies another version.
- **Visible & User-Controlled Window**: Always make SolidWorks 2024 visible on screen by setting `swApp.Visible = True` and `swApp.UserControl = True` (enforced automatically by `SolidWorksSession(version=2024)` / `connect_solidworks(..., visible=True, user_control=True, ensure_visible=True)` / `ensure_visible_user_control(sw)`).
- **Keep Document Open After Saving**: Always keep the created or modified document open in SolidWorks after saving (`keep_open=True` default in `SolidWorksSession`); do **not** call `CloseDoc` or exit SolidWorks unless the user explicitly requests automated cleanup (`keep_open=False`).
- **Zoom to Fit for Live Inspection**: Always call `model.ViewZoomtofit2()` (enforced automatically by `save_document(..., zoom_to_fit=True)` and `SolidWorksSession`) after saving and before finishing so the user can inspect the model live.

## Quick Start

### Environment Requirements

- Windows OS; local interactive CAD automation targets **SolidWorks 2024** (`version=2024`, visible live inspection by default) while maintaining SolidWorks 2026 compatibility; headless open-format writing does not require CAD software installation
- Python 3.10+; native Windows CAD automation also requires `pywin32` / `comtypes`
- MCP / tool-based invocation requires `mcp` / `pydantic`
- Final engineering drawing delivery review requires `PyMuPDF`; it reads back actual dimension text bounding boxes from SolidWorks-exported PDFs and is included in `requirements.txt`
- When working with GLB/GLTF/OBJ/STL mesh reference models, `trimesh` / `pygltflib` / `numpy` / `Pillow` may also be required
- If using via OpenClaw, ensure the skill directory is located at `~/.openclaw/skills/solidworks-automation/` or `~/.agents/skills/solidworks-automation/`

### Entry Preflight Check

Before executing SolidWorks automation, all agents must first run the skill preflight check:

```bash
python SKILL_DIR/scripts/sw_preflight.py
```

Before desktop or CLI execution, it is recommended to run environment diagnostics first:

```powershell
python SKILL_DIR/scripts/cad_studio.py doctor
```

`capabilities.yaml` is the single source of truth for capabilities shared by Skill, MCP, queues, and UI. Capability tiers are `verified`, `pilot`, `reference_only`, or `not_implemented`; the latter two must not be used for unattended delivery. This registry also maintains atomic operation routing across Python, C# PIA/Add-in, native C++, SWBasic, OCCT, and external solvers; query before execution with `python scripts/backend_router.py --list`, and see `references/language-backend-routing.md` for routing rules.

### Multi-Entry & Multi-Backend Architecture

- CAD Studio and Skill/CLI/MCP are peer entry points sharing Automation Job, NeutralCadDocument, Preview Manifest, Evidence Graph, and the capability registry.
- When SolidWorks/AutoCAD is not detected, only native formats such as `SLDPRT/SLDASM/SLDDRW/DWG` are blocked; open-format tasks are routed to `headless_open_format_writing` first.
- For design rule checks or lead-screw/belt motor torque preliminary sizing, read `references/design-rule-check.md` and `references/drive-sizing.md`, using user-provided or verified captured neutral documents as input; missing evidence is flagged as `review_required`, and results must be reviewed by an engineer.
- To identify hole locations on a drilling panel or plan drawing candidates, read `subskills/solidworks-engineering-drawing/references/drilling-panel-gdt.md`; hole types, datums, and tolerances must not be guessed from geometry, and candidate specifications must not masquerade as verified engineering drawings.
- When the user requests automated placement of datums, composite feature control frames, or GD&T on drawings, read `subskills/solidworks-engineering-drawing/references/native-gdt.md`. For existing drawings, first inspect targets with `scripts/sw_gdt_copy.py --source 图纸.slddrw --inspect`, then write to a new copy; for generating new drawings from a model, use the existing MCP `solidworks_generate_drawing` or `scripts/sw_drawing_package.py` and supply structured dimensions, basic dimensions, datums, and single/composite frame requirements. Save and reopen in SW2026 to verify native associativity, all tiers, and datum material modifiers; keep source files intact, and visually review the output; do not guess placement for legacy free text.
- For common datums, datum targets/sub-groups, projected tolerance zones, unequally disposed profile zones, CZ/SZ, limited area/length, and other extended GD&T options, continue reading `subskills/solidworks-engineering-drawing/references/gdt-extended-options.md`, and submit structured members and `options` through the same tool; every member must be verified, and after writing, save and reopen to validate all new semantics.
- To extract displayed dimension tolerances from a saved model, use `scripts/sw_tolerance_extract.py`; it reads only the active configuration and does not cover hidden dimensions or other configurations; angular, assembly, and drawing extraction still require verification.
- For batch renaming by custom properties, first generate a read-only preview with `scripts/sw_file_rename.py`; constrained standalone parts can use `scripts/sw_rename_copy.py`, and single-configuration nested assemblies can use `scripts/sw_assembly_rename.py` to create copies in a new directory and reopen for verification. Source files and external where-used references are untouched; drawings, Toolbox components, multi-configuration files, and other unverified references remain blocked. See `references/rename-preview.md` for details.
- For sprocket visual or geometric demonstrations, read `references/sprocket.md` and use `scripts/sw_sprocket.py` to create an approximate solid body in a new empty part; this model is not verified for chain meshing or manufacturing requirements and must not be used as a production-grade standard sprocket.
- For open-end constant-pitch round-wire helical spring solids, read `references/spring.md` and use `scripts/sw_spring.py`; the input height is the axial travel of the helix centerline rather than the solid free height, and material, end conditions, and engineering performance must be reviewed.
- Headless writing uses `scripts/headless_cad_writer.py`; an isolated OCCT/OCP process writes actual STEP, IGES, BREP, STL, OBJ, and GLB files, while the 2D backend writes DXF, SVG, PDF, and PNG, generating geometry and SHA-256 evidence.
- DXF delivery additionally generates a `preview_scene`; existing DXF files can be converted into a constrained PreviewScene via `python scripts/cad_studio.py preview-dxf --input drawing.dxf --output drawing.scene.json` or MCP `cadstudio_build_dxf_preview_scene`. This command reads only allowlisted entities and refuses to overwrite existing files.
- OCCT currently covers box, cylinder, Boolean union, cylindrical hole Cut, ruled/constrained smooth Loft, line/single-arc Sweep, closed-shell Knit, and open-surface Thicken; complex paths, self-intersecting offsets, or missing OCP runtime remain `blocked`. Faking support via file extension renaming or empty files is prohibited.
- `delivery-preview` is only allowed to display real artifacts from the current task; static samples must be tagged `demo-showcase` with `isDemo: true` and must never enter delivery evaluation.

Rules:

1. When missing `comtypes` / `win32com` / `pythoncom` is detected, run `python -m pip install "pywin32>=305" "comtypes>=1.2.0"` by default to install dependencies; if installation fails, report the reason and manual steps.
2. Set environment variable `SW_AUTO_INSTALL_DEPENDENCIES=off` or run `sw_preflight.py --no-install` to disable automatic installation.
3. When no SolidWorks installation or COM registration is detected, stop native SolidWorks operations; if native formats are not required and `fallbackPolicy=allow_open_formats`, proceed with the headless open-format backend instead of falsely marking the entire task as failed.

### Python Dependency Notes

Install minimal dependencies per task—do not force-install mesh conversion libraries for standard part modeling; engineering drawing delivery requires PyMuPDF from standard `requirements.txt`:

```powershell
# 核心 SolidWorks COM 自动化依赖
python -m pip install -r SKILL_DIR\requirements.txt

# 仅在需要 GLB/GLTF/OBJ/STL 网格检查、缩放或转换时安装
python -m pip install -r SKILL_DIR\requirements-mesh.txt
```

Before running tasks that convert GLB/GLTF/FBX/BLEND to OBJ/STL, use `importlib.util.find_spec()` to check whether
`trimesh`, `pygltflib`, and `PIL` are available; if missing, inform the user which libraries are needed and why before installing or providing manual commands.

### Connecting to SolidWorks

```python
import sys; sys.path.insert(0, r"SKILL_DIR/scripts")
from sw_connect import mm
from sw_part import sketch, sketch_circle, extrude_boss
from sw_sketch_quality import fully_define_sketch
from sw_session import SolidWorksSession

with SolidWorksSession(version=2024, visible=True, keep_open=True, zoom_to_fit=True) as session:
    model = session.new_part()

    with sketch(model, "Front Plane") as sketch_name:
        sketch_circle(model, 0, 0, mm(25))
        fully_define_sketch(model)

    if extrude_boss(model, sketch_name, mm(50)) is None:
        raise RuntimeError("拉伸失败")
    if not session.save(model, r"C:\temp\cylinder.sldprt"):
        raise RuntimeError("保存失败")
    if not session.export(model, r"C:\temp\cylinder.step"):
        raise RuntimeError("导出失败")
    # SolidWorks 2024 stays visible (Visible=True, UserControl=True),
    # the document remains open after saving, and ViewZoomtofit2() frames it for live inspection.
```

> Replace `SKILL_DIR` with the actual installation path of this skill.

For model delivery, read back Sketch constraint states, dimensions, and relations—batch-applying Fix relations to substitute for design parameters is prohibited; after saving and reopening, verify that the Sketch is consumed by the target feature, key dimensions remain editable, and hole positions remain accurate. Basic circles/rectangles may use `fully_define_sketch()`; complex Sketches should explicitly specify design dimensions and relations and be verified with `inspect_model_sketches()`, retaining manual review when evidence is lacking.

By default (`keep_open=True`, `visible=True`, `zoom_to_fit=True`), `SolidWorksSession` keeps SolidWorks visible (`swApp.Visible = True`, `swApp.UserControl = True`), leaves the saved document open, and zooms to fit (`ViewZoomtofit2()`) for live inspection. Pass `keep_open=False` only when automated batch cleanup is explicitly desired—in cleanup mode, the session context closes only documents registered during the current run and confirmed-owned empty instances; when the document budget is reached, process the current run's files first. Do not claim task completion if execution flags failure, rebuild fails, check results are unknown, or manual review is incomplete. Remote MCP retrieves PNG or raw files via `artifact_refs` and verifies SHA-256 checksums; see `mcp-server/README.md` for rules.

## Core Workflows

Select the appropriate module based on user requirements:

| Requirement | Script | Reference |
|---|---|---|
| Entry preflight check & dependency installation | `scripts/sw_preflight.py` | `references/troubleshooting.md` |
| Headless open-format writing (no CAD) | `scripts/headless_cad_writer.py`, `scripts/cad_studio.py write-open-format` | `capabilities.yaml`, shared CAD Core Schema |
| Advanced capability / type library probing | `scripts/sw_capability_probe.py` | `references/complex-mechanical-routing.md` |
| Python/C#/C++/SWBasic/OCCT backend routing | `scripts/backend_router.py` | `references/language-backend-routing.md`, `capabilities.yaml` |
| C# in-process Add-in host, events & UI | `scripts/sw_addin_host.ps1`, `scripts/sw_addin_host.py` | `references/solidworks-addin-host.md` |
| Multi-model macro generation guard | `scripts/sw_macro_guard.py` | `references/openclaw.md` |
| Friendly session API | `scripts/sw_session.py` | - |
| Connection & document management | `scripts/sw_connect.py` | - |
| Appearance & materials | `scripts/sw_appearance.py` | `references/appearance.md` |
| Part modeling (Sketch + Features) | `scripts/sw_part.py` | `references/part-modeling.md` |
| Standard external spur gear solids | `scripts/sw_gear.py` | `references/gears.md` |
| Blind holes / Counterbore / Countersink / Straight slots & hole position verification | `scripts/sw_hole_features.py`, `scripts/sw_review.py` | `references/complex-hole-features.md`, `references/review.md` |
| Natural language to parametric design plan / VibeCAD | `subskills/solidworks-vibecad/scripts/plan_from_brief.py` | `subskills/solidworks-vibecad/SKILL.md`, `subskills/solidworks-vibecad/README.md` |
| Multi-Fillet / Chamfer CNC machined parts | `subskills/solidworks-fillet-chamfer-cnc/scripts/create_cnc_mount_template.py`; use `verify_advanced_fillets.py` for advanced Fillets | `subskills/solidworks-fillet-chamfer-cnc/SKILL.md`, `subskills/solidworks-fillet-chamfer-cnc/references/cnc-fillet-chamfer-lessons.md` |
| Tapped / threaded holes, tap drill holes | `subskills/solidworks-threaded-holes/scripts/create_threaded_hole_template.py` | `subskills/solidworks-threaded-holes/SKILL.md`, `subskills/solidworks-threaded-holes/references/threaded-hole-lessons.md` |
| AutoCAD DWG/DXF 2D drafting, line-art to CAD, batch drawing edits | `subskills/autocad-automation/scripts/acad_draw.py`, `subskills/autocad-automation/scripts/acad_review.py` | `subskills/autocad-automation/SKILL.md`, `subskills/autocad-automation/references/troubleshooting.md` |
| Assembly operations, gear linkage / hinge / draggable kinematic Mates | `scripts/sw_assembly.py` | `references/assembly.md` |
| Motion Study, rotary motors & result audit | `scripts/sw_motion.py` | `references/motion-study.md`, `references/complex-mechanical-routing.md` |
| Engineering drawing generation | `scripts/sw_drawing.py` | `references/drawing.md` |
| TCVN / Vietnamese mechanical standards (drawings, fits, GD&T, welding) | - | `references/tcvn_mechanical.md` |
| File export | `scripts/sw_export.py` | `references/export.md` |
| Configuration family creation/activation, parameter modification & custom properties | `scripts/sw_document_data.py` | `references/advanced.md` |
| Assembly BOM CSV & Pack and Go | `scripts/sw_delivery.py` | `references/export.md` |
| High-fidelity OBJ/STL mesh reference import | `scripts/sw_import_mesh_reference.py` | `references/mesh-reference-import.md` |
| Result self-review | `scripts/sw_review.py` | `references/review.md` |
| Semantic entity references | `scripts/sw_entity_reference.py` | Progressively replacing Face1/Edge1 and screen coordinates |
| DFM manufacturability risk review | `scripts/dfm_review.py`, `scripts/dfm_profiles.py`, `scripts/cad_studio.py check-dfm` | Supplier profiles, B-Rep evidence, declarative rule checks for machining, sheet metal, laser cutting, 3D printing, and injection molding |
| Neutral Routing review & preflight | `scripts/routing_review.py`, `scripts/cad_studio.py check-routing`, `scripts/cad_studio.py routing-preflight` | Endpoints, segments, lengths, bend radii, interference/clearance, supports, Routing BOM; native writing requires add-in/license evidence |
| FEA preflight, setup & constrained solving | `scripts/fea_analysis.py`, `scripts/fea_convergence.py`, `scripts/cad_studio.py fea-preflight/prepare-fea/run-fea/run-fea-convergence` | CalculiX 2.23 verified linear/nonlinear statics, plasticity, surface contact, final-step COPEN/CPRESS/CSLIP, and linear/nonlinear mesh convergence; all still require engineering review |
| Complex surfacing & tooling/molds | `scripts/advanced_geometry.py`, `scripts/advanced_geometry_ocp.py`, `scripts/advanced_surface_ocp.py`, `scripts/cad_studio.py review-advanced-geometry/create-ocp-loft/create-ocp-surface` | Ruled/smooth Loft and constrained Sweep/Knit/Thicken write and reopen B-Rep; G1/G2 continuity and radius of curvature return discrete sampling evidence only |
| Local MCP Server | `mcp-server/server.py` | `mcp-server/README.md`, `references/mcp-server.md` |
| MCP protocol validation | `scripts/validate_mcp.py` | `mcp-server/README.md` |
| Versioned API lookup | `scripts/sw_api_lookup.py` | `references/api-lookup.md` |
| OpenClaw SolidWorks control | - | `references/openclaw.md` |
| Sheet Metal / Weldments / Simulation / Properties | - | `references/advanced.md` |
| Enterprise Agent / Local-first & Cloud RAG | `apps/desktop/cad_workbench/knowledge_retrieval.py` | `references/enterprise-agent-rag.md` |
| Codex/Claude/Gemini/OpenCode Provider Adapter | `apps/desktop/cad_workbench/agent_providers.py` | `references/agent-provider-architecture.md` |
| Integrated mechanical engineering DAG orchestration | `apps/desktop/cad_workbench/engineering_orchestrator.py` | `references/complex-mechanical-routing.md` |
| Common error troubleshooting | - | `references/troubleshooting.md` |

Pack and Go passed native regression three consecutive times on SW2026 SP01.1 using a basic two-part assembly: `SavePackAndGo()` exported the assembly and both parts with status code 0 and without staging fallback. Some versions of `GetDocumentNames()` may still enumerate only the top-level file before saving; do not use `AddExternalDocuments` to patch native assembly components—perform native save first, then audit actual on-disk dependencies. If dependencies are still missing on disk, `scripts/sw_delivery.py::pack_and_go()` defaults to generating a `pilot` staged package with a manifest and SHA-256 checksums via `GetDependencies2`; use `fallback_policy="blocked"` when strict native semantics are required. External references, Toolbox parts, configurations, and engineering drawings still require manual review, so the overall capability remains `pilot`.

## OpenClaw Collaboration Workflow

1. First confirm the SolidWorks version, UI language, input file paths, output paths, and target operation (modeling / assembly / drawing / export).
2. Prefer reusing existing modules under `{baseDir}/scripts`; do not rewrite COM connection logic from scratch.
3. Run short, one-shot Python scripts via OpenClaw's `exec` / `shell` capability with the minimal import set below:

```python
import sys
sys.path.insert(0, r"{baseDir}/scripts")
from sw_connect import connect_solidworks, mm, deg, new_document
```

4. After execution, verify that returned objects are not `None`, save/export succeeded, and output files exist on disk.
5. After generating or modifying a model, perform a self-review: export at least one isometric preview image (plus front/top/right views when needed) and visually inspect the geometry via screenshots or BMPs to ensure it matches user intent.
6. For more complete OpenClaw workflows, prompt examples, and troubleshooting tips, read `references/openclaw.md`.

## Execution Workflow

1. First run `backend_router.py` based on the atomic operation, then evaluate `preferredBackend`, `requiredOutputs`, `nativeFormatRequired`, and `fallbackPolicy` to determine the backend; do not assume Python, C#, or SolidWorks is available. Prefer Automation-equivalent interfaces for general tasks, and escalate to native C++ only when unmanaged C++ raw `I*` pointer semantics are explicitly required.
   Event subscriptions, PropertyManagerPage, TaskPane, or persistent UI route through `solidworks_addin_ui_events`, preferring a C# Add-in; always verify HKLM registration, 64-bit TLB registration, and `host-status.json` rather than claiming success solely from `LoadAddIn=0`. SW2026 PMP Handlers must be public, COM-visible, and expose an `IDispatch` class interface.
2. Run `sw_preflight.py` when native SolidWorks formats are required; missing dependencies are auto-installed by default, and missing SolidWorks blocks only the native stage.
3. When native formats are not required or open-format fallback is allowed, run `python scripts/cad_studio.py write-open-format --input model.cadstudio.json --out-dir output`.
4. For rapid manufacturability review, run `python scripts/cad_studio.py check-dfm --input model.cadstudio.json --output output/dfm_report.json --process machining`; supports `--profile supplier.json` and `--brep-evidence brep.json`. Returns `blocked` if the report lacks material, wall thickness, K-factor, kerf, build envelope, or required B-Rep evidence; passing rules still require manual review.
5. For the native SolidWorks route, prefer `SolidWorksSession()` to manage connection, opening, creation, saving, and exporting; compose `sw_connect.py`, `sw_part.py`, etc. when low-level control is needed.
6. When user requests are natural-language-heavy, under-specified, or need "domain knowledge base + prompt templates + parametric design plan", first read `subskills/solidworks-vibecad/SKILL.md` to generate `design_plan.json` and an execution summary.
7. For CNC parts, mounting brackets, connector blocks, and mounts with many Fillets/Chamfers, first read `subskills/solidworks-fillet-chamfer-cnc/SKILL.md` and follow the stable sequence: "Base Boss -> External Fillets/Chamfers -> Hole/Slot Cuts -> Hole-edge Chamfers -> Review".
8. For screw holes, threaded holes, tapped holes, and M3/M4/M5/M6/M8 blind or through holes, first read `subskills/solidworks-threaded-holes/SKILL.md`; by default follow the stable pipeline: "Parameter/hole-position validation -> Tap drill hole -> Metric Tap physical Thread -> CosmeticThread / evidence helix fallback -> Hole-edge Chamfer -> Post-rebuild feature evidence -> Properties and review". Hole Wizard, external threads, imperial/pipe threads, and modifying holes in existing parts remain `pilot`.

**Gear Routing Gate:** When the user asks to "draw/model/generate a gear", first read `references/gears.md`—never substitute a Gear Mate for a solid gear request. Use `scripts/sw_gear.py` only for standard external spur gears with known module, tooth count, pressure angle, face width, and bore diameter; do not fabricate parameters for manufacturing tasks, though explicit defaults may be declared for visual demos only. Helical, bevel, internal, rack, worm, profile-shifted, or production-grade modified/backlash gears must route to dedicated workflows or manual review rather than forcing the standard spur gear script. Only "gear linkage / transmission / Mate" requests route to `sw_assembly.add_gear_mate_by_cylinders()`.

9. For standard blind holes, through holes, counterbored holes, countersunk holes, straight slots, or hole patterns, read `references/complex-hole-features.md` and prefer `scripts/sw_hole_features.py`; creation parameter evidence must be cross-checked against `collect_geometry_measurements()`, `validate_hole_positions()`, and section views.
10. For SolidWorks part drawings, assembly drawings, TCVN/ISO engineering drawings (or GB/T reference drawings when explicitly requested), dimension chains, hole tables, BOMs, title blocks, or drawing reviews, first read `subskills/solidworks-engineering-drawing/SKILL.md` and always load `references/tcvn_mechanical.md` as the default baseline for drawings, fits/tolerances, GD&T, surface roughness, welding/weldments, and threads; this subskill consumes model, hole/slot, and property evidence from the root skill. For AutoCAD DWG/DXF, 2D drawings, line-art-to-CAD conversion, batch drawing edits, or AutoCAD native previews, read `subskills/autocad-automation/SKILL.md`. Mechanical and 3D-printed perforated deliverables must be treated as manufacturable drawings: every hole, slot, port, gate, screw hole, and screw boss must specify size, quantity, and locating dimensions; use hole/slot tables when views are congested, and never replace critical dimensions with long leaders.
11. When the user requests "authentic appearance", "1:1 replica", or "not a concept model" for a real-world product, first read `references/mesh-reference-import.md`: prioritize public mesh/blueprint references instead of repeatedly refining a low-fidelity hand-built base; prefer `scripts/sw_import_mesh_reference.py` when importing OBJ/STL.
12. If an LLM must generate VBA macros, first use `sw_macro_guard.py` for model routing, code validation, retries, and local template fallback.
13. Save/export files using `session.export()` or `sw_export.py`.
14. Export preview images and self-review with `sw_review.py`; if GUI/desktop screenshot capability is available, capture SolidWorks viewport screenshots to verify.
15. For Sheet Metal, Weldments, complex surfacing, molds, Routing, Simulation/FEA, complex Motion, or configuration family tasks, first run `sw_capability_probe.py` and read `references/complex-mechanical-routing.md`; use `routing-preflight/check-routing` for Routing, `fea-preflight/prepare-fea/run-fea/run-fea-convergence` for FEA, and `review-advanced-geometry/create-ocp-loft/create-ocp-surface` for complex surfacing. Passing FEA and advanced surface solves remain `review_required`.
16. When enterprise/project mechanical knowledge is needed, read `references/enterprise-agent-rag.md`; default to local knowledge only—Cloud RAG must be explicitly enabled, declare `external_network`, and receive manual approval.
17. When a single request spans two or more engineering domains across parts, holes/slots/Fillets, assembly Mates, Motion, engineering drawings/BOM, and multi-format delivery, call `apps/desktop/cad_workbench/engineering_orchestrator.py` to generate a staged DAG. Critical CAD write operations must execute serially by dependency, saving artifacts and acceptance evidence per stage; local edits replan only affected stages and their downstream dependents—never cram an entire engineering project into one giant prompt and declare completion at once.

### Mechanical Drawing Baseline Standards

Whenever this skill participates in CAD, mechanical structure, or 3D-printing projects, enforce these baseline standards by default:

1. Never treat a "readable schematic" as a "manufacturable engineering drawing". Whenever holes, slots, ports, mounting holes, or printed enclosures are involved, provide overall dimensions, wall/base thicknesses, hole/slot specifications, and locating dimensions.
2. By default (including when the user requests "strict compliance" or standard mechanical drawings), load `references/tcvn_mechanical.md` and enforce the TCVN/ISO baseline (`ISO` drafting standard, `MMGS`, First-Angle projection, hole-basis fits, ISO GD&T/weld symbols, and TCVN general tolerance notes).
3. Treat `GB/T`, `GB`, and `JB/T` conventions in this repo as reference only; apply Chinese mechanical drafting conventions (standard sheet sizes/borders/title blocks, FangSong Chinese typography, layered line types, centerlines/hidden lines, native dimension entities, and technical notes) only when the user explicitly requests "Chinese standard format" or "GB/T style".
4. Long leaders may only be used for local callouts, never as substitutes for dimension chains; they must not cross views, overlap holes, centerlines, or dimension text, or intrude into the title block.
5. Dense hole/slot patterns must prefer hole tables, slot tables, or hole/slot schedules specifying location/region, specification, quantity, and coordinates; tables must not be used as an excuse to omit locating dimensions.
6. Visually review preview images before delivery; if missing dimensions, overlaps, line crossings, or title block intrusions are found, rework before reporting.

### High-Fidelity Appearance / Public Mesh Reference Models

When the user requests high-fidelity visual reproduction of real-world objects (automobiles, consumer electronics, sculptures, etc.), first distinguish between a "visual reference model" and a "manufacturable parametric engineering model":

1. If the user wants it to "look like the original", first request or locate public 3D models / multi-view blueprints and record source, author, license, and download date; do not claim the output is an official Class-A or scan-grade model.
2. Convert `.glb/.gltf/.fbx/.blend` to `.obj/.stl` first; prefer OBJ to preserve materials, with STL as a material-less fallback.
3. Verify coordinate axes and scale via bounding box before importing, then scale to true nominal dimensions.
4. If Python conversion/scaling is required, verify optional dependencies in `requirements-mesh.txt` are available; if missing, explain their purpose and prompt for installation.
5. Use `sw_import_mesh_reference.py` to import OBJ/STL into SolidWorks; the key call is `LoadFile4(path, "r", create_empty_dispatch_variant(), errors)`—do not use `OpenDoc6()` or pass `None` to `LoadFile4()`.
6. Result review must inspect four views and key identifying features; "non-blank preview" is no substitute for "resembles the user-specified object".
7. If the user later requires an editable engineering structure, reverse-engineer separate parametric parts against the mesh reference and explicitly clarify that imported mesh bodies are not parametric solids.

### Multi-Color Appearance Requirements

When a model includes car bodies, glass, lighting assemblies, tires, wheels, or other multi-color components:

1. Read `references/appearance.md` and consistently use `sw_appearance.py`; never pass a plain Python `list` directly to COM material properties.
2. Set document-level colors on source parts first; apply component-level color overrides in assemblies only when needed.
3. After each assignment, call `verify_appearance()` or `apply_component_palette()` to read back RGB values; checking only the setter return value is insufficient.
4. Call `model.ClearSelection2(True)` before saving and capturing screenshots; `sw_review.save_preview()` already includes this cleanup.
5. Visually confirm that at least three expected colors are genuinely visible; "non-blank preview" does not replace color verification.
6. If appearance anomalies occur, run `tests/solidworks_appearance_regression.py` first before rebuilding the user model.

### Using the MCP Server

When the user asks to "enable MCP for SolidWorks", "connect tool calling in Codex/Claude Desktop", or "avoid generating huge Python scripts every time":

1. Read `mcp-server/README.md`.
2. If the user asks for automatic MCP configuration, prefer running the multi-client registrar: `powershell -ExecutionPolicy Bypass -File mcp-server/register_all_ai_mcp.ps1 -InstallDependencies`; it attempts to register Codex, Claude Code, Claude Desktop, Cursor, and Windsurf.
3. Use the local `stdio` MCP server: `python mcp-server/server.py`; discovery mode is the default (`SW_MCP_DISCOVERY=search`), exposing only `sw_search_tools` / `sw_describe_tool` / `sw_call_tool`. Set `SW_MCP_DISCOVERY=full` to expose all named tools.
4. Follow the "Search -> Read Schema -> Execute" workflow in discovery mode: first use `sw_search_tools` with English or Chinese keywords to find candidates, then `sw_describe_tool` to verify parameters, and finally `sw_call_tool`. Do not guess tool names directly.
5. Default discovery mode trusts that the client has already obtained authorization for the current task; execute modeling within the user's authorized scope without requesting
   per-step approval. Explicit authorization is still required for unauthorized overwrites, closing documents, or other high-risk actions.
   You may supply `document_target` (absolute `path` and SolidWorks
   `process_id`) for active-document write operations on saved files to validate the target; if omitted, the tool falls back to its default active-document behavior.
   If the user explicitly enables per-call `server` approval, have the user run
   `python scripts/sw_mcp_approve.py approve <请求ID>` on the server when a request ID is returned; stop and report limitations if the target cannot be verified.
6. For CAD-free open-format writing, prefer `cadstudio_write_open_format`; for DFM, Routing, FEA, and complex geometry, call `cadstudio_check_dfm`, `cadstudio_check_routing`, `cadstudio_routing_preflight`, `cadstudio_fea_preflight`, `cadstudio_prepare_fea`, `cadstudio_run_fea`, `cadstudio_run_fea_convergence`, `cadstudio_review_advanced_geometry`, `cadstudio_create_ocp_loft`, and `cadstudio_create_ocp_surface`, respectively; for native SolidWorks operations, call allowlisted `solidworks_*` tools.
7. Do not expose arbitrary Python/VBA execution tools; new MCP tools should reuse verified wrappers from `scripts/sw_*.py`.
8. SolidWorks COM operations must execute serially; the MCP server uses an internal global lock to minimize desktop session contention.
9. Use `examples/08_mini_fan_motion_assembly.py` as the benchmark demo; it verifies automated modeling, assembly, Mates, and Motion Study without promising perfect Fillet/Chamfer aesthetics.

### Kinematic Assembly Requirements

When the user requests "make it move", "draggable in SolidWorks", "hinge", "gear linkage", or "real mechanical Mates":

1. First read the kinematic assembly workflow in `references/assembly.md`; if the user explicitly requests Motion Study / motors, also read `references/motion-study.md`.
2. Prefer reusing `resolve_component()`, `get_assembly_entity()`, `find_largest_cylinder_face()`, `add_mate5_checked()`, `add_concentric_mate_by_cylinders()`, and `add_gear_mate_by_cylinders()` from `sw_assembly.py`.
3. Use Concentric Mates with `lock_rotation=False` for rotating parts; do not lock shafts, gears, or hinged lids with three reference planes.
4. Use real Gear Mates for gear transmissions; do not fake mechanical Mates with scripted animation.
5. After creation, verify via `collect_mate_feature_summary()` or feature tree traversal that real Mate features such as `MateConcentric` and `MateGearDim` exist under MateGroup.
6. When a real Motion Study is needed, prefer reusing `sw_motion.create_motion_study()`, `add_constant_speed_rotary_motor_by_cylinders()`, and `calculate_and_play()` to build the Motion Study and rotary motor.
7. After calculation, call `sw_motion.validate_motion_studies()` or MCP `solidworks_validate_motion_study` to verify study type, duration, motor count, result existence, and `results_out_of_date=False`; merely seeing a timeline, animation, or `Calculate=True` does not pass acceptance.
8. If a demo animation is desired, scripted component transforms or Mate Controller may be added, but clarify that scripted animation is not equivalent to interactive degrees of freedom; interactive dragging in SolidWorks is the final criterion.

## GPT / Kimi / Claude Multi-Model Strategy

When an agent needs an LLM to generate VBA macros, it must go through `scripts/sw_macro_guard.py`:

1. **Model Routing**: GPT-series models use the standard concise prompt; Kimi / Claude / unknown models automatically load a strict-format prompt enforcing VBA-source-only output.
2. **Local Template Fallback**: If model output or parsing fails, do not immediately error out; select a built-in VBA template matching user keywords (e.g., cube, cylinder, Extrude, Sketch) to proceed.
3. **Output Validation**: Before execution, verify `SldWorks`, `ModelDoc2`, `Sub`, and `End Sub` before passing code to SolidWorks; retry on failure.
4. **Timeout / Retry**: Recommend a `30s` timeout per model request; automatically retry `1~2` times on parse failure with stricter formatting instructions appended.

Example:

```python
from sw_macro_guard import build_prompt, fallback_macro_for_request, validate_vba_macro

prompt = build_prompt("画一个 50mm 圆柱", model_name="claude")
macro = fallback_macro_for_request("画一个 50mm 圆柱")
result = validate_vba_macro(macro)
assert result.ok, result.issues
```

## Unwrapped API Rules

When a task requires calling a SolidWorks API not yet wrapped in `scripts/`:

1. First read `references/api-lookup.md` and run `python SKILL_DIR/scripts/sw_api_lookup.py 接口 方法` to query the target version's local type library and official documentation; pass `--version 2024` when the target year is known and `--process-id` for multi-instance setups. Confirm signatures, units, prerequisites, and version differences.
2. Never guess APIs from memory—especially long-argument COM methods, `VARIANT` / by-ref parameters, enum values, selection marks, and `SaveAs`-family methods.
3. Keep scripts minimal and runnable, checking every step's return value for `None` / `False`.
4. After implementation, actually execute the script, save or export target files, and generate preview images and a review report with `sw_review.py`.
5. Document newly discovered pitfalls, error codes, compatibility patterns, or stable wrappers in `references/troubleshooting.md` or the corresponding module reference; promote recurring logic into `scripts/`.

Lookup accesses official SolidWorks documentation by default, falling back to anonymous Parallel queries when direct official fetch fails and no cache exists; only public version, interface, member, and official URLs are sent. `--offline` or `SW_API_LOOKUP_NETWORK=off` disables network access for this tool; `--no-parallel` or `SW_API_LOOKUP_PARALLEL=off` disables Parallel only. Offline mode uses local help and previously cached results—pay attention to version evidence and fetch timestamps. When documentation is insufficient, the client's built-in search may be used within client-permitted limits for public API identifiers only; client network permissions are controlled by the client. Interface declarations, official docs, and live-machine behavior must be assessed separately—never claim verified compatibility without target-version or runtime validation.

When a natural-language task does not name specific APIs, first run `python SKILL_DIR/scripts/sw_api_lookup.py --task "任务描述"` to automatically look up common candidates; candidates are not mandatory solutions. When no candidates match or planning identifies other APIs, determine interfaces and members from existing wrappers first, then query each for the target version—never send the full task text to third-party services.

## Result Self-Review

Perform a self-review after every CAD creation, modification, import, or export unless the user explicitly opts out:

1. Verify COM return values, feature objects, save/export return statuses, and output file sizes.
2. Call `model.ForceRebuild3(False)` and `model.ViewZoomtofit2()` to refresh the model.
3. Use `run_review()` from `scripts/sw_review.py` to export `isometric/front/top/right` preview images and write `*_review_report.json`.
4. Inspect `evaluation.status`, `evaluation.issues`, `checks`, and preview images in the report; verify via screenshots or exported BMPs that the main body exists, proportions/orientation are sensible, key components are present, there are no obvious overlaps or floating bodies, and filenames/output paths are correct.
5. If issues are found, fix the script and regenerate before reporting; never merely report "saved successfully".

Example:

```python
from sw_review import run_review

model.ForceRebuild3(False)
report, report_path = run_review(
    model,
    r"C:\temp\review",
    basename="car",
    expected_outputs=[r"C:\temp\car.sldprt", r"C:\temp\car.step"],
)
print(report_path)
print(report["evaluation"])
```

## Key Technical Notes

- **Units**: The API consistently uses **meters**. Use `mm(50)` to convert 50mm to 0.05m and `deg(90)` for angles
- **Version**: Specify the SolidWorks year and verify the target instance; per-operation compatibility is governed by `capabilities.yaml` and live-version evidence—do not treat a successful connection as compatibility across all features
- **Selection**: Prefer object-level `Select2()` when a COM object is available; reference planes may use `SelectByID2("PLANE")`, and Sketches should not rely solely on `SelectByID2("SKETCH")`
- **Sketch**: Prefer `with sketch(model, "Front Plane") as sketch_name:` to automatically enter/exit Sketches; `sw_part.py` caches Sketch object references to avoid name-based Sketch selection failures in Chinese-edition SW2024
- **Adding Components**: Prefer `sw_assembly.add_component()` for assemblies; `AddComponent4` may return `None` in Chinese-edition SW2024, so the wrapper falls back to `AddComponent5`, silently opening the part and reactivating the assembly before retrying
- **Appearance**: For color-critical models, prefer splitting into multi-part assemblies; material arrays must be marshaled as `SAFEARRAY(double)` and verified by reading back RGB values
- **VARIANT**: By-ref parameters must be wrapped with `VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)`
- **Reference Plane Names**: `start_sketch()` automatically supports both English "Front/Top/Right Plane" and Chinese "前视/上视/右视基准面"
- **Sketch Coordinates**: Defined in the Sketch plane's local coordinate system, in meters
- **Kinematic Assemblies**: Resolve components before selecting Mate entities; `GetCorresponding()` maps part-level faces/features into assembly context; Concentric Mates default to unlocked rotation
- **Motion Study**: `swmotionstudy.tlb` must be loaded; under pywin32, `CreateMotionStudy` / `Activate` / `Calculate` may appear as properties—prefer `sw_motion.motion_member()` for compatibility
