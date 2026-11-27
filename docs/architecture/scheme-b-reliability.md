# Scheme B: Reliability Fixes and Acceptance for the Existing Architecture

> **Historical Metric Note (2026-10-27)**: This document is the 2026-10-08 acceptance record; its scenario counts (37 scenarios,
> 10/10 nominal, 21/37 raw completion ratio) reflect the metric scope **at that time** and are preserved verbatim for traceability.
> The current scenario suite has expanded to **43 scenarios** (12 nominal + 31 robustness, baseline v4)—refer to
> [`v2-evaluation.md`](v2-evaluation.md) for current figures and do not cite the counts below as current metrics.

2026-10-08; support and native acceptance target SolidWorks 2026. Implemented on baseline `592e655`, preserving community PR #21 commit history and fixing execution and delivery contracts across related issues.

## Changes and Root Causes

| Issue | Root Cause | Fix and Acceptance Boundary |
|---|---|---|
| Failed executions still reported success | Non-exception returns were treated as success; Core finished before final Review | Required `false` flags fail immediately and unknown evidence blocks; required `FAIL` in Review cannot be overridden by top-level `PASS`; `completed` requires `PASS` with `manual_review_required=false`; Queue and Core terminal states unified |
| #7 Sketches missing design parameters | Geometry coordinates were mistaken for constraints and dimensions; no save-and-reopen verification | Added dimensions and relations to basic circles/rectangles, reading back fully defined state, dimensions, and `Fix`; review checks sketch consumption by features; complex sketches still need design parameters and human review |
| #14 Unstable patterns | Incorrect native member/parameter signatures and unreliable parent-feature/direction-entity selection | Exact parent feature, real parallel straight edge, 20-parameter linear pattern; explicit axis for circular patterns; halt immediately on selection failure |
| #5/#15 Process and document lifecycles | `Dispatch` does not guarantee a new process; unready ROT caused duplicate launches; documents accumulated over time | Read PID/actual Revision and wait for existing instances; clean up only run-registered documents and confirmed run-owned empty instances; default 8-document budget; block creation when document list is unreadable |
| #20/#22 Remote clients only received local paths | `stdio`-only transport; default HTTP Host check failed remote addresses; local paths cannot transfer remote file contents | Added optional HTTP transport to the same MCP with explicit Host/Origin and Bearer auth; reused Ledger for opaque artifact IDs returning PNG content blocks, raw resources, or bounded chunks verified by SHA-256 |
| #12 Missing injection-molding DFM entry | Process allowlist and rule dispatch lacked injection molding | Added `injection_molding` reusing `NeutralCadDocument`, profiles, and reports; screens declared draft angles, rib thickness, wall transitions, undercut plans, gates, and ejector/cooling clearances |

Retained existing Worker, Queue, Reviewer, Artifact Ledger, Policy Gate, and startup mutex. Recovery still emits decisions only. All 60 original MCP tools match baseline names and complete Input Schemas; added `cadstudio_read_artifact` for 61 tools total. Default transport remains `stdio`, with HTTP as an optional transport in the same process.

## Verification Results

- Full Windows / Python 3.12 pytest: 810 passed, 0 skipped, 0 failed, 0 warnings; Skill self-check passed; MCP validated 61 tools; release consistency check passed with 217 bundled runtime files.
- With `pythoncom`, `win32com`, and `comtypes` imports disabled, Core/Eval: 125 passed.
- 37 deterministic scenarios derived from `golden-workflows.yaml`; baseline v3 nominal 10/10, warning classified under guardrail and blocked, raw completion ratio 21/37 (diagnostic only), 0 false-success leaks.
- SolidWorks 2026 SP1.1 / Revision 34.1.1: actual B-Rep vs. analytical volumes matched for 3-hole linear and 4-hole circular patterns; after save and reopen, sketches retained dimensions, had no `Fix` constraints, and were consumed by features; changing thickness 8→10 mm preserved hole diameters and centers.
- Within the same live CAD test instance, the document budget blocked excess creation, Session exit closed only run-owned documents while preserving simulated unsaved user documents and processes, and the test instance cleaned itself up afterward.
- Native model exported STEP over HTTP and retrieved via MCP resource: 31,651 bytes matching SHA-256 `87388f90be31e299eb4d4e3c6dd12e4310d690ab08c16fe1be40552b10eb9ae2`; BMP converted to PNG content block via read-only tool and visually confirmed as the 3-hole model. Review remained `review_required`.
- Standalone HTTP protocol tests verified handshake, tool discovery, 401 auth, invalid Host/Origin rejection, PNGs, and binary resources; injection-molding rules have separate live CLI disk-write tests.

## How to Run and Verify

From the repository root using Python 3.12 with dependencies installed:

```powershell
python scripts/sync_bundled_skill.py
python -m pytest -q
python scripts/validate_skill.py
python scripts/validate_mcp.py
python scripts/release_check.py
python tests/evals/runner.py
```

Live-machine testing requires no active user SolidWorks instance and a non-existent output directory:

```powershell
python tests/solidworks_reliability_b_regression.py --output C:\cad-test\reliability-b-2026
```

`report.json` records volumes, hole positions, sketch evidence, and document cleanup results. This script is excluded from default pytest so CI without SolidWorks never fabricates native acceptance. See [`../../mcp-server/README.md`](../../mcp-server/README.md) for HTTP deployment and artifact retrieval steps.

## Known Limitations

- Under current scope, older SolidWorks versions are no longer scheduled for compatibility work or live verification; retained defensive COM logic is not a legacy-version support commitment.
- Live-machine evidence is limited to the explicit scenarios above and does not guarantee zero crashes across all complex parts, third-party add-ins, or heavy workloads.
- Injection molding remains a `pilot` declarative rule screen; it does not automatically detect full B-Rep draft/undercuts or run moldflow, and passing rules still require engineering review. Thresholds must be declared by the user/process/supplier rather than treated as universal material certifications.
- HTTP acceptance used a local server with remote Host headers and a real MCP client; cross-machine networking, firewalls, TLS proxies, input uploads, and concurrent CAD writes are out of scope.
- Chunked large-file reads verify content per chunk for delivery retrieval; large-file uploads and resumable uploads are not implemented.
- Subsequent 2026-10-08 increments adapted PRs #23/#24/#25 to add fallback process ownership, isolated Pack and Go, health checks, load diagnostics, downloads, and desktop boundaries; see [`remaining-pr-increments.md`](remaining-pr-increments.md).
