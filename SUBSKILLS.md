# SolidWorks Automation Subskill Matrix

This repository uses a "monorepo + multi-subskill" layout. The root skill `solidworks-automation` provides SolidWorks connection, document management, modeling APIs, export, self-review, and the MCP Server; domain-specific capabilities reside under `subskills/`, where each subskill is self-contained with its own `SKILL.md`, `README.md`, `manifest.yaml`, scripts, references, and examples.

This structure follows multi-skill repository conventions: the root README serves as the main entry point, installation guide, capability map, and invocation router, while each subskill owns a stable domain workflow.

## Skill Index

| Subskill | Status | Purpose | Entry Point |
|---|---|---|---|
| `solidworks-vibecad` | experimental | Natural language requirements -> parametric design plan, manufacturability rule checks, execution summary, review gates | `subskills/solidworks-vibecad/SKILL.md` |
| `solidworks-fillet-chamfer-cnc` | stable | CNC mounting brackets, parameter/collision pre-checks, semantic edge selection, bounded dimension fallback, holes/slots, and filleted pockets | `subskills/solidworks-fillet-chamfer-cnc/SKILL.md` |
| `solidworks-threaded-holes` | stable | M3-M12 threaded holes, tap drill holes, hole-edge Chamfers, thread properties, and STEP export | `subskills/solidworks-threaded-holes/SKILL.md` |
| `solidworks-engineering-drawing` | pilot | GB/T first-angle projection part/assembly drawings, dimension chains, hole tables, BOM, PDF/BMP evidence, and manufacturing delivery review | `subskills/solidworks-engineering-drawing/SKILL.md` |
| `autocad-automation` | stable | AutoCAD DWG/DXF 2D drafting, line-art vectorization, layer/text/dimension handling, export, and drawing self-checks | `subskills/autocad-automation/SKILL.md` |

## Recommended Routing

```text
自然语言需求
  -> solidworks-vibecad
  -> 结构化 design_plan.json
  -> 按零件类型路由到专项子技能
  -> 工程图需求连接 solidworks-engineering-drawing
  -> 父技能 scripts/sw_*.py 执行 SolidWorks COM
  -> sw_review.run_review() 审查
```

## When to Use Which Subskill

### solidworks-vibecad

When the user says:

- "Parameterize this requirement"
- "Build a text-to-CAD workflow"
- "Codify domain knowledge base and prompt templates"
- "Don't model yet—produce a design plan first"

Use:

```text
subskills/solidworks-vibecad/SKILL.md
```

### solidworks-fillet-chamfer-cnc

When the user says:

- "CNC mounting bracket"
- "Connector block / bracket"
- "Many Fillets and Chamfers"
- "Weight-reduction pockets / straight slots / counterbore plate"

Use:

```text
subskills/solidworks-fillet-chamfer-cnc/SKILL.md
```

### solidworks-threaded-holes

When the user says:

- "M6 threaded hole"
- "Tapped hole"
- "Tap drill hole"
- "Hole Wizard / ThreadFeatureData / CosmeticThread"

Use:

```text
subskills/solidworks-threaded-holes/SKILL.md
```

### autocad-automation

When the user says:

- "Draw this in AutoCAD"
- "Generate/modify DWG or DXF"
- "Convert this line-art image into CAD"
- "Batch-check layers, text, blocks, and Xrefs"
- "Export native AutoCAD previews and review"

Use:

```text
subskills/autocad-automation/SKILL.md
```

### solidworks-engineering-drawing

When the user says:

- "Generate part drawing / assembly drawing / engineering drawing"
- "Create drawings per GB/T and first-angle projection"
- "Add dimension chains, hole tables, BOM, and title block"
- "Review whether an engineering drawing is ready for manufacturing delivery"

Use:

```text
subskills/solidworks-engineering-drawing/SKILL.md
```

This subskill can be linked on demand by the root skill, VibeCAD, hole/slot/CNC subskills, or the engineering orchestrator; other subskills do not need reverse dependencies on it.

Note: For standard "trace-image-to-CAD" final deliverables, keep only vectorized curves from the original image—do not retain hand-guessed outer contours, facial feature ovals, logo triangle lines, wave lines, placeholder text, or in-drawing review notes.

## Subskill Directory Convention

When adding a new subskill, maintain this layout:

```text
subskills/<skill-name>/
├── SKILL.md             # AI 调用入口和工作流
├── README.md            # 人类阅读入口
├── manifest.yaml        # 索引元数据
├── scripts/             # 可复用脚本
├── references/          # 实测经验、避坑和 API 说明
├── examples/            # 示例输入/输出
└── agents/              # 可选，不同客户端配置
```

## Quality Gates

Every subskill must document:

- Applicable and non-applicable scenarios.
- Which parent-skill `scripts/sw_*.py` modules are recommended.
- Stable strategies and fallback strategies for SolidWorks APIs.
- Output files and review requirements.
- Newly encountered pitfalls must be recorded under `references/`.
