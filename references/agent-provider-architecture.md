# Multi-Agent Provider Architecture

## Objective

CAD Studio targets diverse user environments without locking into a single model or CLI. All providers share one CAD task protocol, approval policy, knowledge retrieval layer, artifact ledger, and review gate; differences are confined strictly to command compilation and result parsing.

```text
用户任务
  -> UnifiedAutomationJob
  -> Policy Gate
  -> Provider Adapter
  -> Codex / Claude Code / Gemini CLI / OpenCode
  -> UnifiedAgentResult
  -> Artifact Ledger
  -> CAD/B-Rep/Motion Reviewer Gate
  -> 本地交付目录
```

## Do Not Conflate Provider States

The UI and logs must distinguish each of the following states explicitly:

| State | Evidence | Can Be Described as "Connected"? |
|---|---|---|
| Not Installed | CLI entry point not found or `--version` fails | No |
| Installed | `--version` succeeds | No |
| Auth Failed | Official auth status command returns failure | No |
| Auth Pending | CLI lacks a low-cost auth status command | No; verified on first real task |
| Auth Verified | Official auth status command succeeds | May be described as auth verified |
| Execution Verified | Real task returns structured output under unified protocol | May be described as task execution succeeded |

The presence of a CLI binary, environment variables, or a Provider entry in CC Switch cannot independently prove that model requests work. Nor does a Provider's self-reported success prove that SolidWorks/AutoCAD deliverables are valid.

## Unified Task Protocol

Tasks use kind `agent_task` and executor `agent`:

```json
{
  "kind": "agent_task",
  "executor": "agent",
  "objective": "创建带沉孔和半圆槽的安装板",
  "skillPath": "C:/Users/user/.codex/skills/solidworks-automation/SKILL.md",
  "uiConfig": {
    "agentRuntime": {
      "provider": "claude",
      "providerName": "Claude Code",
      "protocol": "claude-print-v1",
      "model": ""
    }
  }
}
```

Legacy `codex_task` and `executor=codex` remain compatibility aliases only and normalize into the exact same execution flow once inside the Worker.

## Unified Result Protocol

Every Provider must ultimately produce the following fields:

```json
{
  "summary": "本轮做了什么",
  "changedFiles": [],
  "verification": [],
  "risks": [],
  "nextSteps": []
}
```

The unified result is only an agent execution record, not CAD acceptance evidence. Mechanical deliverables still require independent file hashes, B-Rep dimensions, hole/slot locating checks, preview renders, Motion results, and manual review records.

## Current Adapters

| Provider | Protocol ID | Non-Interactive Entry | Structured Output Source |
|---|---|---|---|
| Codex | `codex-exec-v1` | `codex exec` | `--output-schema` + output file |
| Claude Code | `claude-print-v1` | `claude -p` | `--output-format json` + `--json-schema` |
| Gemini CLI | `gemini-headless-v1` | `gemini -p` | JSON response wrapper |
| OpenCode | `opencode-jsonl-v1` | `opencode run` | JSONL text events |

Implementations live in:

- `apps/desktop/cad_workbench/agent_providers.py`
- `apps/desktop/cad_workbench/queue_worker.py`
- `apps/workbench-ui/src-tauri/src/lib.rs`

## Steps to Add a New Provider

1. Register a stable ID in `SUPPORTED_PROVIDER_IDS` and frontend `AgentProviderId`.
2. Use only non-interactive flags confirmed in that CLI's official documentation; never guess flags from memory.
3. Compile the unified task into a Provider command inside `build_provider_command()`.
4. Parse the native wrapper inside `parse_provider_result()` and enforce convergence onto the unified result schema.
5. Add tests for installation, authentication, timeout, non-JSON output, missing fields, and task cancellation.
6. Distinguish install, auth, and execution verification in desktop health checks; never introduce an ambiguous "connected" boolean.
7. Run a real minimal probe to verify exit code, stdout/stderr, cancellation, and timeout behavior.

## Observable Execution Trace

The application may display plans, public steps, tool calls, approvals, logs, file changes, and review results. Never promise or fabricate hidden model chain-of-thought; what users actually need is an auditable execution trail and a follow-up-ready conversation context.

## Security Boundaries

- Provider adapters do not expose arbitrary Python, PowerShell, or VBA tools directly.
- CAD COM calls are serialized to prevent multiple agents from colliding in the same desktop session.
- External network access, cloud RAG, and hazardous local CAD operations pass through the Policy Gate.
- API keys are never written to task JSON, logs, or frontend persistent state; only redacted status or environment variable names are recorded.
- Provider outputs must pass schema validation, Artifact Ledger logging, and the Reviewer Gate before delivery can be declared complete.
