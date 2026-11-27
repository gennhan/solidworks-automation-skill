# CAD Automation Delivery Workbench MVP Product Specification

Version: v0.1  
Date: 2026-07-25  
Related research: `docs/market-research-2026.md`

> **Historical Specification Note (2026-10-27)**: This document is the 2026-07-25 MVP specification, in which "Desktop UI: PySide6 / Qt"
> has been superseded by subsequent implementation—the current desktop client is **Tauri + React** (`apps/workbench-ui/`),
> while the PySide6 prototype resides in `apps/desktop/` and is marked legacy. The original specification is preserved here for design-intent traceability
> and does not describe the current tech stack.

## 1. Product Positioning

Tentative product name:

```text
CAD 自动化交付工作台
```

One-line summary:

```text
面向机械工程师和 3D 打印打样用户，把常见结构件从参数输入到建模、出图、规范复核和交付归档做成一个本地软件流程。
```

Version 1 does not build a new CAD app, cloud collaboration, or full PLM. It closes one real end-to-end loop:

```text
3D 打印外壳自动交付
```

## 2. MVP Success Criteria

A user on a local Windows PC can complete:

1. Create a new 3D-printed enclosure project.
2. Enter outer dimensions, wall thickness, holes, slots, screw bosses, and connector cutout parameters.
3. Invoke SolidWorks to automatically generate a 3D model with genuine geometric cuts.
4. Invoke SolidWorks Drawing or AutoCAD to generate engineering drawings.
5. Automatically check whether drawings satisfy P0 standards.
6. Output a complete delivery package.

### Acceptance Metrics

| Metric | MVP Target |
|---|---|
| Project creation to parameter confirmation | Under 5 minutes |
| Modeling script execution | Under 10 minutes |
| Initial engineering drawing generation | Under 5 minutes |
| Missed P0 drawing callouts | Must be 0 |
| Output file traceability | Every file recorded in manifest |
| Failure diagnosability | Every failure reports stage, reason, and suggested action |

## 3. Technical Boundaries

### Local-First Execution

No rented servers and no cloud job queues. All CAD files, reference images, parameters, and review reports stay on the user's local machine.

Recommended stack (original MVP):

```text
桌面界面: PySide6 / Qt
自动化脚本: Python + pywin32/comtypes
CAD 控制: SolidWorks COM + AutoCAD COM
项目数据: 本地 JSON / Markdown / 文件夹
打包: PyInstaller
版本更新: GitHub 仓库
```

### Non-Goals

- No custom CAD geometry kernel.
- No browser-hosted web service.
- No multi-user collaboration.
- No user account system.
- No claim of fully autonomous generation for arbitrary complex parts.
- No enterprise PDM/PLM integration.
- No arbitrary Python/VBA/AutoLISP execution endpoint exposed to general users.

## 4. V1 User Persona

### Primary Users

Independent mechanical designers, automation equipment engineers, makers, and 3D-printing prototyping users.

What they care about most:

- Whether holes are genuinely cut through.
- Whether the model can be 3D-printed directly.
- Whether drawings adhere to mechanical engineering standards (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, retaining `GB/T` as a secondary reference).
- Whether hole positions, slots, and connector cutouts are fully dimensioned.
- Whether files are ready to hand off to machining, printing, or clients.

### Prerequisites

The user's local machine requires:

- Windows.
- SolidWorks installed and launched at least once.
- AutoCAD installed and launched at least once (optional if only SolidWorks Drawing is used).
- Python 3.10+.
- `pywin32` / `comtypes`.

## 5. Information Architecture

The V1 desktop interface uses left navigation + center task form + right review/output panel.

```text
┌────────────────────────────────────────────────────────────────┐
│ CAD 自动化交付工作台                                            │
├──────────────┬──────────────────────────┬──────────────────────┤
│ 项目          │ 任务: 3D 打印外壳          │ 复核状态              │
│ 新建项目      │                          │ P0 规范检查            │
│ 参数模板      │ 外形尺寸 / 开孔 / 螺丝柱   │ 输出文件              │
│ 生成模型      │ 工程图 / 技术要求          │ 执行日志              │
│ 生成图纸      │                          │                      │
│ 规范复核      │ [保存参数] [生成模型]      │ [打开输出目录]        │
│ 输出交付      │ [生成图纸] [一键复核]      │                      │
│ Skills 管理   │                          │                      │
└──────────────┴──────────────────────────┴──────────────────────┘
```

## 6. Core Workflow

### 6.1 Create Project

User inputs:

- Project name.
- Project type: `3d_print_shell`.
- Output directory.
- Units: default `mm`.
- Drawing style: this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO** as default, while retaining `GB/T` as a secondary reference.
- Require AutoCAD DWG/DXF: enabled by default.
- Require native SolidWorks Drawing: optional.

System actions:

1. Create the project directory.
2. Write `project.json`.
3. Create `inputs/`, `outputs/`, `reviews/`, `previews/`, and `logs/`.
4. Verify SolidWorks/AutoCAD/Python dependencies.

### 6.2 Upload Reference Image

Supported formats:

- `jpg`
- `png`
- `jpeg`
- `bmp`

Purpose:

- Appearance reference.
- Assist in locating hole and connector positions.
- Never used directly as manufacturable dimensional authority.

Rule:

Reference images do not replace dimensions. Every hole, slot, connector cutout, port, screw hole, and boss must have explicit specifications and locating dimensions in the parameter table.

### 6.3 Fill Parameters

Uses a structured form, with prompts serving only as supplementary notes.

Required sections:

- Overall dimensions.
- Wall / bottom thickness.
- Fillets / chamfers.
- Holes / slots.
- Screw bosses / mounting holes.
- Drawing settings.
- Technical notes.

### 6.4 Generate Model

System actions:

1. Read `parameters.json`.
2. Generate or invoke the SolidWorks modeling script.
3. Build the main enclosure body.
4. Apply shell or boolean cut.
5. Perform real geometric cuts for all holes, slots, and connector cutouts.
6. Add screw bosses, ribs, and fillets/chamfers.
7. Save `SLDPRT`.
8. Export `STEP` and `STL`.
9. Execute model review.

Mandatory checks:

- Model is non-empty.
- Overall dimensions match parameters.
- Wall thickness is present.
- Hole/slot counts match the parameter table.
- Holes/slots are genuine geometric cuts rather than decorative sketch lines.
- STL file exists and has a reasonable file size.

### 6.5 Generate Engineering Drawings

Supports two routes:

| Route | Use Case |
|---|---|
| SolidWorks Drawing | Generate orthographic/isometric views, dimensions, and PDF directly from the 3D model |
| AutoCAD DWG/DXF | Generate standard DWG/DXF engineering drawings, hole/slot tables, and title blocks |

The MVP prioritizes AutoCAD DWG/DXF drawings because users explicitly require standard DWG/DXF deliverables and strict drafting conventions (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, retaining `GB/T` as a secondary reference).

Drawings must include:

- Drawing frame (border).
- Title block.
- Units.
- Scale.
- Front view.
- Top view.
- Right view or required section view.
- Isometric reference view.
- Overall exterior dimensions.
- Wall / bottom thickness.
- Hole/slot specifications and quantities.
- Hole/slot locating dimensions.
- Technical notes.
- Hole/slot schedule table.

### 6.6 Standards Review

Review is split into automated checks and visual inspection.

Automated checks:

- File existence.
- Reasonable DWG/DXF bounding box.
- Layer completeness.
- Dimension entity count meets threshold.
- Hole/slot entity count matches parameters.
- Title block present.
- Hole/slot table present.
- Complete `review.json` schema.

Visual inspection:

- No dimension lines colliding with geometry.
- No leader lines crossing views.
- No overlapping text.
- No intrusion into the title block.
- Clear, unambiguous hole/slot locating dimensions.
- Overall presentation meets mechanical engineering drafting expectations (prioritizing **TCVN and ISO**, with `GB/T` as a secondary reference).

## 7. Page Specifications

### 7.1 Home / Project List

Displays:

- Recent projects.
- Project name.
- Type.
- Last modified timestamp.
- Last run status.
- Output directory.

Actions:

- New project.
- Open project.
- Open output directory.
- Duplicate project.
- Delete project record without deleting source files unless explicitly confirmed by the user.

### 7.2 New Project Page

Fields:

| Field | Type | Default | Required | Description |
|---|---|---|---|---|
| project_name | text | Empty | Yes | Project name |
| project_type | select | 3D-printed enclosure | Yes | Single template in MVP |
| output_root | folder | User-selected | Yes | Root output directory |
| unit | select | mm | Yes | Millimeters only initially |
| drawing_standard | select | TCVN / ISO (secondary: GB/T) | Yes | Extensible to enterprise templates later |
| need_dwg | checkbox | true | No | Export DWG |
| need_dxf | checkbox | true | No | Export DXF |
| need_pdf | checkbox | true | No | Export PDF |
| need_stl | checkbox | true | No | Export STL |
| need_step | checkbox | true | No | Export STEP |

### 7.3 Parameter Form Page

#### Exterior Dimensions

| Field | Type | Unit | Required | Validation |
|---|---|---|---|---|
| outer_length | number | mm | Yes | > 0 |
| outer_width | number | mm | Yes | > 0 |
| outer_height | number | mm | Yes | > 0 |
| wall_thickness | number | mm | Yes | >= 0.8 |
| bottom_thickness | number | mm | Yes | >= 0.8 |
| corner_radius | number | mm | No | >= 0 |
| edge_chamfer | number | mm | No | >= 0 |
| shell_open_direction | select | - | Yes | top / bottom / side |

#### 3D Printing Parameters

| Field | Type | Unit | Default | Description |
|---|---|---|---|---|
| print_process | select | - | FDM | FDM / SLA / SLS; MVP prioritizes FDM |
| nozzle_diameter | number | mm | 0.4 | FDM nozzle size |
| hole_compensation | number | mm | 0.2 | Suggested hole clearance allowance |
| fit_clearance | number | mm | 0.3 | Mating clearance |
| min_wall_warning | number | mm | 1.2 | Warn when below threshold |

#### Hole Parameters

Every hole must define:

- Type.
- Specification.
- Quantity.
- Target face.
- Datum edges.
- Center location.

Fields:

| Field | Type | Unit | Required | Description |
|---|---|---|---|---|
| id | text | - | Yes | e.g., H1 |
| name | text | - | Yes | e.g., Display mounting hole |
| hole_type | select | - | Yes | round / counterbore / countersink / threaded / slot |
| face | select | - | Yes | front / back / left / right / top / bottom |
| diameter | number | mm | Conditional | Circular hole diameter |
| width | number | mm | Conditional | Slot width |
| length | number | mm | Conditional | Slot length |
| quantity | number | pcs | Yes | >= 1 |
| datum_x | select | - | Yes | left / right / centerline |
| datum_y | select | - | Yes | bottom / top / centerline |
| center_x | number | mm | Yes | Offset relative to X datum |
| center_y | number | mm | Yes | Offset relative to Y datum |
| pitch_x | number | mm | Conditional | Horizontal pitch for patterns |
| pitch_y | number | mm | Conditional | Vertical pitch for patterns |
| through | checkbox | - | Yes | Through-hole flag |
| note | text | - | No | Process note |

#### Interface Cutouts

Interface cutouts fall under the hard hole/slot rules and cannot be specified as text notes only.

Common types:

- USB-C.
- Circular DC jack.
- HDMI.
- RJ45.
- Button hole.
- Indicator LED hole.
- Display window.
- Port/opening.
- Ventilation slot.

Interface fields:

| Field | Type | Unit | Required |
|---|---|---|---|
| id | text | - | Yes |
| interface_type | select | - | Yes |
| face | select | - | Yes |
| cutout_width | number | mm | Conditional |
| cutout_height | number | mm | Conditional |
| cutout_diameter | number | mm | Conditional |
| corner_radius | number | mm | No |
| center_x | number | mm | Yes |
| center_y | number | mm | Yes |
| quantity | number | pcs | Yes |
| clearance | number | mm | No |

#### Screw Boss Parameters

| Field | Type | Unit | Required | Description |
|---|---|---|---|---|
| id | text | - | Yes | e.g., B1 |
| screw_size | select | - | Yes | M2 / M2.5 / M3 / M4 |
| boss_outer_diameter | number | mm | Yes | Outer diameter of boss |
| hole_diameter | number | mm | Yes | Pilot or insert hole diameter |
| boss_height | number | mm | Yes | Height of screw boss |
| face | select | - | Yes | Target face |
| center_x | number | mm | Yes | X location |
| center_y | number | mm | Yes | Y location |
| quantity | number | pcs | Yes | Quantity |
| rib_enabled | checkbox | - | No | Add reinforcement ribs |

### 7.4 Execution Page

Displayed stages:

```text
preflight -> build_model -> export_model -> build_drawing -> export_drawing -> review -> package
```

Each stage displays:

- Status: `waiting` / `running` / `passed` / `warning` / `failed`.
- Start time.
- End time.
- Log summary.
- Failure reason.
- Suggested remediation.

### 7.5 Review Report Page

Divided into four sections:

1. Model review.
2. Drawing review.
3. 3D printability review.
4. Delivery package review.

Statuses:

- `pass`: Ready for delivery.
- `warning`: Deliverable with human confirmation.
- `fail`: Not deliverable; rework required.

Whenever any P0 rule fails, overall status must be `fail`.

## 8. Project Directory Structure

Each project is saved in its own folder:

```text
<output_root>/<project_slug>/
├── project.json
├── parameters.json
├── inputs/
│   ├── reference_001.png
│   └── brief.md
├── generated/
│   ├── build_model.py
│   ├── build_drawing.py
│   └── drawing_plan.json
├── outputs/
│   ├── model/
│   │   ├── <project>.sldprt
│   │   ├── <project>.step
│   │   └── <project>.stl
│   ├── drawing/
│   │   ├── <project>.dwg
│   │   ├── <project>.dxf
│   │   └── <project>.pdf
│   └── package/
│       └── <project>_delivery.zip
├── previews/
│   ├── model_iso.png
│   ├── model_front.png
│   ├── drawing_preview.png
│   └── package_cover.png
├── reviews/
│   ├── model_review.json
│   ├── drawing_review.json
│   ├── printability_review.json
│   └── final_review.json
├── logs/
│   └── run_YYYYMMDD_HHMMSS.log
└── README_交付说明.md
```

## 9. Data File Specifications

### 9.1 project.json

```json
{
  "schema_version": "0.1",
  "project_id": "20260725_001",
  "project_name": "ai_cpu_cooling_shell",
  "project_type": "3d_print_shell",
  "unit": "mm",
  "drawing_standard": "GB_T_style",
  "created_at": "2026-07-25T20:00:00+08:00",
  "updated_at": "2026-07-25T20:00:00+08:00",
  "output_root": "C:/Users/current/Documents/CADAutomationWorkbench",
  "status": "draft"
}
```

### 9.2 parameters.json

```json
{
  "schema_version": "0.1",
  "units": "mm",
  "shell": {
    "outer_length": 120,
    "outer_width": 80,
    "outer_height": 35,
    "wall_thickness": 1.6,
    "bottom_thickness": 2.0,
    "corner_radius": 4,
    "edge_chamfer": 0.5,
    "open_direction": "top"
  },
  "printing": {
    "process": "FDM",
    "nozzle_diameter": 0.4,
    "hole_compensation": 0.2,
    "fit_clearance": 0.3,
    "min_wall_warning": 1.2
  },
  "features": {
    "holes": [],
    "cutouts": [],
    "bosses": [],
    "vents": []
  },
  "drawing": {
    "paper_size": "A3",
    "scale": "1:1",
    "title": "3D打印外壳",
    "material": "PLA/PETG",
    "projection": "first_angle",
    "required_exports": ["dwg", "dxf", "pdf", "png"]
  }
}
```

### 9.3 final_review.json

```json
{
  "schema_version": "0.1",
  "overall_status": "fail",
  "project_id": "20260725_001",
  "checked_at": "2026-07-25T20:30:00+08:00",
  "checks": [
    {
      "id": "drawing-hole-position-complete",
      "severity": "P0",
      "status": "fail",
      "target": "drawing",
      "message": "接口孔 I1 缺少 X/Y 中心定位尺寸",
      "suggestion": "补充相对左边和底边的中心定位尺寸"
    }
  ],
  "outputs": {
    "sldprt": "outputs/model/project.sldprt",
    "step": "outputs/model/project.step",
    "stl": "outputs/model/project.stl",
    "dwg": "outputs/drawing/project.dwg",
    "dxf": "outputs/drawing/project.dxf",
    "pdf": "outputs/drawing/project.pdf",
    "preview": "previews/drawing_preview.png"
  }
}
```

## 10. P0 Standards Checklist

### 10.1 Model P0

| ID | Check Item | Failure Condition |
|---|---|---|
| model-file-exists | Model files exist | SLDPRT/STEP/STL missing or abnormal file size |
| model-solid-body | Main solid body present | No solid body or unexpected body count |
| model-shell-thickness | Wall / bottom thickness present | Thickness not modeled or below user parameters |
| model-cut-through | Holes genuinely cut | Holes/slots are only sketches/lines/cosmetics and do not penetrate the target face |
| model-feature-count | Feature count matches | Hole/slot count in model disagrees with parameter table |
| model-print-scale | Correct dimensional units | Exported STL scale does not correspond to mm |

### 10.2 Drawing P0

| ID | Check Item | Failure Condition |
|---|---|---|
| drawing-frame-title | Frame and title block | Missing frame, title block, units, or scale |
| drawing-main-dimensions | Overall exterior dimensions | Any of length, width, or height missing |
| drawing-wall-dimensions | Wall / bottom thickness | 3D-printed enclosure missing wall or bottom thickness callout |
| drawing-hole-spec | Hole/slot specifications | Missing size, quantity, or type |
| drawing-hole-position | Hole/slot locating dimensions | Missing X/Y location, center distance, or datum dimension |
| drawing-real-dimensions | Real dimension entities | Key dimensions faked with manual lines or plain text |
| drawing-leader-crossing | Leader crossings | Long leaders cross views, holes, centerlines, or overlap text |
| drawing-overlap | Drawing collisions | Overlapping dimensions, text, or tables impair readability |
| drawing-title-intrusion | Title block intrusion | Dimension lines or text enter the title block |
| drawing-hole-table | Hole/slot schedule table | Crowded holes/slots lack a table, or table lacks spec/qty/location |

### 10.3 3D Printing P0

| ID | Check Item | Failure Condition |
|---|---|---|
| print-min-wall | Minimum wall thickness | Below user-defined hard lower bound |
| print-open-hole | Required openings | User requested openings not cut in the model |
| print-fit-clearance | Mating clearance | Assembly fit requested without clearance allowance |
| print-stl-valid | STL export | File missing, empty, or incorrect scale |

## 11. Default Drawing Style

This localized edition prioritizes **TCVN (Vietnamese Standards) and ISO** as the default mechanical drafting convention, while retaining `GB/T` as a secondary reference.

Default settings:

| Item | Default |
|---|---|
| Sheet size | A3, or A4 when appropriate |
| Units | mm |
| Scale | 1:1; 1:2 or 2:1 if geometry does not fit |
| Font | Technical drafting font; when unavailable, fall back to an installed Unicode font and log it |
| Line types | Separate layers for thick continuous, thin continuous, centerline, hidden, and dimension lines |
| Title block | Lower-right corner |
| Views | Front, top, right/section view, plus isometric reference |
| Tables | Prioritize hole/slot schedule tables |

Note:

```text
“参照 GB/T 风格”不是替代企业审图。若用户提供企业模板，必须优先使用企业模板。
```

*(In this localized edition, TCVN/ISO defaults—with `GB/T` retained as a secondary reference—likewise never replace company drawing review; always prioritize user-supplied company templates.)*

## 12. Delivery Package Specification

The delivery package must contain:

```text
01_model/
  project.sldprt
  project.step
  project.stl

02_drawing/
  project.dwg
  project.dxf
  project.pdf
  drawing_preview.png

03_review/
  model_review.json
  drawing_review.json
  printability_review.json
  final_review.json

04_source/
  project.json
  parameters.json
  generated_scripts/

README_交付说明.md
```

`README_交付说明.md` must document:

- Project name.
- Units.
- Material and printing process assumptions.
- Description of output files.
- Drawing standard reference.
- Review status.
- Items still requiring human confirmation.

## 13. State Machine

Project states:

```text
draft -> ready -> running -> generated -> reviewing -> pass
                                      -> warning
                                      -> failed
```

Stage states:

```text
waiting
running
passed
warning
failed
skipped
```

Rules:

- Any P0 failure sets project status to `failed`.
- P1 failures may set project status to `warning`.
- Project status may be `pass` only when all required outputs exist and all P0 checks pass.

## 14. Error Handling

Errors must be recorded in structured JSON:

```json
{
  "stage": "build_drawing",
  "error_code": "AUTOCAD_COM_REJECTED",
  "message": "AutoCAD COM 调用被拒绝",
  "retryable": true,
  "suggestion": "等待 AutoCAD 空闲后重试，必要时关闭弹窗或重启 AutoCAD"
}
```

Common error codes:

| Error Code | Stage | Handling |
|---|---|---|
| SOLIDWORKS_NOT_FOUND | preflight | Prompt user to install or launch SolidWorks |
| PYWIN32_MISSING | preflight | Prompt user to install dependencies |
| AUTOCAD_NOT_FOUND | preflight | Prompt user to install or launch AutoCAD |
| AUTOCAD_COM_REJECTED | build_drawing | Retry serially; prompt user to dismiss dialogs if needed |
| FEATURE_PARAM_INCOMPLETE | validate_parameters | Block generation and request missing hole/slot locations |
| MODEL_CUT_MISSING | review_model | Rework 3D model |
| DRAWING_DIM_MISSING | review_drawing | Rework drawing |
| EXPORT_FILE_MISSING | package | Re-export missing file |

## 15. MVP UI Priority

### P0 Pages

- Home / Project list.
- New project.
- 3D-printed enclosure parameter form.
- Execution log page.
- Review report page.
- Output files page.

### P1 Pages

- Skills version management.
- Rule library configuration.
- Enterprise template import.
- Historical project duplication.

### P2 Pages

- Visual hole-position editor.
- 3D preview.
- Online drawing markup.
- Multi-template marketplace.

## 16. Development Breakdown

### First Runnable Milestone

Goal:

```text
能创建项目、保存参数、跑一次 mock 执行、生成 review.json 和交付目录。
```

Tasks:

1. Set up the desktop project directory.
2. Implement main window and navigation.
3. Implement project creation.
4. Implement parameter form.
5. Implement local JSON persistence.
6. Implement mock execution state machine.
7. Implement opening the output directory.

### Second Milestone

Goal:

```text
接入 SolidWorks，生成真实 3D 打印外壳模型。
```

Tasks:

1. Integrate `sw_preflight.py`.
2. Integrate SolidWorks modeling scripts.
3. Export SLDPRT / STEP / STL.
4. Generate model previews.
5. Generate model review report.

### Third Milestone

Goal:

```text
接入 AutoCAD，生成符合 P0 规则的 DWG/DXF 工程图。
```

Tasks:

1. Integrate `acad_preflight.py`.
2. Generate `drawing_plan.json`.
3. Invoke AutoCAD drafting.
4. Export DWG / DXF / PDF / PNG.
5. Implement P0 drawing review.

### Fourth Milestone

Goal:

```text
一键交付包。
```

Tasks:

1. Collect all outputs.
2. Write delivery notes.
3. Archive delivery package.
4. Build final status page.

## 17. V1 Open Questions

Items requiring subsequent verification:

- Stability of AutoCAD preview export across versions.
- Whether SolidWorks Drawing or AutoCAD Drawing yields less rework.
- Reliable geometric detection of whether holes/slots genuinely cut through.
- Which P0 drawing checks can be automated vs. which must remain human visual sign-off.
- Whether to bundle built-in default drawing frames or require users to import enterprise templates.

## 18. Next Step

Proceed next to prototyping under:

```text
apps/desktop/
```

Minimal implementation:

- PySide6 main window.
- Project creation.
- Parameter form.
- Local project directory creation.
- Mock execution and `review.json`.

Integrate SolidWorks and AutoCAD only after the mock prototype runs end-to-end, validating the user workflow before wrestling with COM stability.
