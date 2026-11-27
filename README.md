# SolidWorks Automation Skill

**AI Skill + MCP toolkit for reliable desktop CAD automation.**

Enables agents such as Codex, Claude, and Cursor to drive real CAD software via natural language with execution verification and tracing.

> Tool success is not treated as task success.

A successful tool call does not mean the task is genuinely complete; tasks requiring review are verified before delivery.

The current release is **v2.2.0**. This release delivers real-time SolidWorks execution previews, AutoCAD Chinese font support and DXF drafting check reports, plus improvements to Codex read-only permissions, Rib features, optional instance-attach fallback, and hole failure diagnostics. Engineering stage review remains in place. The Skill ZIP, MCPB, and CAD Studio installer and portable builds share the same runtime version. See the [v2.2.0 Release Notes](docs/releases/v2.2.0.md) for downloads and upgrades.

CAD Studio uniformly verifies across production executors that delivered files were newly created or modified during the current run; stale files are rejected, and insufficient evidence transitions to pending review. See [Current-Run Delivery Freshness Gate](references/delivery-freshness.md) for scan scope, compatibility, and validation methods.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Release](https://img.shields.io/github/v/release/wzyn20051216/solidworks-automation-skill)](https://github.com/wzyn20051216/solidworks-automation-skill/releases)
[![GitHub Stars](https://img.shields.io/github/stars/wzyn20051216/solidworks-automation-skill?style=flat)](https://github.com/wzyn20051216/solidworks-automation-skill)
[![MCP](https://img.shields.io/badge/MCP-stdio--server-blue)](mcp-server/README.md)
[![CI](https://github.com/wzyn20051216/solidworks-automation-skill/actions/workflows/windows-release.yml/badge.svg)](https://github.com/wzyn20051216/solidworks-automation-skill/actions/workflows/windows-release.yml)

```text
User → Agent (Codex / Claude / Cursor) → Skill / MCP → Execution Core → CAD → Artifacts + Evidence
```

The AI handles intent understanding, API lookup, and step planning; the Execution Core ensures traceable, verifiable, and recoverable execution.

---

## See It In Action

<p align="center">
  <img src="assets/showcase/solidworks-engineering-drawing-demo.gif" alt="Code-driven SolidWorks generating a complex test part and GB/T engineering drawing" width="900">
</p>

A real workflow: natural language request → Agent invokes Skill → SolidWorks generates native `SLDPRT + SLDDRW` → exports PDF → automatically reviews dimensions and evidence.

| Case | Capability | Status |
|---|---|---|
| [M6×1 Physical Threaded Hole](subskills/solidworks-threaded-holes/README.md) | Metric Tap Thread with post-rebuild readback | `verified` |
| [CNC Multi-Fillet/Chamfer Mounting Bracket](subskills/solidworks-fillet-chamfer-cnc/README.md) | Semantic edge selection, variable-radius, face/full-round/setback Fillets | `stable` |
| [Standard Involute Spur Gear](references/gears.md) | Solid driven by module / tooth count / pressure angle | `pilot` |

---

## Prerequisites

| Item | Requirement | How to Check |
|---|---|---|
| OS | Windows 10/11 x64 | Native `SLDPRT` / `SLDASM` / `SLDDRW` requires SolidWorks COM; other OSes support open-format capabilities only |
| Python | 3.10+ (local live-machine acceptance uses 3.12) | `python -V` |
| Node.js | 20+ (workbench, MCP registrar, and Skill installer) | `node -v` |
| Git | Any recent version (installer fetches and updates the repo via `git clone` / `git pull`) | `git --version` |
| SolidWorks | Locally installed and licensed for native modeling; check [verified versions](capabilities.yaml) per capability | `python scripts/cad_doctor.py` |
| AutoCAD | Optional; required only for the DWG/DXF subskill | — |

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
# 只有开放格式（OCCT）能力才需要：
python -m pip install -r requirements-occt.txt
```

Read-only environment diagnostics (will not open or close CAD):

```powershell
python scripts/cad_doctor.py           # 发现的安装路径、版本、COM 注册状态
python scripts/sw_capability_probe.py  # 类型库与能力清单
```

Templates and material libraries are **auto-detected by default**—no hardcoded paths are needed. Only non-standard installation locations require
[`config/runtime.example.json`](config/runtime.example.json) and `SOLIDWORKS_TYPELIB_DIRS`,
see [`config/README.md`](config/README.md).

---

## Quick Start

Choose **any one** of the three entry points—you do not need to run them simultaneously.

### Option 1 — Skill

```powershell
npx github:wzyn20051216/solidworks-automation-skill --target claude
```

This command fetches this repository and executes `install.js` at the root (the `bin` entry point in `package.json`).

**Default behavior (safety-first, since 2026-10-28)**:

- Installs only into clients whose skills directory **already exists** (`.agents` / `.claude` / `.codex` / `.cursor` / `.openclaw`);
  if none are detected, it **will not create directories for you**, and will prompt you to specify `--target` explicitly.
- If the target directory already exists but is **not a git checkout of this repository** (manually placed, extracted, or from another source),
  it **refuses to install and deletes no files**.
- Directories installed from this repository are updated via `git pull --ff-only`; if fast-forward fails, it **only reports and does not delete**.
- Automatically installs Python dependencies by default; on Windows without Python 3.10+, it attempts to install Python 3.12 for the current user via winget. Reports a prompt on failure; disable with `--no-install-deps`.
- Refuses non-Windows platforms by default (SolidWorks COM is unavailable); pass `--allow-non-windows` if you specifically need open-format capabilities.

| Option | Purpose |
|---|---|
| `--target claude,codex` | Install to specified clients; `all` targets all supported clients |
| `--dry-run` | Print planned actions only without writing to disk |
| `--install-deps` | Install `requirements.txt` + `mcp-server/requirements.txt` (default) |
| `--no-install-deps` | Skip automatic Python and Python dependency installation |
| `--no-register-mcp` | Skip MCP config registration (registered by default; backs up to `.bak-<timestamp>` before overwriting) |
| `--force-reinstall` | Rename old directory to `.bak-<timestamp>` before reinstalling (**does not delete**) |

Installation uses `git clone --depth 1`, fetching only the working tree without full history. The full working tree is ~13 MB,
of which `apps/` (desktop source code, ~6 MB) is not required for Skill runtime.
If `npx` is unavailable in your network environment, clone via Option 2 below and run `node install.js`.

### Option 2 — MCP

Windows desktop clients supporting MCPB can import the standard `.mcpb` extension from the releases page. If the current release does not yet attach this file, you can build it from a Git checkout. See [MCPB Extension Guide](mcp-server/README.md#windows-mcpb-扩展) for initial setup, `uv` preparation, and build instructions.

```powershell
git clone https://github.com/wzyn20051216/solidworks-automation-skill.git
cd solidworks-automation-skill
python -m pip install -r requirements.txt -r mcp-server/requirements.txt
node mcp-server/register_all_ai_mcp.js --help          # 查看全部参数
node mcp-server/register_all_ai_mcp.js --clients codex,claude-code,cursor
```

The registration script writes MCP configuration for the target clients and creates a `.bak` backup beforehand; add `--strict` to exit non-zero if any client fails.

### Option 3 — CAD Studio Desktop

Download the Windows installer from [GitHub Releases](https://github.com/wzyn20051216/solidworks-automation-skill/releases).

When the desktop app launches its local executor on Windows without a usable Python 3.10+, it attempts to install Python 3.12 for the current user via winget and displays an error if installation fails. Environment diagnostics remain read-only. SolidWorks must be installed and licensed separately by the user; 7-Zip, Python packages, and verifiable local API Help required for API lookup are provisioned on demand—see [`references/api-lookup.md`](references/api-lookup.md) for details.

> **Choose one entry point. You do not need to run all three.**

| Entry Point | Best For | Requires GUI | Typical Usage |
|---|---|---|---|
| **Skill** | Agent clients supporting skill imports | No | Drive SolidWorks via natural language |
| **MCP** | MCP clients such as Codex / Claude / Cursor / Windsurf | No | Automated Agent Tool Calling |
| **CAD Studio** | Users wanting a GUI to manage projects/jobs/previews/deliverables | Yes | Submit tasks from the desktop app |

All three are **peer entry points** sharing the same capability registry (`capabilities.yaml`), scripts, and evidence system. After installation, run `python scripts/cad_doctor.py` for environment diagnostics; see [`docs/CAD_STUDIO_USER_MANUAL.md`](docs/CAD_STUDIO_USER_MANUAL.md) for detailed installation and CLI usage.

---

## Why This Project

LLMs can plan, but typical AI CAD automation faces several real-world problems:

- LLMs can plan, but cannot genuinely operate desktop CAD software
- A tool returning `success` does not mean the task actually succeeded
- CAD API versions, environments, and backend differences are complex
- A fixed toolset cannot cover every engineering requirement
- Agent execution is usually untraceable and non-auditable

How this project solves them:

| Problem | Solution |
|---|---|
| Natural language → real execution | Skill / MCP connected to real COM and backends |
| Tool success ≠ Task success | Verification-first completion |
| Backend failure | Backend Router + Recovery Decision |
| Missing capability | Capability Gap → handed back to Agent for API lookup |
| Untraceable execution | Structured Trace |
| Reliability verification | Golden Workflow Eval |

---

## Architecture

```text
User / Agent
  ↓
Skill / MCP
  ↓
Execution Core（Capability · Verification · Recovery Decision · Trace）
  ↓
Backend Router
  ↓
Python COM / C# / OCCT
  ↓
CAD Software
  ↓
Artifacts + Evidence
```

- **Root Skill** = general capabilities, rules, and execution infrastructure (connection, modeling, review, MCP).
- **Subskills** = domain-specific workflows (engineering drawings, threaded holes, CNC Fillets, VibeCAD, AutoCAD), invoked on demand by the Root Skill without manual startup.
- **Execution Core** = internal reliable execution layer: unified state, result verification, failure recovery decisions, and execution tracing. It is an internal implementation, **not a standalone service and requires no manual startup**.
- **Capability Gap** = when a capability is missing, returns a structured `CAPABILITY_GAP` back to the Agent for lookup instead of saying "cannot do":

  ```text
  Existing Tools → Tool Composition → Backend Fallback → Capability Gap
    → Agent 查 references / 官方 API / SDK → 最小实现 → Verification
  ```

  Execution Core itself **never automatically goes online to execute unknown code**.

Details: [`docs/architecture/execution-core.md`](docs/architecture/execution-core.md)

---

## Reliability

Currently ships with **43 deterministic reliability scenarios** (12 nominal + 31 robustness),
covering nominal execution, fault injection, backend fallback, capability gaps, and policy gates; derived from the 12 workflows in `golden-workflows.yaml`.

| Metric | Current baseline |
|---|---|
| Nominal workflow | 12/12 first-pass (baseline v4; warnings routed to guardrails, awaiting manual review) |
| Injected false-completion cases | all detected |
| Escaped false completion | 0 in current deterministic benchmark |
| Regression suite | See [Reliability Fixes & Acceptance](docs/architecture/scheme-b-reliability.md) for current Scheme B verification records |

> This is a **deterministic engineering benchmark** (Fake Handler/Reviewer + fault injection),
> not a production SLA or real-world user success rate. See [`docs/architecture/v2-evaluation.md`](docs/architecture/v2-evaluation.md) for details.

### Verification Boundary

Verification in this project is divided into three layers; **conclusions cannot be generalized across layers**:

| Layer | Where It Runs | What It Covers | What It Does Not Cover |
|---|---|---|---|
| L1 Offline Regression | Any machine | `pytest` (full suite, currently 1,045 tests), `evals/runner.py` (12 workflows / 43 scenarios), governance unit tests (currently 93 tests) | Anything requiring a SolidWorks / AutoCAD process |
| L2 Hosted CI | GitHub-hosted `windows-2022` | Same as L1, plus frontend / Rust builds and release contract checks; job name `test-and-build`, the **only required status check** on `main` | Real CAD execution |
| L3 Live CAD Acceptance | **Maintainer's local machine only** (Windows 11 + SolidWorks 2026 SP01.1) | Five-round live Golden runs, assembly/drawing/Motion Study live regressions | Other machines, other versions |

Three points must be clear:

1. **No remote live-CAD execution evidence exists.** The repository has no self-hosted runner; the `Windows CAD Regression` workflow is manually triggered,
   is **not a required check**, and cannot currently run. Any claim that "remote CAD CI passed" is false.
2. **Local pass ≠ cross-machine pass.** On a different machine, re-run self-checks per `Prerequisites` and `docs/CAD_STUDIO_USER_MANUAL.md`;
   do not cite the maintainer's acceptance results directly.
3. **L2 pass ≠ full governance closure.** Required checks protect `main` only; PRs targeting feature branches (including stacked PRs) are not enforced by this rule.

Recent native SolidWorks regressions use **2026 SP1.1** as the baseline, with additional **2024** live-machine records for certain capabilities. Always refer to `verified_versions`, tiers, and constraints in the [Capability Registry](capabilities.yaml); unlisted versions require separate verification. Environment diagnostics check only installation and runtime prerequisites; engineering functionality must be verified per actual task.

**Full mode exposes 69 named tools; default discovery mode exposes only 3 lookup entry points** (`sw_search_tools` /
`sw_describe_tool` / `sw_call_tool`). Existing named tools remain compatible; discovery mode
retrieves tools on demand; write operations pass through policy checks, with approval behavior and trust boundaries governed by configuration. See
[`mcp-server/README.md`](mcp-server/README.md) for mode switching, approval, and rollback.

---

## Capabilities & Status

| Category | What You Can Do | Status |
|---|---|---|
| Modeling | Part modeling, Sketch/Extrude/Revolve, gears, Sheet Metal, Weldments | `verified` + `pilot` |
| Assembly | Assembly, Mates, interference detection, exploded views | `verified` |
| Drawing | GB/T engineering drawings, dimension chains, hole tables, BOM | `verified` + `pilot` |
| Export | STEP / STL / IGES / PDF / DXF / DWG | `verified` |
| Motion | Motion Study, rotary motors, result gating | `pilot` |
| Design Audit | Neutral document design rules, baseline diffing, lead-screw/belt motor torque preliminary sizing | `pilot` |
| Drilling Panel | Panel hole-location recognition, datums, and drawing specification candidates | `pilot` |
| Tolerances | Read-only extraction of displayed dimension tolerances, CSV output | `pilot` |
| Rename Preview / Copy | Property-based rename preview; constrained standalone parts and single-configuration nested assemblies copied under new names | `pilot` |
| Sprocket | Approximate sprocket geometry demo solid, non-production tooth profile | `pilot` |
| Spring | Open-end constant-pitch round-wire helical spring solid | `pilot` |
| FEA | CalculiX linear/nonlinear solver orchestration and audit | `pilot` |
| DFM / Routing | Manufacturability review, Routing review | `pilot` |
| Surface / Mold | Constrained Loft/Sweep/Thicken, mold planning | `pilot` |
| AutoCAD | DWG/DXF 2D drafting, layers/dimensions/previews | `verified` / `pilot` / `blocked` |
| Open-format | OCCT headless writing for STEP/BREP/STL/OBJ/GLB, etc. | `verified` |

Status tiers (defined in `capabilities.yaml`):

| Status | Meaning |
|---|---|
| `verified` | Live-machine verified; ready for use within documented scope |
| `stable` | Covered by long-term regression suites |
| `pilot` | Implemented, but still requires manual review |
| `blocked` | Automated delivery disallowed under current environment or capability constraints |

Verify SolidWorks capabilities against the registry above. AutoCAD live-machine evidence covers corresponding 2024 capabilities; pilot features retain manual review.

- Full capability matrix (exact tier/version/limits per capability) → [`capabilities.yaml`](capabilities.yaml)
- Domain workflows → [`subskills/`](subskills/) · [`SUBSKILLS.md`](SUBSKILLS.md)

---

## No SolidWorks Installed?

Without SolidWorks installed, several open-format tasks can still be completed:

`STEP · IGES · BREP · STL · OBJ · GLB · DXF · SVG · PDF · PNG`

(Written genuinely via an isolated OCCT/OCP process.)

However, native `SLDPRT / SLDASM / SLDDRW` still requires a licensed SolidWorks environment.

---

## Examples

The [`examples/`](examples/) directory contains runnable examples ranging from basic parts to assemblies, engineering drawings, Motion, and FEA.

---

## Documentation

| Topic | Link |
|---|---|
| MCP Setup | [`mcp-server/README.md`](mcp-server/README.md) |
| CAD Studio | [`docs/CAD_STUDIO_USER_MANUAL.md`](docs/CAD_STUDIO_USER_MANUAL.md) |
| Architecture | [`docs/architecture/execution-core.md`](docs/architecture/execution-core.md) |
| Reliability Eval | [`docs/architecture/v2-evaluation.md`](docs/architecture/v2-evaluation.md) |
| Capability Matrix | [`capabilities.yaml`](capabilities.yaml) |
| Subskills | [`SUBSKILLS.md`](SUBSKILLS.md) |
| API / Backend | [`references/`](references/) |
| Design audit / drive sizing | [`references/design-rule-check.md`](references/design-rule-check.md) · [`references/drive-sizing.md`](references/drive-sizing.md) |
| Drilling panel analysis | [`subskills/solidworks-engineering-drawing/references/drilling-panel-gdt.md`](subskills/solidworks-engineering-drawing/references/drilling-panel-gdt.md) |
| Native GD&T / structured drawing generation (SW2026 pilot) | [`subskills/solidworks-engineering-drawing/references/native-gdt.md`](subskills/solidworks-engineering-drawing/references/native-gdt.md) |
| Common datums / projected zones / extended GD&T (SW2026 pilot) | [`subskills/solidworks-engineering-drawing/references/gdt-extended-options.md`](subskills/solidworks-engineering-drawing/references/gdt-extended-options.md) |
| Tolerance extraction | [`references/tolerance-extraction.md`](references/tolerance-extraction.md) |
| Rename preview | [`references/rename-preview.md`](references/rename-preview.md) |
| Approximate sprocket | [`references/sprocket.md`](references/sprocket.md) |
| Open helical spring | [`references/spring.md`](references/spring.md) |
| Troubleshooting | [`references/troubleshooting.md`](references/troubleshooting.md) |

---

## Roadmap & Contributing

**Roadmap**: Broader live-machine verification · More reliable capability routing · Better CAD Studio observability · More verified subskills · Community contribution workflows.

**Contributing**: When adding capabilities, check `capabilities.yaml` first, prefer reusing existing backends, add tests + evidence, and never mark an unverified capability as `verified`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

---

## License & Community

[MIT](LICENSE) · [GitHub Issues](https://github.com/wzyn20051216/solidworks-automation-skill/issues) · [Star History](https://star-history.com/#wzyn20051216/solidworks-automation-skill&Date)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=wzyn20051216/solidworks-automation-skill&amp;type=Date&amp;theme=dark">
  <img src="https://api.star-history.com/svg?repos=wzyn20051216/solidworks-automation-skill&amp;type=Date" alt="SolidWorks Automation Skill Star History" width="960">
</picture>

---

## English

**SolidWorks Automation Skill** is an AI Skill + MCP toolkit for reliable desktop CAD automation. Codex, Claude, Cursor, and other agents drive real SolidWorks / CAD workflows through natural language, with verification, deterministic recovery decisions, and execution tracing. Three peer entry points — Skill, MCP, and CAD Studio — share one capability registry (`capabilities.yaml`). **Choose one; no extra runtime service is required.** See Quick Start above.

---

<sub>Follow Douyin @balance. · Ongoing updates on embedded development, SolidWorks automation, and AI-assisted engineering practice</sub>

### Assembly Interference Check API

`solidworks_interference_check` uses `IAssemblyDoc.InterferenceDetectionManager`,
computes via `GetInterferences()`, reads `IInterference.Components` and volume, and finishes by calling
`Done()`. Hidden bodies and ignored results are included in the check; intersections within the same multibody part are excluded.
Calculation failure, count read failure, array length mismatch, or check-finalization failure all return `blocked` and never falsely report zero interference.
Suppressed components are excluded from calculation; a zero-interference result still requires checking component resolved state and design intent.
Offline regressions cover call order, failure handling, and SI volume conversion (26 tests passed).
Verified via MCP live testing on SOLIDWORKS 2026 SP4.1 (34.4.1) with Python 3.10;
this live-machine sample has zero interference, while non-zero result parsing remains backed by offline regression evidence.
