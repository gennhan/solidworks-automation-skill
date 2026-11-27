# V2 Evaluation — Golden Workflow Reliability Eval

## 1. Why Eval Is Needed

V2 aims to make existing capabilities execute more reliably. Achieving this requires more than subjective judgment—it requires a **repeatable, quantifiable, CI-safe** reliability benchmark answering:

1. How many nominal tasks succeed? (`Nominal Task Success Rate`)
2. How many nominal tasks succeed on the first attempt? (`Nominal First Pass Success Rate`)
3. Can failures recover cleanly? (`Recovery Success Rate`)
4. Does the system reliably detect injected faults? (`Failure Detection / Expected Outcome Accuracy`)
5. Are there any **escaped false completions** where a tool reports success, Verification fails, yet the task is still marked completed? (`Escaped False Completion Rate`)

These metrics are trustworthy because they come from the **deterministic Execution Core + Fake Handler/Reviewer**, unaffected by LLM variance, networking, or live CAD host state.

## 2. What Golden Workflows Are

`golden-workflows.yaml` is the **sole source of truth** for Golden Workflows (`schema_version: 1.0`), containing `target_first_pass_rate` and the workflow definitions (originally 10 workflows, now 12). Eval **derives scenarios directly from this file** without duplicating definitions or adding a second config, preserving full compatibility with existing fields.

## 3. Scenario Categories (`benchmark_group`)

Eval scenarios must be separated by **metric scope**—deliberately failing scenarios must never be mixed into the same denominator as nominal workflows. Classification is **deterministic** by scenario type:

| category | scenario types | Purpose |
|---|---|---|
| `nominal` | `happy` | Normal business tasks, compared against `target_first_pass_rate` |
| `recovery` | `transient_recovery`, `backend_fallback` | Scripted recovery after failure |
| `fault_injection` | `verification_failure`, `reviewer_blocked`, `retry_exhausted` | Deliberately injected faults testing detection |
| `guardrail` | `warning`, `policy_block`, `user_action_required`, `capability_gap` | Verifies gating and human-review blocking accuracy |

## 4. Metric Definitions

### Nominal (Nominal Scenarios Only)

| Metric | Definition |
|---|---|
| `nominal_task_success_rate` | Fraction of nominal scenarios ending in `terminal == completed` |
| `nominal_first_pass_success_rate` | Fraction of nominal scenarios ending in `completed` on attempt 1 with zero recovery |
| `nominal_average_tool_calls` / `duration` | Mean values over the nominal subset |

`target_first_pass_rate` (`0.90`) is compared **exclusively against `nominal_first_pass_success_rate`**.

### Robustness (`recovery` / `fault_injection` / `guardrail`)

| Metric | Definition |
|---|---|
| `expected_outcome_accuracy` | Fraction where `terminal == expected_terminal_status` (primary robustness metric) |
| `recovery_success_rate` | Fraction of `recovery` scenarios ending in `completed` |
| `failure_detection_rate` | Fraction of `fault_injection` scenarios where `terminal != completed` |
| `policy_block_accuracy` | Fraction of `policy_block` scenarios ending in `blocked` |
| `capability_gap_detection_rate` | Fraction of `capability_gap` scenarios ending in `failed` |
| `backend_fallback_decision_accuracy` | Fraction of `backend_fallback` scenarios ending in `completed` |
| `reviewer_block_detection_rate` | Fraction of `reviewer_blocked` scenarios ending in `blocked` |
| `retry_exhaustion_accuracy` | Fraction of `retry_exhausted` scenarios ending in `failed` |

Note: **The correct outcome of a policy block is `BLOCKED`, and the correct outcome of a capability gap is `FAIL/REPLAN`**—these are **not task failures**, but proper handling. Robustness therefore uses `expected_outcome_accuracy` rather than task success.

### Safety (False Completions)

| Metric | Definition |
|---|---|
| `raw_false_completion_incidence` | Cases where Handler reports success while Verification returns `FAIL`/`BLOCKED`, divided by Handler-success runs. **Expected to be high** because fault-injection deliberately manufactures these candidates. |
| `false_completion_detection_rate` | Injected false-completion candidates properly intercepted by Verification divided by total injected candidates. Target approaches 100%. |
| `escaped_false_completion_rate` | Cases where Handler reports success, Verification returns `FAIL`/`BLOCKED`, yet final status still reaches `completed`. Target **0**. |

### Overall (Diagnostic Only, Never Compared to Target)

| Metric | Definition |
|---|---|
| `overall_scenario_count` | Total number of scenarios |
| `overall_raw_task_completion_rate` | Overall `terminal == completed` ratio (diagnostic only) |

## 5. Precise False Completion Definition (Corrected)

Strictly separate three distinct layers:

- **Raw false positive** (Handler false positive) = `handler_success AND verification ∈ {FAIL, BLOCKED}`. This measures how often underlying execution produces false-success candidates (naturally high in fault-injection suites) and is **not the system's false-completion leak rate**.
- **Detection rate** = fraction of injected false-success candidates intercepted by Verification. **High = effective Verification**.
- **Escaped rate** = fraction of false-success candidates that still reach `completed`. **This is the true false-completion leak**, targeted at 0.

The legacy metric conflated all three into one `false_completion_rate` (`33.3%`), making "Verification correctly caught 11 injected false-success candidates" look like "the system leaks 33.3% false completions".

## 6. Legacy Calculation Flaw (Why 59.5% / 29.7% / 33.3% Were Distorted)

Phase 6's original formula mixed all 37 scenarios (10 `happy` + 10 `verification_failure` + 10 `transient_recovery` + 7 cross-cutting) **into one denominator** for first-pass and false completion:

- **29.7% first-pass**: 10 `happy` + 1 `warning` passing on attempt 1 divided by all 37 scenarios (including intentional failures), artificially depressing first-pass rate and causing a false `BELOW_TARGET` against 90%.
- **33.3% false completion**: 10 `verification_failure` + 1 `reviewer_blocked` were **deliberately injected** false-success candidates properly caught by Verification; the old formula counted incidence instead of leakage, whereas actual escaped leakage was **0%**.

Current baseline **v4** (verified by live run on 2026-10-27): `golden-workflows.yaml` contains 12 workflows deriving **43 scenarios** (12 nominal + 31 robustness). `warning` is classified under the human-review guardrail and can no longer be claimed as task completion. `nominal_first_pass = 100%` (12/12) vs. 90% target → **PASS**; `escaped_false_completion = 0%` → zero false-completion leaks. Overall raw completion across 43 scenarios is 25/43 (`58.1%`, diagnostic only); earlier figures (`21/37` / `56.8%`, `11/11`, `59.5%`) are historical scopes.

> **Historical Scope Note**: References above to "37 scenarios (10 happy + 10 verification_failure + 10 transient_recovery + 7 cross-cutting)"
> describe the Phase 6 scenario set and are retained for historical comparison. The suite has expanded to 43 scenarios;
> legacy denominator figures (`21/37`, `56.8%`, `29.7%`, `33.3%`) must no longer be cited as current metrics.

## 7. Deterministic Fixture Design

Makes zero LLM, web, or live CAD calls. Uses Fake Handlers (`success_handler`/`fail_handler`), Fake Reviewers (`pass`/`warn`/`fail`/`blocked`/`crash_reviewer`), Fake Capability Facade, and exception classes aligned with `core.recovery._EXCEPTION_KIND`. Post-recovery steps are simulated via scripted multi-attempt sequences without turning on auto-retry in production Worker.

## 8. Running Eval

```powershell
python tests/evals/runner.py
```

Outputs `eval_report.json` and `eval_report.md` (defaulting to gitignored `tests/evals/reports/`).

## 9. Reading the Report

The report has four sections: Nominal Reliability (business pass rate + target check), Robustness (expected-outcome accuracy + detection rates), Safety (false-completion incidence/detection/escaped), and Overall Diagnostic (diagnostic only).

- `Nominal First Pass Success Rate` vs. `Target` → `PASS` / `BELOW_TARGET`.
- `Escaped False Completion Rate` → must equal `0`.
- `Expected Outcome Accuracy` → composite robustness indicator.

## 10. What Current Eval Does Not Cover

- Live SolidWorks / AutoCAD execution (covered by live-machine regressions).
- Real LLM planning/tool-calling quality, model comparisons, token cost, or LLM-as-a-judge.
- Network / external APIs.

## 11. Extending to Live Agent Eval Later

Phase 6 / 7.5 benchmarks **Execution Reliability** deterministically. A future Live Agent Eval (running real Codex/Claude through real Skill + Worker) can reuse the exact same `EvalRecord` / `metrics` / `EvalReport` pipeline simply by swapping `run_scenario`'s handler for a live agent call.
