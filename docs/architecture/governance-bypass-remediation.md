# Risk of Bypassing Required Checks and Minimal Remediation Plan

> Status: **Plan finalized, not yet executed**. Remote ruleset remains unchanged pending explicit maintainer approval.
> Scope: `protect-main` ruleset (id `25631760`).
> Related implementation: [`governance-attestation.md`](governance-attestation.md).

---

## 1. Current State (Observed 2026-10-27, Read-Only)

```json
{
  "id": 25631760,
  "name": "protect-main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["refs/heads/main"], "exclude": [] } },
  "rules": ["deletion", "non_fast_forward", "pull_request", "required_status_checks"],
  "required_status_checks": [{ "context": "test-and-build", "integration_id": 15368 }],
  "required_approving_review_count": 0,
  "require_code_owner_review": false,
  "bypass_actors": [{ "actor_id": 199356225, "actor_type": "User", "bypass_mode": "always" }],
  "updated_at": "2026-10-22T18:42:30.335+08:00"
}
```

## 2. Risk: Effect of `bypass_mode = always`

GitHub's `bypass_actors` exempts listed actors from **every rule in the ruleset**, including:

- No PR required (`pull_request` rule bypassed);
- No passing `test-and-build` required (`required_status_checks` bypassed);
- Exempt from `deletion` / `non_fast_forward` (force-push and branch deletion permitted).

Consequently, **required checks currently apply only to actors other than the owner**. In a single-maintainer repository like this one,
that means the ruleset is effectively unenforced for almost every real write operation.

### 2.1 Why Signed Attestation Alone Does Not Solve This

An offline attestation proves only that "`bypass_actors` was empty in the ruleset snapshot captured at time T".
It is **authenticity proof of a configuration snapshot**, not **a technical control preventing bypass**:

| Mechanism | Can Prove | Cannot Do |
| --- | --- | --- |
| Signed attestation + `trust_root_anchor` | Bypass was empty at capture time; config was not silently altered | Stop the owner from pushing directly to `main` while bypass is configured |
| `check_governance_drift` | Produces an explicit diff when governance files change | Stop an authorized user from editing both files and merging anyway |

As long as `bypass_actors` is non-empty, both controls can be bypassed "legitimately"—not by breaking cryptography, but because the ruleset permits it.

### 2.2 Current Effective Exposure

| Scenario | Current State |
| --- | --- |
| External contributor force-pushes `main` | ❌ Impossible (no write access) |
| External contributor merges skipping required checks | ❌ Impossible (no merge access) |
| **Owner pushes directly to `main`** | ✅ **Possible** (`bypass always`) |
| **Owner merges skipping `test-and-build`** | ✅ **Possible** |
| Owner force-overwrites history | ✅ Possible (`non_fast_forward` bypassed) |

---

## 3. Minimal Remediation Plan

### 3.1 Proposed Change

**Single-field edit**: `bypass_actors: [...] → []`. All other fields (`rules`, `conditions`, `enforcement`,
`required_status_checks`, and `pull_request` parameters) remain **completely untouched**.

### 3.2 Why This Is Minimal

| Alternative | Assessment |
| --- | --- |
| Delete and recreate ruleset | ❌ Loses `updated_at` continuity and leaves an unprotected window during recreation |
| Change `enforcement: evaluate` | ❌ Disables enforcement—opposite of the goal |
| Add a second ruleset for feature branches | Out of scope (goal is solely removing bypass) and raises single-maintainer overhead |
| **Clear `bypass_actors`** | ✅ Single PUT, single field, field-by-field readback verification, exact rollback possible |

### 3.3 Prerequisites (All Mandatory)

1. Take a full JSON backup of the current ruleset and record its SHA-256 hash;
2. Confirm `test-and-build` runs on **GitHub-hosted runners** (`windows-2022`, requiring no self-hosted runner);
3. Confirm the maintainer accepts that all subsequent changes to `main` must go through a PR and wait for CI;
4. Record rollback triggers (see §5).

### 3.4 Execution Steps

```bash
# 1) 备份
gh api repos/wzyn20051216/solidworks-automation-skill/rulesets/25631760 > ruleset-backup-$(date +%Y%m%d).json
sha256sum ruleset-backup-*.json

# 2) 仅改 bypass_actors（其余字段取自上一步的备份，逐个复制）
gh api -X PUT repos/wzyn20051216/solidworks-automation-skill/rulesets/25631760 \
  --input ruleset-without-bypass.json

# 3) 立即回读完整结构
gh api repos/wzyn20051216/solidworks-automation-skill/rulesets/25631760 \
  --jq '{bypass:.bypass_actors, rules:[.rules[].type], upd:.updated_at, cond:.conditions}'

# 4) 重签证明（旧证明必因 updated_at + snapshot_digest 变化而失效）
GH_TOKEN="$(gh auth token)" node scripts/ci/capture_governance_attestation.cjs --verify
node scripts/ci/check_governance_drift.cjs --update
```

### 3.5 Acceptance Criteria

| Criterion | Expected |
| --- | --- |
| `bypass_actors` | `[]` (empty array, not missing field) |
| `rules` | Still the four types: `deletion`, `non_fast_forward`, `pull_request`, `required_status_checks` |
| `conditions.ref_name.include` | Still `["refs/heads/main"]` |
| `required_status_checks` | Still `test-and-build` |
| **`policy_digest`** | **Identical to pre-change value** (proves rules were not altered) |
| **`snapshot_digest`** | **Must change** (covers bypass and `updated_at`) |
| `updated_at` | Changes (sole read-only observable change anchor) |
| New attestation `--verify` | Passes, with `compliant: true` and empty `noncompliance_reasons` |

> This is the exact division of roles between the two digests: unchanged `policy_digest` proves "only bypass changed",
> while changed `snapshot_digest` proves "the complete snapshot genuinely changed". Never use the former to claim overall immutability.

### 3.6 Post-Change Operational Impact

After clearing bypass, the owner's workflow changes as follows:

- Changes to `main` **must** use a PR and pass `test-and-build`;
- During emergencies (CI outage, quota exhaustion), there is **no** direct-push shortcut. The proper procedure is:
  record outage evidence → retry manually via `workflow_dispatch` → if still failing, defer the change or explicitly approve a temporary relaxation and **document it retroactively**;
- Any temporary re-addition of bypass constitutes a **new ruleset modification**, invalidating the attestation and requiring immediate re-capture.

---

## 4. Relationship to CI Gates

Clearing bypass resolves only "owner can bypass". It does **not** resolve the following three gaps, which remain separate concerns:

| Gap | Status | Notes |
| --- | --- | --- |
| Admin can edit the ruleset itself | Present | An admin can re-add bypass and re-sign an attestation; mitigated only by change audit trail + human review, not technically preventable |
| No mandatory code owner review | Present | `require_code_owner_review = false`; enabling in a single-maintainer repo deadlocks because authors cannot approve their own PRs |
| PR can edit guard/workflow/tests together | Present | Drift detection produces an explicit diff but cannot block |

All three gaps must remain transparently disclosed; clearing bypass must **not** be presented as "complete governance closure".

---

## 5. Rollback Plan

**Triggers** (roll back immediately if any occur): readback shows missing rule types, altered `conditions`,
lost `required_status_checks`, or `test-and-build` unable to execute on hosted runners.

```bash
# 原样 PUT 回备份（不要手写简化 body）
gh api -X PUT repos/wzyn20051216/solidworks-automation-skill/rulesets/25631760 \
  --input ruleset-backup-YYYYMMDD.json
# 回滚后必须重新 GET 复核，并重新采集证明；不能沿用旧证明
```

Never use `git reset --hard` on the code side; use `git revert` when reverting commits.

---

## 6. Stop Conditions

- Incomplete or unrecoverable backup;
- Unable to verify the change affected only `bypass_actors` (any `policy_digest` change is treated as failure);
- Readback still shows non-empty or unreadable `bypass_actors`;
- Any action would touch code pushes, PR merges, or releases (this plan modifies remote ruleset configuration only, not code);
- Maintainer has not completed §3.3 prerequisites.
