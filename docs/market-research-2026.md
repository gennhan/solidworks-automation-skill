# SolidWorks Automation Skill Market Research and Product Positioning

Research date: 2026-07-25

## 1. Executive Summary

Do not build a new CAD application, and do not start with a polished but empty visual shell.

A stronger direction is:

```text
面向机械工程师和打样团队的本地 CAD 自动化交付助手
```

Core value proposition:

```text
传参考图/填参数 -> 自动建模 -> 自动出工程图 -> 按国标和制造规则复核 -> 输出可交付文件包
```

This direction avoids head-on competition with SolidWorks, Inventor, Fusion, NX, and Creo, focusing instead on repetitive, error-prone, yet mission-critical tasks engineers face every day.

## 2. Market Signals

### 2.1 CAD and Industrial R&D Design Software Continue Growing

- Research and Markets' 2026 CAD Market Report segments CAD software by 3D/2D, deployment model, modeling approach, and application vertical, identifying engineering firms and industrial design studios as key end users.
- A 2025 Chyxx (Zhiyan Consulting) report estimates the 2024 global industrial R&D design software market at roughly USD 55 billion and the Chinese industrial R&D design software market at roughly RMB 35 billion, driven by smart manufacturing, digital transformation, and domestic adoption.

Assessment:

The core CAD market is huge but heavily dominated by incumbents, and building a full CAD kernel requires massive investment. We should build productivity and automation tooling around existing CAD systems.

### 2.2 AI Use Cases in Mechanical Engineering Are Clear

In its 2026 overview of AI tools for mechanical engineering, CoLab Software groups AI adoption into five categories:

- Engineering knowledge management
- Generative design and AI CAD modeling
- AI simulation
- Automated design review and DFM
- PLM and digital thread

The strongest entry point for this project is:

```text
自动设计审查和 DFM + 工程图自动化 + 本地知识库/规范库
```

These areas have clear inputs, explicit rules, and concrete deliverables, making them well suited to automation and easy to verify.

### 2.3 Incumbents Are Adopting AI, Leaving Vertical Opportunities

SOLIDWORKS has positioned AI CAD automation, Virtual Companions, and AURA/LEO as part of the design workflow to free engineers from repetitive work.

Autodesk Fusion emphasizes an integrated stack covering CAD, simulation, generative design, mesh editing, plastic part rules, and lifecycle management.

AutoCAD Mechanical 2026 highlights mechanical drafting automation, BOMs, parts lists, balloons, automated dimensioning, GD&T symbols, and standards-based annotations.

Assessment:

Incumbent roadmaps validate demand, yet incumbent suites lean general-purpose, enterprise-heavy, and subscription-locked. Our opportunity lies in:

- Local Windows workflows
- Regional mechanical drafting practices
- Standards-based engineering drawing review (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, while retaining `GB/T` as a secondary reference)
- SolidWorks + AutoCAD interoperability
- 3D printing and low-volume prototyping deliverables
- Direct invocation by AI agents

## 3. Competitive Landscape

| Product / Direction | Core Capabilities | Lessons for Us | Areas to Avoid Competing Head-On |
|---|---|---|---|
| SOLIDWORKS AI | Embedded AI, virtual assistants, workflow speedup | Confirms in-CAD AI assistants are a real trend | Do not build a full CAD kernel |
| Autodesk Fusion | CAD + simulation + generative design + lifecycle | Design-to-manufacturing integration is central | Do not build a full cloud CAD suite |
| AutoCAD Mechanical | Mechanical drafting automation, standard annotations, BOM | Drawing standards and auto-dimensioning are must-haves | Do not replace AutoCAD |
| Siemens Solid Edge 2D Drafting | 2D drawings, dimensioning, standards compatibility | 2D engineering drawings remain essential | Do not build a standalone 2D CAD app |
| DraftAid | Automated 2D manufacturing drawings from 3D models | Drawing automation is a sharp pain point | Do not restrict support to English/Western standards only |
| CoLab AutoReview | Design review, DFM, issue tracking, knowledge capture | Review enters enterprise workflows faster than generation | Do not start by building a large collaboration platform |
| Leo AI | CAD-aware knowledge management, engineering reuse | Engineering knowledge bases and past lessons add high value | Do not promise complex B-Rep AI semantics |
| Zoo.dev | Text-to-CAD, modern geometry kernel, API | Text-driven CAD is a growing trend | Do not build a proprietary geometry kernel |

## 4. Target Users

### 4.1 Primary Target Users

Independent mechanical designers, makers, small studios, automation equipment engineers, and 3D-printing prototyping teams.

Shared traits:

- Familiar with SolidWorks or AutoCAD
- Frequently design enclosures, brackets, mounting plates, panels, and heatsink housings
- Need rapid STL/STEP/DWG/DXF/PDF outputs
- Want to stop repeatedly drawing holes, chamfers, screw bosses, and engineering drawings
- Require standards-compliant drawings (this localized edition prioritizes **TCVN and ISO**, retaining `GB/T` as a secondary reference) and manufacturable deliverables

### 4.2 Secondary Target Users

Small-to-medium manufacturers, custom automation teams, and educational/training institutions.

Needs:

- Consistent drafting standards
- Fewer drawing errors from junior engineers
- Reusable template libraries and checklists
- Shorter turnaround from requirements to prototyping

### 4.3 Out-of-Scope Users (Not Prioritized Initially)

- Full PLM workflows for large automotive, aerospace, or defense enterprises
- Ultra-complex freeform surfacing and topology optimization
- Cloud-based multi-user collaborative CAD platforms
- Full CAD replacements for SolidWorks, NX, or CATIA

## 5. High-Frequency Mechanical Engineer Pain Points

| Pain Point | Concrete Symptoms | Automation Opportunity |
|---|---|---|
| Repetitive modeling of similar parts | Enclosures, brackets, panels, and mounting plates repeatedly resized | Parametric template library |
| Drawing annotation rework | Holes specify size without locating dimensions; overlapping dimension lines; leaders crossing views | Standards-based drawing review engine (prioritizing **TCVN and ISO**, with `GB/T` as secondary reference) |
| Unprintable 3D models | Walls too thin, holes not genuinely cut through, missing hole clearance compensation, insufficient assembly clearance | 3D printing manufacturability rule library |
| Tedious export and delivery | Separate manual exports for STL, STEP, DWG, DXF, PDF, and previews | One-click delivery package |
| Unreusable engineering experience | Rules known by senior engineers are never captured systematically | Rule library + project retrospectives |
| Unstable prompts | One-line prompts omit hole locations, tolerances, and materials | Form-based inputs + AI follow-up questions |
| Fragmented toolchain | SolidWorks for modeling, AutoCAD for drawings, manual file organization | Local task orchestration |

## 6. Current Project Assets

Existing assets:

- SolidWorks automation scripts
- AutoCAD automation subskill
- Engineering drawing generation experience
- Documented rules and lessons for holes, slots, and locating dimensions
- GitHub skill repository
- Initial MCP server prototype
- Sample and test scripts

Gaps:

- No user-facing task entry point
- No structured template library
- No formal drafting-standards rule library (prioritizing **TCVN and ISO**, retaining `GB/T` as a secondary reference)
- No systematic DFM / 3D printing rule library
- No stable schema for automated drawing review reports
- No project file management or run history
- No packaged Windows desktop shell

## 7. Product Positioning

Proposed product name:

```text
CAD 自动化交付工作台
```

One-line positioning:

```text
把机械工程师重复的建模、出图、开孔检查和交付文件整理，变成可复核的一键流程。
```

What it is NOT:

- Not a new CAD application
- Not a pure AI chatbot
- Not a cloud collaboration platform
- Not a toy that only renders attractive previews

What it IS:

- A local automation control plane for SolidWorks / AutoCAD
- A mechanical drawing standards checker (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, retaining `GB/T` as a secondary reference)
- A 3D-printing and prototyping delivery assistant
- A mechanical structure template library
- A task orchestrator combining AI, engineering rules, and CAD scripts

## 8. MVP Feature Recommendations

### MVP Goal

Enable the user to complete one real end-to-end task:

```text
做一个可 3D 打印的外壳，并输出符合中国机械制图习惯的工程图和交付包。
```

*(Note: In this localized edition, drafting outputs and review rules prioritize **TCVN (Vietnamese Standards) and ISO**, while retaining `GB/T` conventions as a secondary reference.)*

### Must-Have Features

1. Project creation
   - Choose project type: 3D-printed enclosure
   - Set output directory
   - Upload reference image

2. Parameter form
   - Overall length, width, and height
   - Wall thickness
   - Fillets / chamfers
   - Display openings, connector ports, screw holes, ports/openings, and ventilation slots
   - Every hole/slot category must specify size, quantity, and locating datums

3. Model generation
   - Invoke SolidWorks scripts
   - Verify holes/slots are genuinely cut in geometry
   - Export STL / STEP / SLDPRT

4. Drawing generation
   - Invoke AutoCAD or SolidWorks Drawing
   - Output DWG / DXF / PDF / PNG
   - Default A3 or A4 drawing frame, title block, scale, and millimeter units

5. Standards review
   - Sheet size and title block
   - Hole/slot specifications, quantities, and locating dimensions
   - Overlaps among dimension lines, leaders, and text
   - Verification that openings actually exist in geometry
   - Baseline 3D-printing wall-thickness / hole-diameter / clearance rules

6. Delivery package
   - Unified archiving of output files
   - Generate `review.json`
   - Generate `README_交付说明.md`

### Deferred Features

- Cloud accounts
- Multi-user collaboration
- PLM / PDM integration
- Topology optimization
- Complex freeform surfacing
- Automated quoting
- Fully autonomous LLM generation of arbitrary CAD

## 9. Drawing Standards Priority Tiers

### P0 Hard Rules

- Every hole, slot, connector cutout, port, screw hole, and boss must have size, quantity, and locating dimensions.
- Long leader lines must not replace key dimension chains.
- Leaders must not cross views, holes, centerlines, or the title block.
- Dimensions must not collide with lines, text, or the sheet border.
- Drawings must include a frame, title block, units, scale, view labels, and technical notes.
- Openings on 3D-printed parts must be genuinely cut in the 3D model, not merely drawn symbolically on the 2D drawing.

### P1 Recommended Rules

- Prefer hole/slot tables in crowded regions.
- Express symmetric holes using centerlines and datum dimensions.
- Express repeated holes with `n×Φd` or a hole table instead of scattered callouts.
- Provide manufacturing clearance compensation suggestions for 3D-printed hole diameters.
- Provide recommended clearances for mating fits.

### P2 Enhanced Rules

- Automatically detect under-defined sketches.
- Automatically detect thin walls, sharp corners, overhangs, and tiny isolated islands.
- Automatically detect non-manifold edges, flipped normals, and open edges in STL meshes.
- Automatically generate DFM recommendations.

## 10. Initial 3D Printing Rule Library

Prioritize FDM first, as it is most common among individual users and small workshops.

Recommended defaults:

| Item | Initial Recommendation |
|---|---|
| Structural wall thickness | Prefer >= 1.6 mm |
| Minimum printable wall thickness | At least 0.8–1.0 mm depending on nozzle |
| Screw boss outer diameter | At least 2–2.5× screw diameter; refine later with M2/M3/M4 templates |
| Standard hole compensation | FDM holes tend to print undersized; offer 0.2–0.4 mm allowance option |
| Assembly clearance | Reserve 0.2–0.5 mm for slip/press-in fits |
| Horizontal circular holes | Prompt for teardrop profile or supports |
| Tight-tolerance small holes | Prompt for post-drilling or reaming |

All rules must remain configurable rather than hard-coded, since printer, material, nozzle, and slicer settings change final values.

## 11. Recommended Software Form Factor

Start with a local Windows desktop app rather than a cloud service.

Recommended stack:

```text
PySide6 桌面软件 + Python 自动化脚本 + 本地项目目录 + GitHub 更新 skill
```

Rationale:

- No server hosting costs
- Direct access to SolidWorks / AutoCAD COM APIs
- Reuses existing Python scripts directly
- Straightforward packaging into an `.exe`
- Data stays on the user's machine, protecting engineering file privacy

For a more polished UI later, consider:

```text
Tauri/Electron + 本地 Python 后端
```

## 12. MVP Validation Metrics

Prioritize proving real time savings and rework reduction over feature count.

Suggested targets:

| Metric | Target |
|---|---|
| Enclosure modeling to STL | Under 10 minutes |
| Initial engineering drawing draft | Under 5 minutes |
| Missed hole/slot callout rate | 0 missed P0 rules |
| Printability checks | At least wall thickness, hole diameter, real cuts, and clearance |
| Rework rounds | Reduced from multiple rounds to <= 1 round |
| User input mode | Form-primary, prompt-assisted |

## 13. 90-Day Roadmap

### Weeks 1–2: Product Skeleton

- Create `apps/desktop` or a standalone desktop project
- Build the PySide6 main window
- Implement project creation, output directory selection, and log panel
- Read local skill status and version

### Weeks 3–4: Enclosure Template

- Build the 3D-printed enclosure parameter form
- Connect SolidWorks modeling scripts
- Output STL / STEP / SLDPRT
- Add real-hole cut verification

### Weeks 5–6: Drawings and Review

- Connect AutoCAD / SolidWorks Drawing generation
- Output DWG / DXF / PDF / PNG
- Implement P0 drawing standards checks
- Generate `review.json`

### Weeks 7–8: Delivery Package

- One-click deliverable archiving
- Generate delivery notes
- Add project history list
- Visualize failure causes

### Weeks 9–12: Template Expansion

- Mounting plate template
- Bracket template
- Heatsink enclosure template
- Screw boss / heat-set insert template
- Configurable 3D-printing rule library

## 14. Risks

| Risk | Mitigation |
|---|---|
| SolidWorks / AutoCAD COM instability | Serialize job execution; add retries and timeout recovery |
| Incomplete user dimensional inputs | Enforce strict form constraints + AI follow-up questions |
| Hard to fully automate drawing standards | Implement P0 rules first; keep human preview review |
| Varying company drafting conventions | Configurable rule library; this localized edition prioritizes **TCVN and ISO** as default, retaining `GB/T` as a secondary reference |
| Wide variation in 3D printing parameters | Default recommendations + per-user printer profiles |
| Scope creep | Stay focused on high-frequency enclosure, bracket, and mounting-part templates |

## 15. Next Step

Write a product prototype specification before diving into implementation.

Planned deliverable:

```text
docs/product-mvp-spec.md
```

Contents:

- Home page information architecture
- First task wizard: 3D-printed enclosure
- Parameter field definitions
- Output file structure
- `review.json` schema
- P0 standards checklist
- Initial UI wireframes

Completing this specification before coding the PySide6 prototype will keep product direction grounded.

## 16. Research Sources

- Research and Markets: Computer Aided Design CAD Software Market Report 2026  
  https://www.researchandmarkets.com/reports/5972859/computer-aided-design-cad-software-market-report
- Chyxx (Zhiyan Consulting): 2025 China Industrial R&D Design Software Market Size, Value Chain, Competitive Landscape, and Trends  
  https://www.chyxx.com/industry/1217927.html
- SOLIDWORKS: AI Product Design with Embedded AI Tools  
  https://www.solidworks.com/product/solidworks-design/ai-overview
- SOLIDWORKS: AI CAD Tools for Workflow Optimization  
  https://www.solidworks.com/solution/solidworks-ai-cad-tools-workflow-optimization
- Autodesk Fusion: Design AI solutions  
  https://www.autodesk.com/solutions/generative-design-ai-software
- Autodesk AutoCAD Mechanical Toolset  
  https://www.autodesk.com/products/autocad/included-toolsets/autocad-mechanical
- Siemens Solid Edge 2D Drafting  
  https://resources.sw.siemens.com/en-US/download-free-2d-cad-software/
- CoLab Software: Best AI Tools & Agents for Mechanical Engineers 2026  
  https://www.colabsoftware.com/ai-tools-for-mechanical-engineers-guide
- CoLab Software: Design for Manufacturability Reviews  
  https://www.colabsoftware.com/use-case/design-for-manufacturability
- DraftAid: AI CAD Drawing Automation  
  https://draftaid.io/
- Zoo.dev: Zookeeper and Text-to-CAD  
  https://zoo.dev/zookeeper
- Leo AI: Engineering-grade AI for mechanical engineers  
  https://www.getleo.ai/
- Secondary Reference (`GB/T` — National Standards Open Platform): GB/T 4458.4-2003 Mechanical Drawings — Dimensioning  
  https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=08588A5F3FE19F16B9EE8D5D87E064D5
- Secondary Reference (`GB/T` — National Standards Open Platform): GB/T 4457.4-2002 Mechanical Drawings — General Principles of Presentation — Lines  
  https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=5B789BF5B537CF6F89B5D743DA71D883
- Secondary Reference (`GB/T` — National Standards Open Platform): GB/T 10609.1-2008 Technical Drawings — Title Blocks  
  https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=0F8577CB9AB82D5819048A87920CABAB
- JLC3DP: 3D Printing Design Guideline  
  https://jlc3dp.com/help/article/3d-printing-design-guideline
- Prusa Knowledge Base: Modeling with 3D printing in mind  
  https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135
- Formlabs: Minimum Wall Thickness for 3D Printing  
  https://formlabs.com/blog/minimum-wall-thickness-3d-printing/
