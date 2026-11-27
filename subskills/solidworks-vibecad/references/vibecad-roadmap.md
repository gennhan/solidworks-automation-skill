# VibeCAD Engineering Roadmap

## Strategic Direction

The value lies not in "having an LLM improvise a snippet of SolidWorks code on the fly", but in codifying repetitive mechanical design into:

```text
行业知识库 + 参数 schema + 提示词模板 + 稳定 API 封装 + 自动审查
```

The LLM interprets intent and fills in parameters; SolidWorks APIs provide deterministic execution; the knowledge base enforces engineering soundness; and the review pipeline catches false positives.

## Phase 1: Planning Closed Loop

Completed:

- CNC mount example brief
- Parametric design-plan JSON
- Initial manufacturing-rules knowledge base
- LLM planning prompt template
- SolidWorks execution outline
- JSON and Python syntax validation

Next additions:

- More part families: connector blocks, L-brackets, shafts, sheet-metal enclosures
- More standard-component rules: bearings, couplings, motor flanges, countersunk screws, dowel pins
- Stricter schema validation: dimensional ranges, hole spacing / edge distance, process constraints

## Phase 2: Live SolidWorks Executor

Prioritize building the `cnc_mount` executor:

1. Run `sw_preflight.py`.
2. Read `design_plan.json`.
3. Create a new Part via `SolidWorksSession()`.
4. Create the baseplate, holes, pockets, Fillets, and Chamfers per the plan.
5. Save `SLDPRT` and export `STEP`.
6. Call `sw_review.run_review()`.
7. Read the review report; if it fails, automatically degrade and retry.

Key principles:

- Every long-parameter SolidWorks API call must check its return value.
- All millimeter-to-meter unit conversions must go through `sw_connect.mm()`.
- Fillet/Chamfer edge selection must prefer object-based `edge.Select2()`.
- Threaded holes must guarantee tap-drill geometry, hole-mouth Chamfer, and custom properties first.

## Phase 3: Deepening the Knowledge Base

Prioritize capturing these high-frequency rules:

- M3/M4/M5/M6/M8/M10 coarse/fine pitches and tap-drill diameters
- Recommended clearance, counterbore, and countersink dimensions for screws
- CNC minimum wall thickness, minimum Fillet radius, and default Chamfer values
- Sheet-metal bend radius, K-factor, and bend allowance
- Bearing-housing bores, tolerance fits, and retaining-ring grooves
- Motor mounting bolt patterns and flange standards

## Phase 4: Interactive Entry Points

Target interfaces include:

- CLI: generate a plan and build the model from a single brief
- MCP: let Codex/Claude invoke SolidWorks through allowlisted tools
- Local lightweight Web UI: enter requirements, tune parameters, and inspect review previews
- Template library: save verified cases as reusable design templates

## Metrics

- Reduction in repetitive modeling time
- First-pass modeling success rate
- Automated review pass rate
- Number of manual revisions
- Template reuse count
- Rate at which failure causes are fed back into the knowledge base
