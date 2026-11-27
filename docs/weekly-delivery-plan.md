# CAD Studio Weekly Delivery Plan

Each week commits only to a buildable, testable, and rollback-safe set of capabilities. Features that have not passed real CAD review remain marked as `pilot`, `reference_only`, or `not_implemented`.

| Phase | Goal | Acceptance Exit |
|---|---|---|
| Week 1 | Local installation discovery, reliability diagnostics, STL/GLB/OBJ/DXF preview foundation | Both CAD suites detected accurately; Python/Rust/frontend tests pass; non-empty preview pixel and narrow-viewport screenshot checks pass |
| Week 2 | Split project/chat/job/file/review modules to reduce `App.tsx` size | Project switching P95 < 150 ms; migration counts match; deleting a project does not delete CAD deliverables |
| Week 3 | SolidWorks parameter modification, batch export, properties/BOM, Pack and Go | Golden workflow live regression passes; artifact ledger rejects stale files |
| Week 4 | Drawing views/hole callouts, AutoCAD layer/dimension/frame checks, DXF layer preview | Headless DXF check passes; AutoCAD 2024 ActiveX native drawing live regression is currently `blocked` and must not be falsely reported as passing |
| Week 5 | Assembly checks, configuration family pilot, deliverable version diffing and regeneration | Capability gates, error codes, retries, and human review evidence complete |
| Week 6 | 20-run stability regression, Windows self-hosted CI, installer regression, v0.4 release | Zero duplicate CAD instances or orphan workers; golden workflow first-pass success rate reaches 90% |

## Week 1 Results

- Detected local `E:\Solidworks\SOLIDWORKS\SLDWORKS.exe` and `D:\AutoCAD 2024\acad.exe`; public desktop shortcuts and COM registrations unified into discovery.
- `cad-studio doctor` outputs product, version, source, and path; exported diagnostic bundles retain filenames only for path redaction.
- Three.js loads STL, GLB/GLTF, and OBJ on demand; read-only DXF covers `LINE`, `CIRCLE`, and `LWPOLYLINE`.
- STEP/IGES and DWG are not yet parsed directly in the browser and continue to rely on native preview exports from SolidWorks/AutoCAD; placeholders are never presented as real geometry.

## Week 2 Results

- `App.tsx` reduced from 3,968 lines to ~3,479 lines; project, job, chat, review, and deliverable views moved into dedicated component/domain modules so future CAD workflows no longer pile into a single file.
- Top-left project menu supports project search, archive/restore, duplicate project, rename, and double-confirmed deletion; duplication copies only project metadata and folder references, not jobs, chats, or CAD deliverables.
- Sidebar task queue supports bulk cleanup of terminal jobs; queued, running, and approval-pending jobs can never be bulk-deleted.
- SQLite preserves the legacy `app_state` snapshot while adding entity indexes for projects, conversations, messages, and jobs; automatic migration runs on first launch and `app_store_migration_status` reports whether source and index counts match.
- Project switching passed Playwright 1440×900 / 900×700 acceptance with zero console errors; measured `performance.measure("cad-studio.project-switch")` was ~18 ms, well below the 150 ms target.
- Verification results: frontend build passed, 15 Rust tests passed, 118 Python tests passed; real SolidWorks/AutoCAD artifact capabilities remain governed by the capability manifest and human review gates.

## Week 3 Supplemental Results

- SolidWorks 2024 part modeling, dimension modification, property readback, assemblies, BOM, and batch export passed live regressions.
- In early SW2024 regressions, native Pack and Go enumeration returned only the top-level assembly; the wrapper therefore retains dependency auditing and a fallback gate, prohibiting incomplete packages from being marked as successful deliveries.

## SolidWorks 2026 SP01.1 Upgrade Regression Results

- Local installation discovery and COM type libraries adapted to `E:\SolidWroks2026\SOLIDWORKS\SLDWORKS.exe`, recognizing revision `34.1.1`, `sldworks.tlb`, and Motion and Routing type libraries.
- Drawing regression generated 3 real views and 6 real dimension entities across three consecutive runs, with SLDPRT, SLDDRW, PDF, and non-empty previews all produced by the current run.
- Final Pack and Go code passed natively across three consecutive runs; each run output 1 SLDASM and 2 SLDPRTs, `document_count=3`, status codes `[0,0,0]`, `missing_dependencies=[]`, without using the staging fallback.
- `comtypes` fallback prefers attaching to an active instance and only exits instances explicitly created by the current run; zero orphan `SLDWORKS.exe` processes remained after the final two runs and teardown run.
- Overall `pack_and_go` maturity remains `pilot`: complex external references, Toolbox, configurations, suppressed components, and associated drawings do not yet have a consecutive regression matrix.

## Week 4 Supplemental Results

- DXF structural inspection schema 2.0 covers entity types, layers, bounding boxes, real `DIMENSION` entities, hole centers/diameters, drawing frames, and title-block candidates; rendered PNG outputs require non-empty pixels.
- AutoCAD 2024 completed COM version detection, but dynamic proxies for `Documents.Count`, `Documents.Add`, `Layers`, and `SelectionSets.Add` remain unstable. Native DWG drafting is marked `not_implemented` in `capabilities.yaml` (retaining interactive troubleshooting mode only); the headless DXF backend is marked `pilot`.

## Week 5 Results

- Assembly interference check returns a structured `pass/warn/blocked` report with counts, items, and human review gates.
- Configuration-reading pilot returns the configuration list, active configuration, and limitations; batch modification of design tables is not yet enabled.
- Deliverables use SHA-256 snapshots to compare `added`/`removed`/`changed`/`unchanged`; regeneration requests preserve prior artifacts, prohibit overwriting, and require review.

## Week 6 Results

- Added `scripts/stability_regression.py` to validate connection, cancellation, and exit-ownership constraints across 20 simulated lifecycle runs.
- Added `scripts/release_check.py` for pre-release validation of UI/Tauri/Cargo version parity, unique capability IDs, and required file completeness.
- Added `.github/workflows/windows-cad-regression.yml` to run live regressions exclusively on self-hosted Windows runners with SolidWorks/AutoCAD preinstalled; public GitHub runners never fabricate CAD pass results.

## Next-Phase 4-Week Expansion Results

- Drawing structural review returns sheets, views, real dimensions, tables, drawing-frame templates, and human review fields; BOM adds traceability links across models, drawings, and review reports.
- Automation Job 2.0 supports `drawingEvidence`, `bomEvidence`, `reviewFindings`, and `artifactRelations`; the worker maps domain evidence accurately to `blocked`, `failed`, or `review_required`.
- The Delivery page groups artifacts by models, drawings, BOM, previews, and review reports; legacy Job 1.0 records continue to read via original fields.
- AutoCAD backend statuses remain independent: headless DXF `pilot`, allowlisted scripts `pilot`, COM currently `blocked`; .NET SDK 8 was installed in the current user directory and the AutoCAD 2024 allowlisted plugin passed live verification via `NETLOAD`, real DWG save-and-reopen, PDF/PNG export, and entity/layer/dimension inspection, promoting the .NET backend to `pilot`.
- .NET regression permits only fixed commands `CADSTUDIOPROBE/CADSTUDIOCREATE` and does not expose arbitrary AutoLISP, SCR, or C# execution; AutoCAD 2025–2026 and signed desktop plugin deployment require subsequent verification.
- Added comprehensive regression `tests/cad_studio_weekly_regression.py` and SolidWorks live drawing regression `tests/solidworks_week4_drawing_regression.py`; real CAD runs only when explicitly invoked with `--real-cad` or on self-hosted CI.

## Follow-up Phase 1 Results: Versioned Retry and Delivery Gate

- Before re-running a terminal job, a read-only `runHistory` snapshot is saved (retaining up to the latest 20 runs); prior artifacts, errors, drawing/BOM evidence, and review records remain visible in-app and are never recursively copied.
- `retryPolicy` explicitly records the previous run ID, restart point, running only the failed stage and downstream stages, preserving old artifacts, and forbidding overwrites; the worker reuses the prior engineering DAG and enforces versioned output in the execution prompt.
- The Delivery Center determines `ready/review_required/blocked/failed/incomplete` uniformly from current-run artifacts, domain evidence, human review, and blocking reasons, no longer equating file existence or a sidebar "Completed" badge with delivery readiness.
- The Delivery page adds valid current-run artifact count, version history, SHA-256 change summary, artifact traceability, and AutoCAD backend diagnostics; model, drawing, and BOM groups share a single preview pane to prevent duplicate heavy renders on narrow windows.
- `ai_team/delivery-gate-e2e.cjs` verifies the 1440×900 pending-review state and 760×900 approved state in real Chromium with no horizontal overflow, no duplicate previews, and ensures "Ready for Delivery" appears only after human approval.

## Weeks 7–8 Results: Dual-Backend Headless Geometry

- `scripts/headless_occt_service.py` invokes OCP in an isolated subprocess to genuinely write STEP, IGES, BREP, STL, OBJ, and GLB and read back validity, volume, bounding box, and topology statistics; current golden samples cover box, cylinder, boolean union, and cylindrical hole cut.
- `scripts/headless_cad_writer.py` preserves `.cadstudio.json`, versioned outputs, SHA-256 hashes, and the `producedThisRun` ledger; missing OCP or unsupported features return `pilot/blocked` rather than writing partial meshes masquerading as complete solids.
- 7 OCP/open-format regressions and versioned no-overwrite regressions passed; complex surfaces, sheet metal, weldments, and parametric features remain unimplemented.

## Weeks 9–12 Results: Headless 2D Writing

- DXF writing now includes `OUTLINE/HOLES/CENTER/DIMENSION/FRAME/TITLE/TEXT` layers, real linear/diameter `DIMENSION` entities, hole centerlines, and optional A4/A3/A2/A1 drawing-frame and title-block fields (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, while retaining `GB/T`-style layouts as a secondary reference).
- SVG, PDF, and PNG render by default from the same DXF via `ezdxf`/`matplotlib`, falling back to a clearly labeled simplified renderer when dependencies are missing; DWG is not written.
- 10 regressions covering 2D writing, DXF inspection, and `PreviewScene` passed; frame layout, font rendering, and final manufacturability still require visual review by an engineer, keeping the capability at `pilot`.

## Weeks 13–16 Results: JS Preview v1

- `ModelViewport` supports on-demand Three.js loading for GLB/GLTF/STL/OBJ, standard views, orthographic/perspective toggle, selection, on-demand rendering, and resource disposal; switches to manifest PNG fallbacks when WebGL is unavailable or model decoding fails.
- `DxfViewport` parses DXF/`PreviewScene` in a Worker with layer toggles, entity selection, dimensions/text, and Evidence references; `.scene.json` is integrated into frontend format routing.
- Real Chromium E2E covers desktop, 760px narrow, and 390px mobile viewports, verifying canvas pixels, zero horizontal overflow, source badges, and fallback images; an independent 20 MB / 30 FPS performance benchmark has not yet been completed and is not claimed.

## Weeks 17–20 Results: DXF Inspector and Demo Boundaries

- Added `scripts/dxf_preview_scene.py` for read-only allowlisted parsing of `LINE/CIRCLE/ARC/LWPOLYLINE/POLYLINE/TEXT/MTEXT/DIMENSION`, capped at 50 MB and 200,000 entities; unsupported entities log warnings only and never execute scripts.
- Added CLI command `cad-studio preview-dxf` and MCP tool `cadstudio_build_dxf_preview_scene`; output must be a new `.scene.json` file and refuses to overwrite existing files.
- The Help page includes seven fixed demo scenarios (mounting plate, bracket with holes, CPU enclosure, small assembly, standard drawing frame — prioritizing TCVN/ISO with `GB/T` as secondary reference, sample FEA contour, and sample Routing path), all tagged `demo-showcase/isDemo` and excluded from delivery decisions.
- E2E verifies backend Scene JSON, raw DXF Worker, all seven demo scenarios, and WebGL PNG fallback; the FEA contour and Routing path are educational demos only—real solving and native Routing must pass the new gates and return `blocked` when dependencies are unmet.

## Week 21 Hardening: DFM, Routing, FEA, and Complex Geometry Gates

- DFM adds vendor profiles, unit normalization, B-Rep evidence binding, and anti-spoofing checks; passing rules still yields `review_required`.
- Routing adds neutral review of endpoints/segments/lengths/bend radii/collision clearances/support spacing/Routing BOM; SW2026 detects the Routing type library, but native writing remains `blocked` without add-in and license evidence.
- FEA adds FEA 1.0 Schema, CalculiX/Elmer preflight checks, and allowlisted CalculiX inputs; CalculiX 2.23 genuinely solved a constrained linear-static sample and parsed displacement, stress, and convergence evidence.
- Complex surfacing/molding adds structured gates; OCP 7.9.3.1.1 genuinely generated and reopened STEP/BREP for a constrained closed ruled Loft, while smooth Lofts, surface continuity, and mold tooling remain incomplete.
- Both CLI and MCP added allowlisted entry points (`check-routing`, `routing-preflight`, `fea-preflight`, `prepare-fea`, `run-fea`, `review-advanced-geometry`, `create-ocp-loft`) included in protocol validation.

## Weeks 1–20 Audit Conclusion

- Scope backed by real code and automated evidence: project/delivery gates, open-format geometry, basic 2D drawing structure, Preview Manifest/Scene, dual desktop/Skill/CLI/MCP entry points, browser preview fallbacks, DFM profiles/B-Rep evidence, neutral Routing review, constrained CalculiX linear-static solving, and constrained OCP closed ruled Loft.
- Scope still requiring self-hosted live CAD or human review: final visual quality of SolidWorks drawings/BOM, native AutoCAD DWG, smooth/continuous complex surfaces, FEA mesh convergence and safety sign-off, native SOLIDWORKS Routing writes, and the 20 MB / 30 FPS performance target.
- Capabilities that have not passed these regressions are never shown as completed and are never accepted by the delivery gate as current-run artifacts.
