# SolidWorks MCP Server Design Notes

## Architecture

```text
Codex / Claude / 其他 MCP Client
        ↓ stdio MCP
mcp-server/server.py
        ↓ Python COM / pywin32
SolidWorks Desktop
```

SolidWorks is a Windows desktop COM application, not a native MCP service. The MCP Server's role is to expose verified `scripts/sw_*.py` modules as controlled tools so agents do not have to synthesize large ad-hoc scripts on every run.

## Transport Selection

`stdio` is the default:

- Well suited for local desktop software.
- The client launches the server as a child process with minimal configuration.
- Exposes no network ports, minimizing attack surface.

HTTP is not enabled by default:

- SolidWorks COM is typically bound to the active interactive desktop user session.
- Concurrent multi-client calls easily corrupt SolidWorks document state.
- Remote access would also require authentication, Origin checks, and desktop session isolation.

## Tool Discovery and Approval

Default mode `SW_MCP_DISCOVERY=search` exposes only three entry points (`sw_search_tools` / `sw_describe_tool` / `sw_call_tool`), allowing the 69 native named tools to be discovered on demand. `SW_MCP_DISCOVERY=full` exposes all named tools directly for clients that require per-tool permission prompts.

Use `sw_search_tools` to search for "API signature" (or `"API 接口签名"`), then call `solidworks_lookup_api` with `interface` and `member`, or natural-language `task`, plus optional `version` / `process_id`. Because it may auto-configure dependencies by default, tool annotations mark it as potentially modifying the environment; set `auto_install=false` to disable installation and `offline=true` to disable networking and installation. The server differentiates side-effect levels by parameter while preserving existing client and server authorization modes. When direct official-site reads fail and no local cache exists, anonymous Parallel is used by default to extract the version-matched official page; disable with `parallel_fallback=false`. Parallel carries weaker version proof than structured official metadata, and no lookup result replaces live verification on the target version. See `references/api-lookup.md` for details.

Implementation replaces FastMCP's `_tool_manager` with a `ToolGate` proxy. Both `list_tools` and `call_tool` read this attribute on every invocation, so `stdio`, `streamable-http`, and direct client calls to hidden tools all pass through the exact same enforcement pipeline:

- `mcp-server/discovery.py`: Offline search over read-only tool metadata; handles neither authorization nor execution.
- `mcp-server/policy.py`: Single source of truth for side effects (`READ` / `WRITE` / `DESTRUCTIVE` / `UNKNOWN`); unregistered tools are denied by default, new tools must be classified first, and `tests/test_mcp_discovery.py` enforces registry alignment.
- `mcp-server/gate.py`: Visibility control, pre-execution policy checks, and write-operation approval.
- `mcp-server/approval.py`: Optional HMAC-signed one-time approval ledger binding tool name, argument digest, server session, and TTL. Strict mode can bind saved-document process ID and path, though it cannot prove document contents remain unchanged.
- `scripts/sw_mcp_approve.py`: Interactive terminal confirmation; passing `approved: true` inside MCP tool arguments from a model has no effect. Note that a TTY does not prove a human operator—processes under the same OS user can emulate a terminal or access the ledger, so this is not a security boundary against an untrusted agent running under the same user account.

Approval mode `SW_MCP_APPROVAL`: `auto` (default: discovery mode -> `task`, full mode -> `client`), `task`, `server`, `client`, `elicit`, `off`. `task` trusts client task authorization without server-side proof of user confirmation. `elicit` relies on client MCP elicitation support and can be auto-answered by agents, so it is not default. The server ledger likewise does not isolate processes sharing the same OS privileges.

## Multi-Client Registration Strategy

The installer runs `mcp-server/register_all_ai_mcp.js` to register common local AI clients automatically where possible:

- Codex: registered via `codex mcp add solidworks -- <python> <server.py>`.
- Claude Code: registered via `claude mcp add --scope user solidworks -- <python> <server.py>`.
- Claude Desktop: written to user-level `claude_desktop_config.json`.
- Cursor: written to global `~/.cursor/mcp.json`.
- Windsurf: written to global `~/.codeium/windsurf/mcp_config.json`.

Notes:

1. Automatic local MCP config edits only run when executing the `npx` installer or registration script; importing a skill alone generally does not run install scripts.
2. Clients may require a restart or manual trust confirmation before loading the new MCP server.
3. Cloud web apps without a local configuration entry point cannot have a local MCP installed automatically by the skill.
4. JSON configs create `.bak-*` backups before writing; CLI clients remove any existing server of the same name before re-registering.

## Concurrency Strategy

`mcp-server/server.py` serializes all tool calls with a global `RLock` because:

- SolidWorks COM automation is not a thread-safe concurrent service.
- Concurrent tools switching active documents, selecting entities, or saving files corrupt each other's state.
- Motion Study and Mate creation depend on the active selection set and must avoid concurrent interference.

Each tool call invokes `pythoncom.CoInitialize()` to ensure COM is initialized on the active MCP worker thread.

## Tool Naming

Tool prefixes reflect capability boundaries: `cadstudio_` covers headless open formats, DFM, Routing, FEA, and complex geometry gates; `solidworks_` covers live SolidWorks COM operations.

CAD Studio gate tools:

- `cadstudio_resolve_backend`
- `cadstudio_write_open_format`
- `cadstudio_build_dxf_preview_scene`
- `cadstudio_check_dfm`
- `cadstudio_check_routing`
- `cadstudio_routing_preflight`
- `cadstudio_fea_preflight`
- `cadstudio_prepare_fea`
- `cadstudio_run_fea`
- `cadstudio_run_fea_convergence`
- `cadstudio_review_advanced_geometry`
- `cadstudio_create_ocp_loft`
- `cadstudio_create_ocp_surface`

Native SolidWorks tools:

- `solidworks_connect`
- `solidworks_new_document`
- `solidworks_open_document`
- `solidworks_inspect_configurations`
- `solidworks_create_configuration`
- `solidworks_activate_configuration`
- `solidworks_save_document`
- `solidworks_close_documents`
- `solidworks_export_active`
- `solidworks_review_active`
- `solidworks_add_rotary_motor`

## Security Boundaries

Excluded from Phase 1:

- Arbitrary Python execution.
- Arbitrary VBA macro execution.
- Direct file deletion.
- Hidden batch closing or overwriting of user files.

Adding any hazardous tool requires at minimum:

1. Explicit action keywords in the tool name (`delete` / `overwrite` / `close_all`, etc.).
2. Input schemas restricting paths and parameter bounds.
3. Structured return output detailing actual blast radius.
4. Documenting `destructiveHint=True`.

## Recommended Expansion Order

Prioritize high-value, low-ambiguity tools:

1. Documents & Export: open, save, export, review.
2. Assemblies: insert component, lookup by name, create Concentric/Coincident mates.
3. Motion Study: rotary motor, linear motor, calculate/play.
4. Part Modeling: controlled sketch and feature primitives.
5. Engineering Drawings: standard three views, BOM, PDF export.
6. Headless capabilities: DFM profiles, neutral Routing review, constrained linear/nonlinear CalculiX & mesh convergence sequences, OCP ruled/smooth Loft, Sweep/Knit/Thicken, and complex geometry plan review.

Deferred for later:

- Arbitrary sketch constraint solving.
- Smooth Loft, complex sweeps, G1/G2/Class-A, and mold-grade B-Rep generation.
- Large-scale contact, automated penetration sign-off, collision dynamics, and safety certification.

## Return Format

Tools default to JSON for downstream LLM parsing, and also support `response_format="markdown"` for human reading.

Error responses must include:

- `error_type`
- `message`
- `suggestion`

Never expose raw Python tracebacks to MCP clients.
