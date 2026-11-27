# CAD Studio User Manual

This guide is intended for mechanical engineers, students, and designers using CAD Studio for the first time. CAD Studio is a peer entry point alongside Skill/CLI/MCP, sharing the same CAD Core, job protocol, capability manifest, and evidence system; users can run Skill/CLI/MCP directly without installing the desktop app. Engineering files and job records are stored locally by default.

## 1. What the Software Can Do

- Plan and create basic parts, enclosures, fixtures, and assemblies from natural language; SW2026 supports pilot creation of open-profile base flanges and flat-pattern DXF export, while other sheet-metal capabilities follow the capability manifest into human review or `blocked`.
- Modify existing SLDPRT, SLDASM, STEP, STL, DWG, DXF, PDF, or reference image files.
- Create through holes, blind holes, counterbores, countersinks, threaded holes, slots, half-round slots, and hole patterns.
- Output `.cadstudio.json`, STL, OBJ, DXF, SVG, PDF, PNG, and review reports without CAD software installed; native SLDPRT/SLDASM/SLDDRW/DWG outputs require the corresponding CAD software and a verified backend.
- Automatically select CAD software, materials, processes, and execution stages, while still allowing manual overrides.
- Orchestrate integrated engineering workflows: "Requirements Analysis -> Concept -> Parts -> Assembly -> Motion/Interference -> Drawings -> Delivery".
- Enforce human approval and review gates to prevent unconfirmed control of desktop CAD or delivery of erroneous files.

## 2. System Requirements

### 2.1 Desktop Application

- Windows 10 22H2 or Windows 11, 64-bit.
- Microsoft Edge WebView2 Runtime. Usually preinstalled on Windows 10/11; the installer prompts if missing.
- 8 GB RAM recommended; 16 GB or more recommended for complex assemblies.

### 2.2 Execution AI

Install and sign in to at least one of the following CLIs:

- Codex CLI
- Claude Code
- Gemini CLI
- OpenCode

CAD Studio does not bundle model credits and does not store API keys. Model accounts, subscriptions, proxies, and routing are managed by the respective CLI or CC Switch.

Refer to the table below for initial installation. Installing via npm requires Node.js 20 or higher; on managed corporate machines where global npm installs are restricted, contact your administrator or use each project's official installer.

| Agent | Official Documentation | Common Installation Method | Check Command |
| --- | --- | --- | --- |
| Codex CLI | <https://developers.openai.com/codex/cli/> | `npm install -g @openai/codex` | `codex --version`, `codex login status` |
| Claude Code | <https://docs.anthropic.com/en/docs/claude-code/setup> | Follow the official Windows installer or PowerShell guide | `claude --version`, then run `claude` to sign in |
| Gemini CLI | <https://github.com/google-gemini/gemini-cli> | `npm install -g @google/gemini-cli` | `gemini --version`, then run `gemini` to sign in |
| OpenCode | <https://opencode.ai/docs/> | `npm install -g opencode-ai` | `opencode --version`, `opencode auth login` |

Close and reopen CAD Studio after installation. If the check command works in PowerShell but CAD Studio does not detect the CLI, confirm that the npm global directory is in your user `PATH`; you can also set system environment variables `CODEX_BIN`, `CLAUDE_BIN`, `GEMINI_BIN`, or `OPENCODE_BIN` to the full executable path.

### 2.3 Live CAD Automation

- Python 3.10 or higher; 64-bit Python 3.11/3.12 recommended.
- Recent SolidWorks live-machine regressions use 2026 SP1.1 as the baseline, with additional 2024 records for select capabilities. Check `verified_versions`, maturity level, and limitations per item in `capabilities.yaml`. Unlisted versions such as SolidWorks 2025 require separate verification. AutoCAD live-machine evidence covers the corresponding 2024 capabilities.
- Python, SolidWorks, and AutoCAD must all be 64-bit to match the OS.

Dependencies are organized into three tiers and installed on demand:

After an initial failure during installer or automatic COM dependency setup, pip retries once against official PyPI by default. Use `SW_PIP_INDEX_URL` to set the primary index and `SW_PIP_FALLBACK_INDEX_URL` to set the fallback index (set to an empty string to disable fallback).

CAD Studio's environment status handshakes running SolidWorks/AutoCAD instances to distinguish "Connected", "Installed, not running", and "Connection check pending". You can run `python scripts/cad_doctor.py --live-cad` manually. `--probe-cad` allows launching SolidWorks for a self-check and cleans up only self-launched instances that have no open documents.

| Tier | Contents | When Needed | Installation Command |
|---|---|---|---|
| **Minimal** | `pywin32`, `comtypes` | Driving SolidWorks / AutoCAD COM interfaces only | `python -m pip install "pywin32>=305" "comtypes>=1.2.0"` (Windows only) |
| **Full** | Also includes `mcp`, `pydantic`, `ezdxf`, `matplotlib`, `PyMuPDF`, `jsonschema` | Needed for the MCP server, DXF read/write, preview rendering, and schema validation (required by CAD Studio and Golden workflows) | Same as above; included in `requirements.txt` |
| **Open Format** | `cadquery-ocp`, `trimesh`, `numpy` | Writing STEP/BREP/STL/OBJ/GLB without SolidWorks installed | `python -m pip install -r requirements-occt.txt` |

Actual contents of `requirements.txt`:

```text
pywin32>=305; sys_platform == 'win32'
comtypes>=1.2.0; sys_platform == 'win32'
mcp>=1.27,<2
pydantic>=2.0
ezdxf>=1.3,<2
matplotlib>=3.8,<4
PyMuPDF>=1.24,<2
jsonschema>=4.20,<5
```

With only the minimal tier installed, the MCP entry point and `ezdxf`-dependent subskills will fail due to missing packages; `python scripts/cad_doctor.py` explicitly lists missing items rather than silently degrading.

Install all Python dependencies:

```powershell
python -m pip install -r requirements.txt
# 需要开放格式能力时追加
python -m pip install -r requirements-occt.txt
```

Run after first installation or environment changes:

```powershell
python scripts\cad_studio.py doctor
```

The `remediations` field in the output provides official URLs and install commands for missing components; the desktop Settings and Help pages show the same recommendations. Missing optional backends block only their corresponding formats without blocking other available backends.

### 2.4 Headless Open-Format Backend (No CAD Software Required)

Even without SolidWorks/AutoCAD installed, workflows are no longer limited to requirement structuring and script generation. The current headless backend genuinely writes `.cadstudio.json`, STEP, IGES, BREP, STL, OBJ, GLB, DXF, SVG, PDF, and PNG from `NeutralCadDocument`, along with geometric evidence, Preview Manifests, fallback images, and SHA-256 hashes:

```powershell
python scripts\cad_studio.py write-open-format `
  --input .\part.cadstudio.json `
  --out-dir .\output `
  --formats cadstudio step iges brep stl obj glb dxf svg pdf png
```

Existing DXF files can be converted into a standalone browser preview scene:

```powershell
python scripts\cad_studio.py preview-dxf `
  --input .\drawing.dxf `
  --output .\output\drawing.scene.json
```

This converter reads only `LINE`, `CIRCLE`, `ARC`, `LWPOLYLINE`, `POLYLINE`, `TEXT`, `MTEXT`, and `DIMENSION`, capped at 50 MB / 200,000 entities; unsupported entities are recorded as limitations, and it never executes scripts or overwrites existing scene files.

OCCT currently covers boxes, cylinders, boolean unions, cylindrical hole cuts, and constrained closed ruled Lofts via a dedicated entry point, reading back solid validity, volume, bounding box, and topology counts; smooth Lofts and other complex features still return `blocked`. Native SLDPRT/SLDASM/SLDDRW/DWG outputs must return `blocked` when vendor software or licensed SDKs are unavailable and must never be spoofed by renaming file extensions.

Before your first run, execute:

```powershell
python scripts/cad_studio.py doctor
```

Capability boundaries are defined authoritatively in the repository root `capabilities.yaml`. Configuration families, SW2026 open-profile sheet metal, and HSS rectangular weldment frames have entered controlled `pilot`, while design tables and complex sheet metal/weldments are still never marked as complete deliveries. Weldments must read back `WeldmentFeature`, `WeldMemberFeat`, and per-`CutListFolder` body counts, lengths, quantities, and angles, and undergo save-and-reopen verification. Simulation/FEA supports constrained linear-static runs via CalculiX, and complex surfacing supports constrained closed ruled Lofts via OCP; without result evidence, mesh convergence, or geometric quality proof, these pilot capabilities must not be presented as complete engineering deliveries.

The CLI can also invoke these controlled gates independently:

```powershell
python scripts\cad_studio.py check-dfm --input .\part.cadstudio.json --output .\output\dfm.json --profile "$PWD\supplier-profile.json"
python scripts\cad_studio.py routing-preflight
python scripts\cad_studio.py check-routing --input .\route.json --output .\output\routing_report.json
python scripts\cad_studio.py fea-preflight --solver auto
python scripts\cad_studio.py prepare-fea --input .\fea.json --out-dir .\output\fea
python scripts\cad_studio.py run-fea --input .\fea.json --out-dir .\output\fea --timeout 120
python scripts\cad_studio.py review-advanced-geometry --input .\surface-plan.json --output .\output\surface_report.json
python scripts\cad_studio.py create-ocp-loft --input .\loft.json --out-dir .\output\loft
```

Drawing and BOM jobs additionally return views, real dimensions, BOM rows, model/drawing relations, and review findings. Automatic insertion of model dimensions with real dimension entity readback has been verified independently on both SW2024 and SW2026 SP01.1; the SW2026 regression read back 3 real views and 6 real dimension entities across three consecutive runs. Full engineering drawings remain `pilot`: file existence does not equal delivery readiness, and sheet size, view layout, dimension chains, hole tables, title blocks, and BOM still require human review.

AutoCAD backends are separated into headless DXF inspection, an allowlisted command bridge, COM, and .NET. Currently, COM proxies on local AutoCAD 2024 remain unstable; the standalone .NET backend has completed consecutive allowlisted live regressions via the native Managed API, creating and reopening genuine DWGs, generating PDF/PNGs, and reading back entities, layers, and real dimensions. Preflight checks re-verify the last three reports and artifact hashes, returning `verified` when intact and automatically downgrading if evidence is corrupted; this does not imply arbitrary DWG operations or arbitrary plugin code are supported. Run:

```powershell
python subskills\autocad-automation\scripts\acad_dotnet_preflight.py
python subskills\autocad-automation\scripts\acad_dotnet_regression.py
python subskills\autocad-automation\scripts\acad_dotnet_regression.py --real-cad
```

The .NET live regression uses a sample drawing with a localized title block and 120 × 48 mm entity dimensions. It requires SimSun font and PyMuPDF from `requirements.txt`. The regression reopens the DWG to re-verify text, fonts, and dimensions, reads back the viewport and plot extents enclosing the entire drawing, and verifies rendered PDF text plus native PNG dimensions, content, and margins. Results are written to `output/autocad-dotnet`; this sample is for regression only, and manufacturing drawings still require project-specific drawing review.

Use `--install-sdk` only when explicitly authorized; it installs the .NET SDK from the official Microsoft source and never downloads proprietary Autodesk DLLs. If `dotnet.exe` on system `PATH` only provides a runtime, the checker continues probing the current user directory for a real SDK. Loading unsigned plugins in desktop AutoCAD still requires configuring trusted paths or using a signed plugin bundle; live regression reads original `SECURELOAD/FILEDIA/BACKGROUNDPLOT` values first, adjusts them temporarily only inside an exclusive Core Console, and restores them before exit.

## 3. Installation and Startup

### Installer

1. Download `CAD-Studio-<version>-Setup-x64.exe` from GitHub Releases.
2. Double-click to install and follow the prompts.
3. Launch CAD Studio from the Start Menu.

The executable in the install directory is named `cad-studio.exe`; manual navigation to the install folder is not needed for daily use.

### Portable Edition

1. Download `CAD-Studio-<version>-Windows-x64-Portable.zip`.
2. Extract the entire archive to a writable directory.
3. Run `CAD Studio.exe` inside that directory.
4. Do not move only the `.exe`; the sibling `skill` directory is part of the local worker runtime.

Windows SmartScreen may show an "Unknown publisher" warning because open-source builds do not currently purchase a commercial code-signing certificate. Verify the SHA-256 hash on the Release page before running.

### Automatic Updates

On startup, the Windows desktop build of CAD Studio silently checks GitHub Releases once. When a new version is found, an update prompt appears in the lower-right corner; open Settings to inspect the current version, release notes, and download progress.

1. Click "Download & Install" to download the update package and verify the Tauri updater signature.
2. Once the signature validates, the Windows installer takes over and closes the current window.
3. If checking or installation fails, click "Open Download Page" to download manually from GitHub Releases and verify against `SHA256SUMS.txt`.

The updater signature verifies that the update comes from this project and has not been tampered with; it is not a commercial Windows code-signing certificate, so SmartScreen may still show "Unknown publisher". The app never installs updates without explicit user confirmation.

## 4. First-Time Setup

1. Open **Help** in the top bar to inspect environment status.
2. Open **Settings** and choose an installed Agent on your machine.
3. If using CC Switch, click **Read CC Switch Status**. CAD Studio reads CC Switch SQLite/JSON config in your user directory and returns only route name, model, endpoint, and managed status—never API keys.
4. Click **Select Output Folder** to create an isolated project directory.
5. Install Python dependencies and start SolidWorks or AutoCAD if you need live CAD operations.
6. Click **Start Local Worker**. Once you see Running and a PID, you can submit jobs.

## 5. Creating Your First Model

### Modeling from Scratch

1. Click **New Job** on the left or **Modeling** in the top bar.
2. Choose a template such as General Part, Assembly, or Enclosure.
3. Enter your complete requirements in the goal box, for example:

```text
创建一块 120 x 80 x 8 mm 的 6061 铝安装板。
四角各有一个直径 6.6 mm 通孔，孔中心距相邻边均为 10 mm。
上表面中心制作一个直径 20 mm、深 4 mm 的沉孔。
四周倒角 1 x 45 度。
输出 SLDPRT、STEP、PDF 工程图和四视角 PNG，保存到当前输出目录。
```

4. Leave **AI Auto Select** enabled whenever software, material, or process is not specified.
5. Keep **Real Holes/Cuts** enabled whenever holes or slots are involved.
6. Enable **Local CAD Automation** when live CAD operations are required.
7. Review the execution plan on the right and click **Send to Active AI**.
8. When an approval prompt appears for high-risk capabilities, verify the reason and click Approve.

### Modifying Existing Files

1. Click **Import** in the top bar.
2. Select a CAD file, drawing, or reference image.
3. Describe what to keep and what to change in the chat box.
4. Explicitly request saving to a new file to avoid overwriting the original project.

## 6. Using Integrated Engineering Workflows

When assembly, motion, drawings, and delivery are all needed, you do not have to split them into disconnected tasks. Describe the final goal directly, and CAD Studio builds a staged engineering plan:

1. Requirement and constraint extraction.
2. CAD software and skill routing.
3. Part modeling and key features.
4. Assembly mates and interference checking.
5. Motion Study or kinematic verification.
6. Engineering drawings (this localized edition prioritizes **TCVN (Vietnamese Standards) and ISO**, while retaining `GB/T` as a secondary reference), BOM, and tolerances.
7. Format export, artifact ledger, and human review.

For follow-up edits, simply issue localized changes such as "change M6 to M8 and keep all other dimensions unchanged". The system restores the prior plan and re-runs only affected stages and their downstream dependents.

Explicit chat-based modifications also mark impacted prior results in the current project once queued. For example, "change hole diameter to 8 mm" marks stages starting from holes/slots, whereas "change requirement to outdoor use" flags the entire plan for re-verification. Ordinary follow-up questions, hypotheticals, negations, and third-party quotes do not trigger flagging. State the target and new value clearly (e.g., "change width to 120 mm"). Chat instructions are saved with the job, while reference dimension fields in the workbench remain independently editable.

In a job's **Stage Review**, you can inspect each stage's acceptance criteria and steps requiring human confirmation. Criteria come from the engineering plan, while actual execution and sign-off status remain grounded in the job record.

With Local CAD Automation enabled, newly created or opened documents driven by the bundled `SolidWorksSession` script display live modeling views inside the job's **SolidWorks Live Preview**. Frames update at sketch completion, extrusion, cut, save, and export steps (verified on SolidWorks 2026). If the window is minimized, focus switches to another document, or capture fails, **Preview Unavailable** is shown. Preview frames are stored temporarily during the run and cleaned up when the job finishes.

After editing a project's goal or length/width/height/wall thickness in the workbench, prior jobs switch to **Review Required**. Goal changes require re-checking the entire plan; key dimension changes mark part modeling and downstream dependent stages while leaving independent stages intact. Project inputs and review statuses persist across restarts. Old files and prior review records remain inspectable—resubmit the job with updated inputs, then complete review and delivery.

When project inputs have not changed, failed, blocked, canceled, or review-required jobs can also be partially regenerated from the Delivery Center. Before clearing current-run fields, CAD Studio saves the previous run's status, artifact ledger, drawing/BOM evidence, review gates, and errors as a read-only version snapshot (retaining up to the latest 20 runs by default). The retry policy resumes from the failed stage and downstream stages, enforcing a new version directory or filename for new outputs. Historical snapshots store only paths, sizes, hashes, and review evidence—they never duplicate CAD file contents or delete prior deliverables.

When key dimensions, tolerances, loads, material strength, or safety-critical parameters are missing, the AI must ask for clarification or label the result as a concept proposal rather than presenting it as manufacturing-ready.

## 7. Page Guide

- **Left Job List**: Historical jobs for the current project. Titles come from user goals; legacy entries labeled "Codex Execution" are historical internal titles and do not mean Codex is locked in.
- **Overview**: Create jobs, import reference files, and inspect current environment status.
- **Modeling**: Templates for parts, assemblies, fixtures, sheet metal, enclosures, reverse engineering, etc.
- **Features**: Holes, slots, threads, connector cutouts, and patterns.
- **Drawings**: Engineering drawings (this localized edition prioritizes **TCVN and ISO**, retaining `GB/T` as a secondary reference), tolerances, BOM, and format conversion.
- **Review**: Verify native openability, dimensions, features, artifacts, and risks.
- **Delivery**: Unified determination of Ready / Human Review Required / Blocked / Incomplete Evidence, displaying current-run artifacts, version history, artifact relations, and backend diagnostics; STL, GLB/GLTF, and OBJ support rotate/zoom, while DXF and images support read-only preview. CAD, drawing, and deliverable files count as current-run artifacts only when `producedThisRun=true`; stale files fail immediately, and files with unknown provenance require human review first.
- **Settings**: AI, CC Switch, local worker, output paths, and knowledge base.
- **Help**: First-time setup steps and environment diagnostics.

## 8. Agents and CC Switch

"Agent" and "Model Routing" are two distinct layers:

- The **Agent CLI** decides whether Codex, Claude Code, Gemini CLI, or OpenCode executes the job.
- **CC Switch** routing decides which model provider, endpoint, and model that CLI uses.

Selecting Claude Code switches the execution button, executor, and route list to Claude; syncing CC Switch will not revert back to Codex.

CC Switch is optional. Without it, CAD Studio directly uses the selected CLI's local login session and configuration.

### LM Studio Local Q&A and Task Planning

1. Download and load a chat model in [LM Studio 0.4 or newer](https://lmstudio.ai/download). Start the local API on the Developer page (default `http://127.0.0.1:1234/v1`).
2. Expand **LM Studio Local Q&A & Task Planning** in CAD Studio, click **Check Connection**, and choose a model.
3. Ask questions and follow-ups in **Q&A** mode. Switch to **Task Planning**, enter a standalone task goal, and inspect open questions, steps, and acceptance criteria. Planning requires a model that supports [Structured Output](https://lmstudio.ai/docs/developer/openai-compat/structured-output).

The local assistant displays results within the current project session. Actual CAD actions are still submitted and approved via **AI Execution Chat**. Switching projects or closing CAD Studio clears the local assistant's temporary session.

If LM Studio runs on another port, set `LMSTUDIO_BASE_URL` before launching CAD Studio (loopback HTTP addresses only). If API auth is enabled, set `LMSTUDIO_API_KEY` for the CAD Studio process. If the model list is empty, load a chat model and check connection again.

## 9. Approval and Review

The following actions require human approval:

- Controlling a desktop SolidWorks / AutoCAD session.
- Accessing files outside the project directory.
- Using external networks or cloud knowledge bases.
- Full-access sandbox, deleting files, or `git push`.

After job completion, verify at minimum:

- Files open natively in the target CAD software.
- Key dimensions, tolerances, datums, and hole locations are accurate.
- Holes and slots are real geometric features, not just sketches or annotations.
- Assembly mates, clearances/interference, and motion directions are accurate.
- Current-run output files exist with the expected timestamps and versions.

A job can be marked passed only after filling in review notes and completing every checklist item.

## 10. File Storage and Privacy

- Default output: current user's `Documents/CADAutomationWorkbench`.
- Queue and settings: current user's app-data directory `com.wzyn.cadstudio`.
- Wallpapers, project paths, job events, and deliverable ledgers are stored locally.
- API keys are never written to CAD Studio settings or job files.
- Engineering context leaves your machine only if you explicitly enable cloud RAG or the chosen AI CLI itself accesses the network.

Never upload queue directories, logs, or job JSONs containing confidential company data to public GitHub Issues.

## 11. Troubleshooting

### "No Agent Provider Detected"

Confirm the CLI runs `--version` in PowerShell, then restart CAD Studio. Advanced users can specify executables via `CODEX_BIN`, `CLAUDE_BIN`, `GEMINI_BIN`, or `OPENCODE_BIN`.

### "Python Not Installed"

Install 64-bit Python 3 and check **Add Python to PATH** in the installer. Restart CAD Studio, then start the local worker.

### "SolidWorks / AutoCAD Not Detected"

Verify the software is installed properly; launching SolidWorks manually once before automation is recommended. CAD Studio checks COM registrations, public desktop shortcuts, standard paths, and common `D:`/`E:` install directories. "Installed but not running" is not an installation error—launch the software manually and re-check.

### CC Switch Does Not Show All Models

Upgrade to a recent version of CC Switch and confirm your configuration is saved. CAD Studio supports both `~/.cc-switch/cc-switch.db` and legacy `config.json`.

### Job Stuck in Approval Required

Open job details to inspect the approval reasons. The local worker proceeds only after explicit user approval.

### Why Are There Many Items on the Left?

The left sidebar is the historical job list, not a feature menu. Click any job to inspect its status and outputs. Jobs are stored in the local queue directory; deleting app data clears history, so back up needed deliverables first.

## 12. Getting Help and Feedback

When filing a GitHub Issue, please include:

- CAD Studio version and installation type.
- Versions of Windows, Python, SolidWorks/AutoCAD, and your Agent CLI.
- Reproducible steps and sanitized error messages.
- Whether CC Switch is used and the route type; never include API keys.

Project repository: <https://github.com/wzyn20051216/solidworks-automation-skill>
