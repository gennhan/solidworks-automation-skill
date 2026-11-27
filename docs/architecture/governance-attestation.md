# Governance Ruleset Attestation: Offline Capture, Signing, and Read-Only Verification

**This document is the single authoritative specification for governance attestation.** If any other document conflicts with this file, this document prevails;
`CONTRIBUTING.md` and `docs/architecture/real-golden-merge-readiness.md` describe policy and acceptance only and do not duplicate field-level details.

This specification explains how `bypass_actors` on the `main` branch ruleset is proven empty **without granting write permissions to CI**,
along with the attestation's trust boundaries, dual-digest semantics, capture workflow, key rotation, and invalidation rules.

Attestation schema version: `cad-governance-attestation/v2`.

---

## 1. Why Offline Attestation Is Required

GitHub's ruleset detail endpoint only requires `Metadata: read`, but `bypass_actors` is separately gated:

> `bypass_actors` is only returned if the user making the API request has **write access** to the ruleset.

Verified empirically on this repository (2026-10-27, comparing admin vs. anonymous public-repo requests):

| Field | Admin Credentials | No Write Access (Anonymous Equivalent) |
| --- | --- | --- |
| `bypass_actors` | Present | **Field omitted entirely** (not `null`) |
| `current_user_can_bypass` | Present | **Also omitted** |
| `updated_at` | Present | Present (the only usable read-only anchor) |
| List endpoint `/rulesets` | **Never returns** `bypass_actors` | Never returns |

Therefore, no path exists to read `bypass_actors` using read-only credentials alone. Granting write permissions to CI would violate least privilege,
so the model instead is: **Maintainer captures and signs once locally → Attestation committed to repo → CI verifies signatures read-only.**

---

## 2. Trust Boundaries (Must Be Disclosed Honestly)

### 2.1 What This Mechanism Guarantees

- **Tamper Evidence**: Any modification to the attestation invalidates its signature;
- **Configuration Drift Detection**: Any remote ruleset change updates `updated_at`, immediately invalidating the old attestation;
- **Identity Binding**: The attestation binds immutable `repository.id` and `ruleset.id`, preventing cross-repo or cross-ruleset substitution;
- **Integrity Separation**: `policy_digest` and `snapshot_digest` separately cover "rule definitions" versus "full state".

### 2.2 What This Mechanism Cannot Guarantee

| Limitation | Reason | Code Disclosure Flag |
| --- | --- | --- |
| Not an independent audit | Attestation is self-issued by the maintainer | `governance.independent_audit` is always `false` |
| Trust root co-located with protected repo | Public key lives in-repo; anyone able to merge to `main` could replace both key and attestation | `trust_root_stored_in_repository` |
| Repo variable anchor is not absolute | Anyone with repository admin privileges can modify the variable alongside the repo | `trust_root_anchor` check + manual criteria |
| CODEOWNERS not enforced | `require_code_owner_review = false`; enabling it in a single-maintainer repo causes deadlock | `code_owner_review_not_enforced` |
| PR can modify verification code simultaneously | No trusted-baseline workflow executes judgment logic independently | `trusted_baseline_workflow_not_established` |

**Role of repository variable `GOVERNANCE_TRUST_ROOT_ANCHOR`**: Stored outside repository files, so a combined attempt to
"swap public key + alter rotation log + re-sign attestation with a new private key" fails anchor validation.
This raises attack cost and leaves an audit trail, but **cannot stop** a repository administrator from updating the variable as well.

### 2.3 Computing the Trust Anchor

```bash
node -e "const l=require('./scripts/ci/governance_attestation.cjs');
const {TRUSTED_KEYS}=require('./scripts/ci/governance_trust_root.cjs');
console.log(l.trustRootAnchor(TRUSTED_KEYS))"
```

Outputs `sha256:<64 hex chars>`, which is stored in repository variable `GOVERNANCE_TRUST_ROOT_ANCHOR`.
The digest covers `keys` (including `pem` / `not_before` / `revoked_at`) and the complete `log`; PEM strings have CRLF and leading/trailing whitespace normalized first.
**Missing anchor, invalid format, uncomputable trust root, or digest mismatch all block execution.**

---

## 3. Dual-Digest Semantics (Never Conflate)

| Digest | Coverage | Purpose | Excluded |
| --- | --- | --- | --- |
| `policy_digest_sha256` | `id`, `name`, `target`, `enforcement`, branch include/exclude, all `rules` (type + parameters) | Proves "rule definitions were not accidentally altered when adjusting bypass" | **Excludes** `bypass_actors`, `updated_at` |
| `snapshot_digest_sha256` | All of the above + `bypass_actors` (normalized/sorted) + `updated_at` + `created_at` | Binds "full governance state at the moment of capture" | — |

Rules:

1. **Never cite an unchanged `policy_digest` as proof that the entire configuration is unchanged.** Modifying bypass changes `snapshot_digest` only.
2. `policy_digest` must match across all three sources: declared value in attestation = recomputed from attestation body = recomputed from live read-only API response.
3. `snapshot_digest` must be self-consistent; if live credentials **can** read `bypass_actors` (admin context), it must also match the full live snapshot.
4. When read-only credentials cannot see `bypass_actors`, binding `snapshot_digest` to live state relies on `updated_at` equality—this is an **indirect binding** and must never be described as "field-by-field comparison of the full live configuration".

---

## 4. Attestation Structure (v2)

```jsonc
{
  "schema": "cad-governance-attestation/v2",
  "repository": { "id": "1184045765", "full_name": "wzyn20051216/solidworks-automation-skill" },
  "ruleset": {
    "id": 25631760, "name": "protect-main", "target": "branch", "enforcement": "active",
    "ref_name_include": ["refs/heads/main"], "ref_name_exclude": [],
    "updated_at": "...", "created_at": "...",
    "rules": [ { "type": "deletion" }, { "type": "pull_request", "parameters": { } } ],
    "bypass_actors": [ ]
  },
  "policy_digest_sha256":   "<64 hex>",
  "snapshot_digest_sha256": "<64 hex>",
  "compliant": false,
  "noncompliance_reasons": ["bypass_not_empty"],
  "governance": {
    "mode": "single_maintainer",
    "independent_audit": false,
    "bypass_requirement": "empty",
    "trust_boundary": "……"
  },
  "captured_at": "…", "expires_at": "…",
  "generator": { "tool": "capture_governance_attestation.cjs", "node": "v22.x" },
  "signer": { "key_id": "ed25519:<sha256>", "key_type": "ed25519", "signed_at": "…" },
  "signature": "<base64 Ed25519>"
}
```

The signature covers **every field except `signature`** (canonical JSON: sorted keys, order-preserving arrays).
Thus `compliant`, `noncompliance_reasons`, both digests, and `bypass_actors` are all cryptographically protected,
preventing post-hoc edits from flipping a non-compliant record to compliant.

### 4.1 Meaning of `compliant`

`compliant` indicates **whether the recorded state satisfies admission prerequisites**, determined uniformly by `evaluateCompliance()` using:

- `enforcement === 'active'`;
- `target === 'branch'`;
- Branch scope is strictly `refs/heads/main` with an empty `exclude` list;
- Both `pull_request` and `required_status_checks` rules are present;
- Required status checks include `test-and-build`;
- `bypass_actors` is an array of length 0 (omission is recorded as `bypass_unreadable`, never treated as passing).

The verifier not only requires `compliant === true` and an empty `noncompliance_reasons`, it also **recomputes compliance from the attestation payload**;
any mismatch fails with `attestation_compliance_inconsistent`.

---

## 5. Generation Workflow (Maintainer Local Machine)

```bash
# 一次性：生成签名密钥对。私钥留在本机，公钥由 governance_trust_root.cjs 固定
node -e "const c=require('node:crypto'),f=require('node:fs'),p=require('node:path');
const dir=p.join(require('node:os').homedir(),'.cad-governance');f.mkdirSync(dir,{recursive:true});
const {publicKey,privateKey}=c.generateKeyPairSync('ed25519');
f.writeFileSync(p.join(dir,'ed25519-private.pem'),privateKey.export({type:'pkcs8',format:'pem'}),{mode:0o600});
console.log(publicKey.export({type:'spki',format:'pem'}))"

# 每次规则集变更后：采集并签名（默认只在合规时签发）
GH_TOKEN="$(gh auth token)" node scripts/ci/capture_governance_attestation.cjs --verify

# 只打印不入库
GH_TOKEN="$(gh auth token)" node scripts/ci/capture_governance_attestation.cjs --print-only

# 非合规状态需要留证时（诊断用途，产物永远无法通过准入）
GH_TOKEN="$(gh auth token)" node scripts/ci/capture_governance_attestation.cjs --allow-noncompliant
```

Arguments and exit codes:

| Argument | Description |
| --- | --- |
| `--ttl-days N` | Validity period, `1..30`, default `30` |
| `--out PATH` | Output path, default `docs/architecture/evidence/governance-ruleset-attestation.json` |
| `--key PATH` | Private key path, default `%USERPROFILE%\.cad-governance\ed25519-private.pem` |
| `--print-only` | Print to stdout only without writing to disk |
| `--allow-noncompliant` | Allow capturing evidence while non-compliant; output is marked `compliant: false` |
| `--verify` | Immediately re-verify against the read-only snapshot and repository trust root after capture |

| Exit Code | Meaning |
| --- | --- |
| `0` | Issued a `compliant: true` attestation |
| `1` | Failure (including **default refusal to sign**: remote non-compliant, unreadable bypass, identity mismatch) |
| `2` | Issued a diagnostic attestation with `compliant: false` |
| `3` | `--verify` check failed |

**Default refusal to sign is a hard constraint**: when the remote state is non-compliant, no file is written, preventing "generated" from being misread as "passed".

---

## 6. CI Read-Only Checks (28 Checks)

`evaluatePolicy()` in `scripts/ci/cad_ci_guard.cjs` evaluates each check; any `false` result yields `blocked`.

**Context and Source**

1. `trusted_repository`
2. `manual_branch_only`
3. `protected_ref_is_main`
4. `protected_immutable_source`

**Ruleset Structure**

5. `ruleset_active`
6. `pull_request_required`
7. `required_status_checks_present` (must include `test-and-build`)

**Trust Root**

8. `trust_root_integrity`
9. `trust_root_rotation_log`
10. `trust_root_anchor`

**Attestation Binding**

11. `attestation_present`
12. `attestation_schema`
13. `attestation_declaration`
14. `attestation_signature`
15. `attestation_repository`
16. `attestation_ruleset_identity`
17. `attestation_main_scope`
18. `attestation_fresh`
19. `attestation_policy_digest`
20. `attestation_snapshot_digest`
21. `attestation_updated_at`
22. `attestation_compliant`
23. `no_bypass_actors`
24. `live_bypass_consistent`

**Credentials and Runtime Environment**

25. `authorized_actor_and_rerunner`
26. `protected_environment_exists`
27. `protected_deployment_branches`
28. `idle_windows_cad_runner`

### 6.1 Fail-Closed Summary

All of the following **unconditionally block**, and "unreadable" must never be interpreted as "empty":

- `bypass_actors` field missing, not an array, or non-empty;
- Attestation missing, unparseable, wrong schema, invalid signature, or signed by an unknown/revoked key;
- Mismatch in repository ID, ruleset ID, name, `enforcement`, or branch scope;
- Expired attestation, TTL exceeding 30 days, or `captured_at` in the future beyond clock-skew tolerance;
- Mismatch between attested and live `updated_at`;
- Self-inconsistent `policy_digest` or `snapshot_digest`;
- Missing or malformed trust root, broken rotation log, or retired key without revocation;
- Missing, malformed, or mismatched repository variable `GOVERNANCE_TRUST_ROOT_ANCHOR`.

### 6.2 Path Injection Isolation

`GOVERNANCE_ATTESTATION_PATH` **takes effect only when `NODE_ENV=test`**. Production runs ignore this variable and read the fixed path
`docs/architecture/evidence/governance-ruleset-attestation.json`; if an ignored injection attempt is detected,
the governance risk `attestation_path_overridden_by_test_env` and `attestation_source` are recorded.

---

## 7. Invalidation Rules

| Remote Change | Invalidation Mechanism | Result |
| --- | --- | --- |
| Rule content modified | `policy_digest` changes | `blocked` |
| Bypass modified | `snapshot_digest` changes + `bypass_empty` | `blocked` |
| Any configuration edit | `updated_at` changes | `blocked` |
| Ruleset deleted and recreated | `ruleset.id` changes | `blocked` |
| Attestation expires | `expires_at` | `blocked` |
| Public key replaced | `trust_root_anchor` | `blocked` |
| Retired key not revoked | `trust_root_rotation_log` | `blocked` |

After clearing `bypass_actors`, you **must re-capture immediately**: the old attestation becomes invalid because `updated_at` and both digests change.
This is intentional by design, not a bug.

---

## 8. Key Pinning and Rotation

1. Generate a new key pair locally; keep the private key in `%USERPROFILE%\.cad-governance\` and **never commit it** (excluded via `.gitignore`);
2. **Append** a new entry to `KEYS` in `governance_trust_root.cjs`—never delete old entries;
3. Append the new `key_id` to the end of `ROTATION_LOG`;
4. **Set `revoked_at` on the retired key**. Omission is not treated as revoked—a retired but unrevoked key causes `trust_root_rotation_log` to fail and **blocks all runs**;
5. Recompute the anchor via `trustRootAnchor()` and update repository variable `GOVERNANCE_TRUST_ROOT_ANCHOR`;
6. Re-capture the attestation;
7. Run `node scripts/ci/check_governance_drift.cjs --update` and commit the updated manifest in the same PR.

Mandatory rotation-log checks: every log entry must map to an existing key, every key in `KEYS` must appear in the log,
no duplicates are allowed, every entry except the last must have a parseable `revoked_at`, and the last entry must not be revoked.

> Known limitation: Historical attestations whose `signed_at` precedes `revoked_at` continue verifying to preserve historical auditability.
> Revoking a key therefore does **not** immediately invalidate older attestations; freshness relies on re-capture and `updated_at` binding.

---

## 9. Drift Detection (`check_governance_drift.cjs`)

`test-and-build` executes this script, comparing the SHA-256 digests of 10 governance-sensitive files against
`.github/governance-sensitive-manifest.json`; any discrepancy yields `BLOCKED`.

**Positioning**: This is **drift detection**, not tamper-proofing. Anyone with merge rights can update both the target files and the manifest—but doing so creates an explicit diff showing manifest modifications rather than taking effect silently. True tamper resistance requires a trusted-baseline workflow
(`pull_request_target` without checking out PR code) or an external approval chain, which this repository does not currently have.

The manifest itself is excluded from hashing (self-reference cannot converge) and is covered by `.github/CODEOWNERS`.

```bash
node scripts/ci/check_governance_drift.cjs          # 校验
node scripts/ci/check_governance_drift.cjs --list   # 打印当前摘要
node scripts/ci/check_governance_drift.cjs --update # 有意变更后重建清单
```

---

## 10. Self-Checks

```bash
# 准入策略、证明链路、采集工具、漂移检测的完整回归（当前 93 项）
node --test tests/test_cad_ci_guard.cjs

# 漂移检测
node scripts/ci/check_governance_drift.cjs

# 仅核对离线证明与线上配置是否仍一致（不启动 CI、不启动 CAD）
GH_TOKEN="$(gh auth token)" node scripts/ci/capture_governance_attestation.cjs --allow-noncompliant --print-only --verify
```

All tests above use **local synthetic snapshots** and ephemeral keys and do not represent live remote verification.

---

## 11. Unresolved and Unverified Items

| Item | Status | Notes |
| --- | --- | --- |
| Remote `bypass_actors` currently non-empty | **Unresolved** | `bypass_mode: always`; attestation accurately records `compliant: false` |
| Repo variable `GOVERNANCE_TRUST_ROOT_ANCHOR` | **Not configured** | Must be configured during B5 remote governance stage |
| `cad-validation` Environment | **Does not exist** | B-01 blocker |
| Self-hosted Windows CAD Runners | **0** | B-01 blocker |
| `CAD_CI_AUDIT_TOKEN` | **Does not exist** | Read-only token requiring maintainer creation; guard blocks when missing |
| Remote CAD CI live execution | **NOT VERIFIED** | Has never completed a successful run |
| Cross-machine deployment | **NOT VERIFIED** | Not tested on a second Windows + SolidWorks host |
| Whether `updated_at` updates on every change | **NOT VERIFIED** | Requires one real ruleset edit to confirm |
| Whether authenticated read-only tokens omit bypass identically to anonymous calls | **NOT VERIFIED** | Token not yet created and out of scope for this round |
| Defense against a malicious PR editing guard + workflow + tests together | **Not closed** | Drift detection only; no trusted-baseline workflow |
