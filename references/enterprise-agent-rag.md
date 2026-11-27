# Enterprise Agent and Mechanical Knowledge Base

## Target Architecture

CAD Studio uses a "Control Plane + Deterministic CAD Tools + Reviewer Gate + Local-First RAG" architecture:

```text
用户对话/UI 配置
  -> Intake / Planner
  -> 本地知识检索（默认）
  -> 可选云知识检索（显式启用 + 外部网络审批）
  -> Codex Executor
  -> SolidWorks / AutoCAD 串行工具
  -> Artifact Ledger
  -> Reviewer Gate
  -> 人工复核与继续对话
```

`apps/desktop/cad_workbench/knowledge_retrieval.py` implements:

- Retrieval across root `SKILL.md`, `references/`, all subskill references, and knowledge files.
- Bilingual (Chinese/English) tokenization, chunking, and Top-K ranking.
- Source path, content SHA-256, relevance score, and provider metadata on every chunk.
- Automatic injection of retrieved chunks into enterprise prompts by the Worker.
- Optional HTTPS cloud RAG connector reading tokens exclusively from environment variables.

## Data Boundaries

1. Local skill knowledge is searched by default without uploading user projects, models, drawings, or prompts.
2. Cloud knowledge bases must explicitly declare `external_network` on the task and pass manual approval.
3. Cloud endpoints must use HTTPS; tokens are never written to task JSON, logs, or UI persistence files.
4. The token environment variable is fixed to `CAD_STUDIO_RAG_TOKEN`; tasks cannot specify arbitrary environment variable names to prevent exfiltrating unrelated credentials.
5. Custom local knowledge directories trigger cross-workspace access approval; writing directly to queue files cannot bypass this gate.
6. Retrieved chunks serve only as reference evidence and cannot replace primary TCVN/ISO standards, material handbooks, vendor catalogs, enterprise standard originals, or secondary GB/T reference documents.
7. Knowledge chunks must retain `source` and `sha256`; content without traceable provenance must never serve as a manufacturing gate basis.

## Task Configuration

```json
{
  "uiConfig": {
    "knowledgeBase": {
      "topK": 6,
      "localRoots": ["D:/company-cad-standards"],
      "cloudEnabled": false,
      "endpoint": "https://rag.example.com/retrieve",
      "namespace": "mechanical-engineering",
      "tokenEnv": "CAD_STUDIO_RAG_TOKEN"
    }
  }
}
```

Cloud service response contract:

```json
{
  "chunks": [
    {
      "title": "轴承座孔配合",
      "source": "enterprise-standard://bearing/fit-v3",
      "text": "可检索的原文片段",
      "score": 0.91
    }
  ]
}
```

## Knowledge Hierarchy

- `L0 Session Facts`: User dimensions, purpose, material, loads, manufacturing process, target CAD software.
- `L1 Project Knowledge`: Active drawings, parameter tables, BOMs, company standards, revision history.
- `L2 Skill Knowledge`: Repository reference docs, specialized subskills, verified API experience.
- `L3 Organizational Knowledge`: Approved templates, failure postmortems, shop capabilities, supplier constraints.
- `L4 External Knowledge`: Official APIs, national/industry standards, vendor handbooks; version and provenance must be preserved.

Retrieval precedence is `L0 > L1 > L2 > L3 > L4`. On conflict, halt automatic execution and escalate the conflict to the Reviewer—never silently choose one side.

## Pre-Cloud Readiness Gates

- Multi-tenant namespace isolation and least-privilege tokens.
- Document-level ACLs enforced prior to retrieval, never merely filtered after answer generation.
- Immutable audit logs for uploads, deletions, and re-indexing.
- Client-side redaction of PII, secrets, customer drawing watermarks, and controlled technical data.
- Support for source revocation, version rollback, expiration policies, and citation hit metrics.
- Attach a "verify against original text" tag to standard numbers, materials, tolerances, and safety factors.
